"""
Search Agent — Deterministic pipeline + single LLM ranking call.

Applies the "spawner/despawner" pattern:
1. Deterministic Python searches ALL approved domains in parallel
2. Deterministic extractors pull prices from HTML (JSON-LD, meta, CSS)
3. Deterministic RAG lookup finds historical prices
4. Single LLM call ranks/scores candidates against the item description

No tool calling, no multi-turn loops. Local model is sufficient for ranking.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote_plus

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.config import settings
from app.services.llm_settings import run_with_settings, get_model
from app.services.domain_registry import (
    DomainConfig,
    get_all_domains,
    get_domain_config,
    get_search_url,
    is_approved,
)
from app.services.price_extractor import (
    PriceField,
    extract_prices,
    extract_product_links,
    extract_metadata,
)
from app.services.price_normalizer import (
    ComputedTotal,
    NormalizedQuote,
    PricingRules,
    compute_total,
    normalize_price,
)
from app.services.rag import search as rag_search
from app.services.web_fetcher import fetch_page

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structured output models (unchanged — same API contract)
# ---------------------------------------------------------------------------

class WebQuote(BaseModel):
    """A single price quote from a web source with rich product metadata."""

    # Core pricing fields
    vendor: str = Field(description="Supplier/vendor name")
    url: str = Field(description="Product page URL")
    product_name: str = Field(description="Product name as listed on the website")
    unit_price: float = Field(description="Unit price (as displayed, may include VAT)")
    currency: str = Field(default="EUR")
    unit: str = Field(default="kom", description="Unit of measure")
    pack_size: float | None = Field(default=None, description="Pack size if applicable")
    pack_unit: str | None = Field(default=None)
    vat_included: bool = Field(default=True)
    confidence: float = Field(ge=0, le=1, description="How confident this matches the target item")

    # Images
    image_url: str = Field(default="", description="Primary product image URL")
    image_urls: list[str] = Field(default_factory=list, description="Gallery of product images")

    # Stock & Availability
    availability: str = Field(default="unknown", description="Availability status")
    stock_status: str = Field(default="unknown")
    stock_quantity: int | None = Field(default=None)
    lead_time_days: int | None = Field(default=None)

    # Reviews & Ratings
    rating: float | None = Field(default=None)
    review_count: int | None = Field(default=None)

    # Shipping
    shipping_cost: float | None = Field(default=None)
    free_shipping_threshold: float | None = Field(default=None)
    shipping_policy: str = Field(default="unknown")

    # Product Details
    brand: str = Field(default="")
    sku: str = Field(default="")
    ean: str = Field(default="")
    specifications: dict[str, str] = Field(default_factory=dict)

    # Volume/Bulk Pricing
    volume_prices: list[dict[str, Any]] = Field(default_factory=list)

    # Metadata
    evidence: dict[str, str] = Field(default_factory=dict)
    scraped_at: str = Field(default="")
    source_method: str = Field(default="unknown")


class SearchResult(BaseModel):
    """Complete result of a web price search for a BoQ item."""
    quotes: list[WebQuote] = Field(default_factory=list)
    best_quote: WebQuote | None = None
    computed: dict[str, Any] | None = Field(default=None)
    reasoning: str = Field(default="")
    search_log: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

@dataclass
class SearchDeps:
    """Dependencies passed to the search pipeline at runtime."""
    description: str
    unit: str = "kom"
    quantity: float | None = None
    file_id: str = ""
    pricing_rules: PricingRules = field(default_factory=PricingRules)


# ---------------------------------------------------------------------------
# STEP 1: Build search queries (deterministic)
# ---------------------------------------------------------------------------

# Boilerplate Croatian phrases to strip from search queries
_BOILERPLATE_RE = re.compile(
    r"(dobava\s+i\s+ugradnja|nabava\s+i\s+ugradnja|dobava\s+i\s+montaža|"
    r"komplet\s+s\s+priborom|uključujući\s+sav\s+rad|prema\s+projektu|"
    r"sve\s+komplet|sa\s+svim\s+radom)",
    re.IGNORECASE,
)

_ITEM_NUMBER_RE = re.compile(r"^\s*\d+[\.\)]\s*")
_PARENS_RE = re.compile(r"\([^)]{30,}\)")  # Long parenthetical noise


def _build_search_queries(description: str) -> list[str]:
    """Generate 1-2 clean search queries from an item description."""
    # Strip item numbers, boilerplate, long parenthetical details
    q = _ITEM_NUMBER_RE.sub("", description)
    q = _BOILERPLATE_RE.sub("", q)
    q = _PARENS_RE.sub("", q)
    q = re.sub(r"\s+", " ", q).strip()

    if not q:
        q = description[:60]

    queries = []

    # Primary query: truncated to ~60 chars at word boundary
    if len(q) > 60:
        truncated = q[:60].rsplit(" ", 1)[0]
        queries.append(truncated)
    else:
        queries.append(q)

    # Secondary query: first 3-4 significant words (material focus)
    words = [w for w in q.split() if len(w) > 2]
    if len(words) > 4:
        short = " ".join(words[:4])
        if short != queries[0]:
            queries.append(short)

    return queries


# ---------------------------------------------------------------------------
# STEP 2: Search all domains (deterministic, parallel)
# ---------------------------------------------------------------------------

_FETCH_SEMAPHORE = asyncio.Semaphore(4)


async def _search_one_domain(
    domain_config: DomainConfig,
    query: str,
    search_log: list[str],
) -> list[dict[str, str]]:
    """Search a single domain, return candidate product links."""
    search_url = get_search_url(domain_config.domain, quote_plus(query))
    if not search_url:
        return []

    try:
        async with _FETCH_SEMAPHORE:
            result = await fetch_page(search_url)
        if result.status_code != 200:
            search_log.append(f"{domain_config.display_name}: HTTP {result.status_code}")
            return []

        links = extract_product_links(result.html, base_url=f"https://{domain_config.domain}")
        search_log.append(f"{domain_config.display_name}: {len(links)} product links for '{query[:40]}'")

        # Return top 3 per domain
        return [
            {"url": link["url"], "title": link["title"], "domain": domain_config.domain}
            for link in links[:3]
        ]
    except Exception as exc:
        search_log.append(f"{domain_config.display_name}: error — {exc}")
        return []


async def _search_all_domains(
    queries: list[str],
    search_log: list[str],
) -> list[dict[str, str]]:
    """Search all approved domains in parallel, return deduplicated candidate links."""
    domains = get_all_domains()
    tasks = [
        _search_one_domain(domain, query, search_log)
        for domain in domains
        for query in queries
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Flatten and deduplicate by URL
    seen_urls: set[str] = set()
    candidates: list[dict[str, str]] = []
    for result in results:
        if isinstance(result, Exception):
            continue
        for link in result:
            if link["url"] not in seen_urls:
                seen_urls.add(link["url"])
                candidates.append(link)

    search_log.append(f"Total unique candidates: {len(candidates)}")
    return candidates[:12]  # Cap at 12


# ---------------------------------------------------------------------------
# STEP 3: Fetch candidates and extract prices (deterministic, parallel)
# ---------------------------------------------------------------------------

async def _fetch_one_candidate(
    link: dict[str, str],
    search_log: list[str],
) -> list[WebQuote]:
    """Fetch a candidate page and extract prices."""
    url = link["url"]
    domain = link.get("domain", "")

    if not is_approved(url):
        return []

    try:
        async with _FETCH_SEMAPHORE:
            result = await fetch_page(url)
        if result.status_code != 200:
            return []

        prices = extract_prices(result.html)
        if not prices:
            return []

        metadata = extract_metadata(result.html)
        config = get_domain_config(url)
        vendor = config.display_name if config else "Unknown"

        quotes: list[WebQuote] = []
        for pf in prices[:3]:  # Top 3 prices per page
            nq = normalize_price(
                pf,
                vendor=vendor,
                domain_vat_included=config.vat_included if config else True,
            )
            quote = WebQuote(
                vendor=vendor,
                url=url,
                product_name=nq.product_name or link.get("title", ""),
                unit_price=nq.unit_price,
                currency=nq.currency,
                unit=nq.unit,
                pack_size=nq.pack_size,
                pack_unit=nq.pack_unit,
                vat_included=nq.vat_included,
                availability=nq.availability,
                confidence=nq.confidence,
                evidence={"raw_text": nq.evidence_snippet, "source_method": nq.source_method},
                image_url=nq.image_url,
                image_urls=metadata.images,
                rating=metadata.rating,
                review_count=metadata.review_count,
                stock_status=metadata.stock_status,
                stock_quantity=metadata.stock_quantity,
                shipping_cost=metadata.shipping_cost,
                free_shipping_threshold=metadata.free_shipping_threshold,
                brand=metadata.brand,
                sku=metadata.sku,
                ean=metadata.ean,
                specifications=metadata.specifications,
                source_method=nq.source_method,
            )
            quotes.append(quote)

        search_log.append(f"Extracted {len(quotes)} prices from {vendor} ({url[:60]})")
        return quotes

    except Exception as exc:
        search_log.append(f"Fetch error {url[:60]}: {exc}")
        return []


async def _fetch_all_candidates(
    links: list[dict[str, str]],
    search_log: list[str],
) -> list[WebQuote]:
    """Fetch all candidate pages in parallel, extract prices."""
    tasks = [_fetch_one_candidate(link, search_log) for link in links]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_quotes: list[WebQuote] = []
    for result in results:
        if isinstance(result, Exception):
            continue
        all_quotes.extend(result)

    search_log.append(f"Total web quotes: {len(all_quotes)}")
    return all_quotes


# ---------------------------------------------------------------------------
# STEP 4: RAG lookup (deterministic)
# ---------------------------------------------------------------------------

def _rag_lookup(description: str, file_id: str) -> list[dict[str, Any]]:
    """Search historical prices from ChromaDB. Returns filtered matches."""
    try:
        hits = rag_search(
            query_text=description,
            top_k=5,
            file_id_exclude=file_id or None,
        )
        return [
            {
                "id": h["id"],
                "similarity": h["similarity"],
                "unit_price": h["metadata"].get("unit_price", 0),
                "unit": h["metadata"].get("unit", ""),
                "file_id": h["metadata"].get("file_id", ""),
            }
            for h in hits
            if h["similarity"] >= 0.3 and (h["metadata"].get("unit_price") or 0) > 0
        ]
    except Exception as exc:
        logger.warning("RAG lookup failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# STEP 5: LLM ranking (single call, local model, no tools)
# ---------------------------------------------------------------------------

_RANKING_SYSTEM_PROMPT = (
    "You are a Croatian construction materials pricing specialist. "
    "You rank product candidates by how well they match a target BOQ item description. "
    "Consider: product name similarity, unit compatibility, price plausibility, "
    "and extraction confidence. Croatian terms: cijena=price, komad=piece, "
    "PDV=VAT (25%). Respond ONLY with valid JSON."
)

# PydanticAI agent for ranking — no tools, simple prompt-in prompt-out
_ranking_agent = Agent(
    get_model(),
    system_prompt=_RANKING_SYSTEM_PROMPT,
    retries=1,
    model_settings={"temperature": 0.1},
)


def _build_ranking_prompt(
    description: str,
    unit: str,
    web_quotes: list[WebQuote],
    rag_matches: list[dict[str, Any]],
) -> str:
    """Build the ranking prompt for the LLM."""
    lines = [
        f'Target item: "{description}" (unit: {unit})',
        "",
    ]

    if web_quotes:
        lines.append("Web candidates:")
        for i, q in enumerate(web_quotes, 1):
            lines.append(
                f"  {i}. [{q.vendor}] \"{q.product_name}\" — "
                f"€{q.unit_price:.2f}/{q.unit} — "
                f"{q.availability} — {q.source_method} conf={q.confidence:.1f}"
            )
        lines.append("")

    if rag_matches:
        lines.append("Historical matches:")
        for i, m in enumerate(rag_matches):
            lines.append(
                f"  {chr(65+i)}. similarity={m['similarity']:.2f} — "
                f"€{m['unit_price']:.2f}/{m['unit']} — file: {m['file_id']}"
            )
        lines.append("")

    if not web_quotes and not rag_matches:
        lines.append("No candidates found.")
        lines.append("")

    lines.append(
        "Return JSON: {\"rankings\": [{\"index\": 1, \"confidence\": 0.85, \"reason\": \"...\"}], "
        "\"best_index\": 1, \"reasoning\": \"brief overall summary\"}"
    )
    lines.append(
        "Index numbers refer to web candidates (1-based). "
        "Confidence 0-1 reflects match quality to the target item. "
        "If no candidate is a good match, set best_index to null."
    )

    return "\n".join(lines)


def _try_parse_json(text: str) -> dict | None:
    """Try multiple strategies to extract valid JSON from LLM output."""
    # Strategy 1: find outermost { ... } and parse directly
    json_match = re.search(r"\{[\s\S]*\}", text)
    if not json_match:
        return None

    raw = json_match.group()

    # Strategy 2: strip control characters and try
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 3: fix unescaped quotes inside string values
    # Replace internal double-quotes with single quotes (crude but effective)
    try:
        # Remove trailing commas before } or ]
        fixed = re.sub(r",\s*([}\]])", r"\1", cleaned)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Strategy 4: extract just the rankings array and best_index with regex
    try:
        data: dict[str, Any] = {}
        # Pull best_index
        bi_match = re.search(r'"best_index"\s*:\s*(\d+|null)', cleaned)
        if bi_match:
            val = bi_match.group(1)
            data["best_index"] = None if val == "null" else int(val)

        # Pull individual ranking objects: {"index": N, "confidence": F, ...}
        ranking_items = re.findall(
            r'\{\s*"index"\s*:\s*(\d+)\s*,\s*"confidence"\s*:\s*([\d.]+)',
            cleaned,
        )
        if ranking_items:
            data["rankings"] = [
                {"index": int(idx), "confidence": float(conf)}
                for idx, conf in ranking_items
            ]
            return data

        # Pull reasoning
        reason_match = re.search(r'"reasoning"\s*:\s*"([^"]*)"', cleaned)
        if reason_match:
            data["reasoning"] = reason_match.group(1)

        if data:
            return data
    except (ValueError, TypeError):
        pass

    return None


def _parse_ranking_response(
    text: str,
    web_quotes: list[WebQuote],
) -> tuple[list[WebQuote], str]:
    """Parse the LLM ranking response. Returns (ranked_quotes, reasoning)."""
    data = _try_parse_json(text)

    if data is None:
        logger.warning("Could not extract JSON from LLM response, using deterministic fallback")
        return _deterministic_rank(web_quotes), "LLM response unparseable, used deterministic ranking"

    reasoning = data.get("reasoning", "")
    best_index = data.get("best_index")
    rankings = data.get("rankings", [])

    # Apply LLM confidence scores to quotes
    applied = 0
    for ranking in rankings:
        idx = ranking.get("index")
        conf = ranking.get("confidence", 0)
        if isinstance(idx, int) and 1 <= idx <= len(web_quotes):
            web_quotes[idx - 1].confidence = float(conf)
            applied += 1

    if applied == 0:
        # LLM returned JSON but no usable rankings
        logger.warning("LLM returned JSON but no valid rankings, using deterministic fallback")
        return _deterministic_rank(web_quotes), reasoning or "No valid rankings in LLM response"

    # Sort by confidence descending
    web_quotes.sort(key=lambda q: q.confidence, reverse=True)

    return web_quotes, reasoning


async def _rank_candidates(
    description: str,
    unit: str,
    web_quotes: list[WebQuote],
    rag_matches: list[dict[str, Any]],
    search_log: list[str],
) -> tuple[list[WebQuote], str]:
    """Single LLM call to rank candidates. Falls back to deterministic ranking on failure."""
    if not web_quotes:
        return web_quotes, "No web candidates to rank"

    prompt = _build_ranking_prompt(description, unit, web_quotes, rag_matches)

    try:
        result = await run_with_settings("search", _ranking_agent, prompt)
        ranked, reasoning = _parse_ranking_response(result.output, web_quotes)
        search_log.append(f"LLM ranked {len(ranked)} candidates")
        return ranked, reasoning
    except Exception as exc:
        logger.warning("LLM ranking failed, using deterministic fallback: %s", exc)
        search_log.append(f"LLM ranking failed ({exc}), using deterministic fallback")
        return _deterministic_rank(web_quotes), f"Deterministic ranking (LLM unavailable: {exc})"


def _deterministic_rank(quotes: list[WebQuote]) -> list[WebQuote]:
    """Fallback: rank by extraction confidence, penalize for no LLM verification."""
    # Prefer jsonld/meta over css
    method_score = {"jsonld": 0.9, "meta": 0.8, "css": 0.6, "unknown": 0.4}
    for q in quotes:
        base = method_score.get(q.source_method, 0.4)
        q.confidence = round(base * 0.7, 2)  # Penalty for no LLM verification
    quotes.sort(key=lambda q: q.confidence, reverse=True)
    return quotes


# ---------------------------------------------------------------------------
# Public API (unchanged signature)
# ---------------------------------------------------------------------------

async def run_price_search(
    description: str,
    unit: str = "kom",
    quantity: float | None = None,
    file_id: str = "",
    pricing_rules: PricingRules | None = None,
) -> SearchResult:
    """Run the deterministic price search pipeline for a BoQ item.

    Parameters
    ----------
    description : str
        The BoQ item description to search for.
    unit : str
        Unit of measure (e.g. "m²", "kom", "m³").
    quantity : float, optional
        Quantity for total computation.
    file_id : str
        File ID to exclude from RAG search.
    pricing_rules : PricingRules, optional
        Rules for price computation.

    Returns
    -------
    SearchResult
        Structured result with quotes, best quote, computed total, and reasoning.
    """
    logger.info("Starting price search for: %s", description[:100])
    rules = pricing_rules or PricingRules()
    search_log: list[str] = []

    # STEP 1: Build search queries
    queries = _build_search_queries(description)
    search_log.append(f"Queries: {queries}")

    # STEP 2: Search all domains in parallel
    candidate_links = await _search_all_domains(queries, search_log)

    # STEP 3: Fetch candidates and extract prices (parallel)
    web_quotes = await _fetch_all_candidates(candidate_links, search_log)

    # STEP 4: RAG lookup (deterministic)
    rag_matches = _rag_lookup(description, file_id)
    search_log.append(f"RAG matches: {len(rag_matches)}")

    # STEP 5: LLM ranking (single call)
    ranked_quotes, reasoning = await _rank_candidates(
        description, unit, web_quotes, rag_matches, search_log,
    )

    # STEP 6: Finalize
    best_quote = ranked_quotes[0] if ranked_quotes else None

    # Compute total for best quote (deterministic)
    computed = None
    if best_quote and quantity:
        nq = NormalizedQuote(
            unit_price=best_quote.unit_price,
            currency=best_quote.currency,
            unit=best_quote.unit,
            pack_size=best_quote.pack_size,
            vat_included=best_quote.vat_included,
            vendor=best_quote.vendor,
        )
        ct = compute_total(nq, quantity, rules)
        computed = {
            "quantity": ct.quantity,
            "unit_price_ex_vat": ct.unit_price_ex_vat,
            "subtotal_ex_vat": ct.subtotal_ex_vat,
            "vat": ct.vat,
            "shipping_estimate": ct.shipping_estimate,
            "total": ct.total,
            "currency": ct.currency,
            "notes": ct.notes,
        }

    result = SearchResult(
        quotes=ranked_quotes,
        best_quote=best_quote,
        computed=computed,
        reasoning=reasoning,
        search_log=search_log,
    )

    logger.info(
        "Search complete: %d quotes, best=%s",
        len(ranked_quotes),
        best_quote.product_name[:50] if best_quote else "none",
    )
    return result
