"""Article Context Agent — maps MaterialRequirements to article catalog candidates.

The orchestrator prefetches catalog results deterministically, then this agent
reasons about which articles best match each requirement and why.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from app.models.pricing_pipeline import CatalogMatch
from app.services.llm_settings import get_model_for_agent, run_with_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------


class EnrichedRequirements(BaseModel):
    """Complete result of article catalog enrichment."""

    enriched: list[CatalogMatch] = Field(default_factory=list)
    reasoning: str = ""


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


@dataclass
class ArticleContextDeps:
    """Dependencies passed to the article_context agent at runtime."""

    requirements: list[dict] = field(default_factory=list)
    catalog_prefetch: dict[str, list[dict]] = field(default_factory=dict)
    _enrichment_log: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a Croatian construction materials catalog specialist. Given a list of \
material requirements and pre-fetched catalog search results, your task is to \
determine which catalog articles best match each requirement.

For each requirement:
1. Review the pre-fetched catalog candidates (provided in context)
2. Use catalog_lookup to search for additional matches if needed
3. Use catalog_get to inspect specific articles for details
4. Rank candidates by relevance and assign a relevance_score (0-1)
5. Explain why each candidate matches or doesn't

Scoring guidelines:
- 0.9-1.0: Exact product match (same material, same specs)
- 0.7-0.89: Strong match (same category, minor differences)
- 0.5-0.69: Moderate match (similar product, different specs)
- 0.3-0.49: Weak match (related category)
- 0.0-0.29: Poor match (different product)

Important:
- Never invent article IDs — only use IDs from catalog results
- If no good match exists, return an empty candidates list for that requirement
- Note unit mismatches (e.g. catalog sells by kg, requirement is per m2)
- Croatian terminology: cijev = pipe, ploča = board, cement, armatura = rebar\
"""


def _build_article_context_agent() -> Agent:
    """Create the agent with the current dynamically selected model."""
    current_model = get_model_for_agent("article_context")
    logger.debug("Building article_context_agent with model: %s", current_model)
    agent = Agent(
        current_model,
        output_type=EnrichedRequirements,
        deps_type=ArticleContextDeps,
        system_prompt=SYSTEM_PROMPT,
        retries=2,
        model_settings={"temperature": 0.1},
    )
    return agent


article_context_agent = _build_article_context_agent()


@article_context_agent.instructions
def build_article_context(ctx: RunContext[ArticleContextDeps]) -> str:
    """Build the dynamic prompt with requirements and prefetched catalog data."""
    deps = ctx.deps
    lines = ["MATERIAL REQUIREMENTS TO MATCH:"]

    for req in deps.requirements:
        req_id = req.get("req_id", "?")
        desc = req.get("description", "")
        qty = req.get("qty", 0)
        unit = req.get("unit", "")
        lines.append(f"\n--- {req_id}: {desc} ({qty} {unit}) ---")

        # Show prefetched catalog candidates
        candidates = deps.catalog_prefetch.get(req_id, [])
        if candidates:
            lines.append(f"  Pre-fetched catalog candidates ({len(candidates)}):")
            for i, c in enumerate(candidates, 1):
                price_str = f"{c.get('net_price', 'N/A')} {c.get('currency', 'EUR')}" if c.get('net_price') else "no price"
                lines.append(
                    f"    {i}. [{c.get('id', '?')}] {c.get('name', '')} "
                    f"| {c.get('unit', '')} | {price_str}"
                )
        else:
            lines.append("  No pre-fetched candidates found.")

    lines.append(
        "\nMatch each requirement to the best catalog articles. "
        "Use catalog_lookup for additional searches if the pre-fetched results are insufficient."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@article_context_agent.tool
async def catalog_lookup(
    ctx: RunContext[ArticleContextDeps], query: str, top_k: int = 10
) -> str:
    """Search the article catalog by keywords.

    Args:
        query: Search query (product name, material description).
        top_k: Maximum number of results to return.

    Returns:
        JSON array of matching articles.
    """
    from app.services.catalog_service import catalog_lookup as _lookup

    results = _lookup(query, top_k)
    ctx.deps._enrichment_log.append(f"Catalog lookup: {query} -> {len(results)} results")
    return json.dumps(results, ensure_ascii=False)


@article_context_agent.tool
async def catalog_get(ctx: RunContext[ArticleContextDeps], article_id: str) -> str:
    """Get detailed information about a specific article.

    Args:
        article_id: The article ID to look up.

    Returns:
        JSON object with article details, or error if not found.
    """
    from app.services.catalog_service import catalog_get as _get

    result = _get(article_id)
    ctx.deps._enrichment_log.append(f"Catalog get: {article_id}")
    return json.dumps(result or {"error": "Article not found"}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def enrich_with_catalog(
    requirements: list,
    catalog_prefetch: dict[str, list[dict]],
) -> list[CatalogMatch]:
    """Map requirements to catalog articles using deterministic matching.

    Uses pre-fetched catalog results ranked by match quality.
    The LLM agent is available for future use but the deterministic approach
    works well since catalog_lookup already provides ranked results.

    Parameters
    ----------
    requirements : list
        List of MaterialRequirement objects (or dicts).
    catalog_prefetch : dict
        Pre-queried catalog results, keyed by req_id.

    Returns
    -------
    list[CatalogMatch]
        One CatalogMatch per requirement.
    """
    from app.models.pricing_pipeline import ArticleCandidate

    logger.info(
        "Starting catalog enrichment for %d requirements", len(requirements)
    )

    enriched: list[CatalogMatch] = []

    for req in requirements:
        req_id = req.req_id if hasattr(req, "req_id") else req.get("req_id", "")
        candidates = catalog_prefetch.get(req_id, [])

        article_candidates = []
        for i, c in enumerate(candidates[:5]):  # top 5 candidates
            # Simple scoring: exact ID match = 1.0, position-based otherwise
            score = 1.0 if c.get("id") == (req.description if hasattr(req, "description") else req.get("description", "")) else max(0.3, 0.9 - i * 0.15)

            article_candidates.append(ArticleCandidate(
                article_id=c.get("id", ""),
                name=c.get("name", ""),
                unit=c.get("unit", ""),
                net_price=c.get("net_price"),
                relevance_score=score,
                match_reason=f"catalog match #{i+1}",
            ))

        enriched.append(CatalogMatch(
            req_id=req_id,
            article_candidates=article_candidates,
        ))

    logger.info("Catalog enrichment: %d/%d with candidates",
                sum(1 for e in enriched if e.article_candidates), len(enriched))

    return enriched
