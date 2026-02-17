"""
Search Agent - PydanticAI agent for web price search on approved supplier domains.

Given a BoQ item description, searches pre-approved websites, extracts product prices,
and returns structured quotes. The agent decides *what* to search and *which* results
match; deterministic code handles parsing, normalization, and total computation.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote_plus

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicChatModel

from app.config import settings
from app.services.llm_settings import run_with_settings
from app.services.domain_registry import (
    DomainConfig,
    get_all_domains,
    get_domain_config,
    get_search_url,
    is_approved,
)
from app.services.price_extractor import PriceField, extract_prices, extract_product_links
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
# Structured output models
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
    stock_status: str = Field(default="unknown", description="in_stock, low_stock, out_of_stock, discontinued")
    stock_quantity: int | None = Field(default=None, description="Actual quantity in stock if available")
    lead_time_days: int | None = Field(default=None, description="Estimated delivery time in days")

    # Reviews & Ratings
    rating: float | None = Field(default=None, description="Average rating (0-5 scale)")
    review_count: int | None = Field(default=None, description="Number of customer reviews")

    # Shipping
    shipping_cost: float | None = Field(default=None, description="Shipping cost in currency")
    free_shipping_threshold: float | None = Field(default=None, description="Order amount for free shipping")
    shipping_policy: str = Field(default="unknown", description="free, paid, pickup_only")

    # Product Details
    brand: str = Field(default="", description="Product brand/manufacturer")
    sku: str = Field(default="", description="SKU/product code")
    ean: str = Field(default="", description="EAN barcode")
    specifications: dict[str, str] = Field(default_factory=dict, description="Product specs (material, dimensions, weight, etc)")

    # Volume/Bulk Pricing
    volume_prices: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Volume pricing: [{min_qty: 10, price: 8.50}, ...]"
    )

    # Metadata
    evidence: dict[str, str] = Field(default_factory=dict, description="Evidence: raw_text, snippet, source_method")
    scraped_at: str = Field(default="", description="ISO timestamp when scraped")
    source_method: str = Field(default="unknown", description="jsonld, meta, css, llm")


class SearchResult(BaseModel):
    """Complete result of a web price search for a BoQ item."""
    quotes: list[WebQuote] = Field(default_factory=list)
    best_quote: WebQuote | None = None
    computed: dict[str, Any] | None = Field(default=None, description="Computed total for best quote")
    reasoning: str = Field(default="", description="Agent's reasoning about the search results")
    search_log: list[str] = Field(default_factory=list, description="Step-by-step trace")


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

@dataclass
class SearchDeps:
    """Dependencies passed to the search agent at runtime."""
    description: str
    unit: str = "kom"
    quantity: float | None = None
    file_id: str = ""
    pricing_rules: PricingRules = field(default_factory=PricingRules)
    # Populated at runtime
    _search_log: list[str] = field(default_factory=list)
    _quotes: list[WebQuote] = field(default_factory=list)


# ---------------------------------------------------------------------------
# LLM model & agent
# ---------------------------------------------------------------------------

_model = AnthropicChatModel(model_name=settings.LLM_MODEL_NAME)

SYSTEM_PROMPT = """\
You are a Croatian construction materials price search specialist. Your task is to \
find current prices for construction materials and services on approved supplier websites.

You have access to these tools:
- search_domain: Search a specific approved domain for products
- fetch_and_extract: Fetch a product page and extract price information
- rag_lookup: Look up historical prices from internal database

Workflow:
1. Analyze the item description to understand what product/material to search for
2. Generate good search queries (Croatian construction terms)
3. Search each approved domain using search_domain
4. For promising candidates, use fetch_and_extract to get detailed pricing
5. Compare results and reason about which quotes best match the target item

Important:
- Only search approved domains (bauhaus.hr, gradja.hr, wuerth, era-commerce.hr)
- Report confidence honestly — don't guess if you can't find a match
- Consider unit compatibility (m², kom, m, kg, etc.)
- Croatian terminology: cijena = price, komad = piece, količina = quantity
- PDV = VAT (25% in Croatia), most prices include PDV\
"""

search_agent = Agent(
    _model,
    output_type=SearchResult,
    deps_type=SearchDeps,
    system_prompt=SYSTEM_PROMPT,
    retries=2,
    model_settings={"temperature": 0.1},
)


@search_agent.instructions
def build_search_context(ctx: RunContext[SearchDeps]) -> str:
    """Build the dynamic prompt with item details and available domains."""
    deps = ctx.deps
    domains = get_all_domains()
    domain_list = "\n".join(
        f"  - {d.display_name} ({d.domain}) — search: {d.search_url_template is not None}"
        for d in domains
    )
    lines = [
        "TARGET ITEM TO SEARCH:",
        f"  Description: {deps.description}",
        f"  Unit: {deps.unit}",
    ]
    if deps.quantity is not None:
        lines.append(f"  Quantity: {deps.quantity}")
    lines.append(f"\nAPPROVED DOMAINS:\n{domain_list}")
    lines.append(
        "\nSearch for this item on the approved domains. "
        "Use search_domain for each domain, then fetch_and_extract for promising results."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent tools
# ---------------------------------------------------------------------------

@search_agent.tool
async def search_domain(
    ctx: RunContext[SearchDeps],
    query: str,
    domain: str,
) -> str:
    """Search an approved domain for products matching the query.

    Args:
        query: Search query (product name, material description).
        domain: The domain to search (e.g. "www.bauhaus.hr").

    Returns:
        JSON-formatted list of product candidates with URLs and titles.
    """
    import json

    logger.debug(f"🔍 [Tool] search_domain called: domain={domain}, query={query[:50]}")
    ctx.deps._search_log.append(f"Searching {domain} for: {query}")

    search_url = get_search_url(domain, quote_plus(query))
    if not search_url:
        return json.dumps({"error": f"No search URL template for {domain}", "candidates": []})

    try:
        result = await fetch_page(search_url)
        if result.status_code != 200:
            return json.dumps({"error": f"HTTP {result.status_code}", "candidates": []})

        links = extract_product_links(result.html, base_url=f"https://{domain}")

        # Also try to extract prices directly from the listing page
        listing_prices = extract_prices(result.html)

        candidates = []
        for link in links[:8]:  # Cap at 8 candidates per domain
            candidates.append({
                "url": link["url"],
                "title": link["title"],
            })

        ctx.deps._search_log.append(f"Found {len(candidates)} candidates on {domain}")

        return json.dumps({
            "domain": domain,
            "search_url": search_url,
            "candidates": candidates,
            "listing_prices_count": len(listing_prices),
        })
    except Exception as exc:
        ctx.deps._search_log.append(f"Error searching {domain}: {exc}")
        return json.dumps({"error": str(exc), "candidates": []})


@search_agent.tool
async def fetch_and_extract(
    ctx: RunContext[SearchDeps],
    url: str,
    product_hint: str = "",
) -> str:
    """Fetch a product page and extract price information.

    Args:
        url: The product page URL to fetch (must be on an approved domain).
        product_hint: Optional hint about what product to look for on the page.

    Returns:
        JSON with extracted prices, product name, availability.
    """
    import json

    logger.debug(f"🔍 [Tool] fetch_and_extract called: url={url[:80]}")
    if not is_approved(url):
        return json.dumps({"error": f"URL not on approved domain: {url}"})

    ctx.deps._search_log.append(f"Fetching: {url}")

    try:
        result = await fetch_page(url)
        if result.status_code != 200:
            return json.dumps({"error": f"HTTP {result.status_code}"})

        prices = extract_prices(result.html, product_hint)

        if not prices:
            ctx.deps._search_log.append(f"No prices found on {url}")
            return json.dumps({"url": url, "prices": [], "text_snippet": result.text[:500]})

        # Normalize prices
        config = get_domain_config(url)
        vendor = config.display_name if config else "Unknown"

        price_data = []
        for pf in prices[:5]:  # Cap at 5 prices per page
            nq = normalize_price(pf, vendor=vendor, domain_vat_included=config.vat_included if config else True)
            quote = WebQuote(
                vendor=vendor,
                url=url,
                product_name=nq.product_name or product_hint,
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
            )
            ctx.deps._quotes.append(quote)
            price_data.append({
                "product_name": nq.product_name,
                "unit_price": nq.unit_price,
                "currency": nq.currency,
                "unit": nq.unit,
                "vat_included": nq.vat_included,
                "availability": nq.availability,
                "confidence": nq.confidence,
                "source_method": nq.source_method,
            })

        ctx.deps._search_log.append(f"Extracted {len(price_data)} prices from {url}")

        return json.dumps({
            "url": url,
            "vendor": vendor,
            "prices": price_data,
        })
    except Exception as exc:
        ctx.deps._search_log.append(f"Error fetching {url}: {exc}")
        return json.dumps({"error": str(exc)})


@search_agent.tool
async def rag_lookup(
    ctx: RunContext[SearchDeps],
    query: str,
) -> str:
    """Look up historical prices from the internal BoQ database.

    Args:
        query: Search query for historical items.

    Returns:
        JSON with matching historical items and their prices.
    """
    import json

    logger.debug(f"🔍 [Tool] rag_lookup called: query={query[:50]}")
    ctx.deps._search_log.append(f"RAG lookup: {query}")

    try:
        hits = rag_search(
            query_text=query,
            top_k=5,
            file_id_exclude=ctx.deps.file_id or None,
        )

        results = []
        for h in hits:
            if h["similarity"] >= settings.MATCH_THRESHOLD:
                results.append({
                    "id": h["id"],
                    "similarity": h["similarity"],
                    "unit_price": h["metadata"].get("unit_price", 0),
                    "unit": h["metadata"].get("unit", ""),
                    "file_id": h["metadata"].get("file_id", ""),
                })

        return json.dumps({"matches": results, "count": len(results)})
    except Exception as exc:
        return json.dumps({"error": str(exc), "matches": []})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_price_search(
    description: str,
    unit: str = "kom",
    quantity: float | None = None,
    file_id: str = "",
    pricing_rules: PricingRules | None = None,
) -> SearchResult:
    """Run the price search agent for a BoQ item.

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
    logger.info(f"🔍 Starting price search for: {description[:100]}")
    rules = pricing_rules or PricingRules()
    deps = SearchDeps(
        description=description,
        unit=unit,
        quantity=quantity,
        file_id=file_id,
        pricing_rules=rules,
    )

    result = await run_with_settings(
        "search",
        search_agent,
        "Search for the target item on approved supplier domains. "
        "Find the best price matches, extract pricing data, and compare with historical data. "
        "Return your findings with confidence scores and reasoning.",
        deps=deps,
    )

    output = result.output
    logger.info(f"🔍 Search agent returned: quotes={len(output.quotes)}, search_log_entries={len(output.search_log)}")

    # Merge tool-collected quotes into the result
    if deps._quotes and not output.quotes:
        output.quotes = deps._quotes

    # Merge search log
    if deps._search_log:
        output.search_log = deps._search_log + output.search_log

    # Pick best quote if agent didn't
    if output.quotes and output.best_quote is None:
        output.best_quote = max(output.quotes, key=lambda q: q.confidence)

    # Compute total for best quote (deterministic)
    if output.best_quote and quantity:
        nq = NormalizedQuote(
            unit_price=output.best_quote.unit_price,
            currency=output.best_quote.currency,
            unit=output.best_quote.unit,
            pack_size=output.best_quote.pack_size,
            vat_included=output.best_quote.vat_included,
            vendor=output.best_quote.vendor,
        )
        ct = compute_total(nq, quantity, rules)
        output.computed = {
            "quantity": ct.quantity,
            "unit_price_ex_vat": ct.unit_price_ex_vat,
            "subtotal_ex_vat": ct.subtotal_ex_vat,
            "vat": ct.vat,
            "shipping_estimate": ct.shipping_estimate,
            "total": ct.total,
            "currency": ct.currency,
            "notes": ct.notes,
        }

    return output
