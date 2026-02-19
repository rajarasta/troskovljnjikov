"""Pricing Synthesizer Agent — produces 3 price points (low/mid/high) from
all evidence buckets: article catalog, web quotes, and historical BOQ prices.

This is a NEW agent that does NOT modify the existing pricer_agent.py.
The two agents coexist: pricer_agent produces single-point suggestions from
historical data only; this agent synthesizes from all three sources.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from pydantic_ai import Agent, RunContext

from app.models.pricing_pipeline import PriceSuggestion3
from app.services.llm_settings import get_model_for_agent, run_with_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


@dataclass
class SynthesizerDeps:
    """Dependencies passed to the pricing_synthesizer agent at runtime."""

    req_id: str
    description: str
    unit: str
    qty: float
    catalog_prices: list[dict] = field(default_factory=list)
    web_quotes: list[dict] = field(default_factory=list)
    historical_prices: list[dict] = field(default_factory=list)
    _synthesis_log: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a Croatian construction pricing analyst. Given evidence from three \
sources, produce exactly 3 price points for a construction material or work item.

Evidence sources:
1. **Article catalog** — internal supplier prices (net, ex-VAT)
2. **Web quotes** — current online prices from approved Croatian suppliers
3. **Historical BOQ** — prices from past projects (may be older)

Price point definitions:
- **low**: Conservative/budget estimate. Based on the lowest credible evidence. \
Use this when the buyer has leverage, buys in bulk, or can wait.
- **mid**: Most likely market price. Weighted by recency and evidence quality. \
This is what a typical procurement should expect to pay.
- **high**: Premium/safe estimate. Accounts for urgency, shipping, waste factor, \
or price spikes. Use this for worst-case budgeting.

Rules:
- All prices MUST be NET (ex-VAT) per unit
- Currency: EUR (convert if needed; Croatian PDV = 25%)
- Ignore prices that are 0, null, or clearly erroneous
- If sources conflict, explain the discrepancy in rationale
- Reference specific evidence in each point's rationale
- Use evidence_ids to trace which data points support each price
- If evidence is sparse, be honest about confidence (lower it)
- Each PricePoint needs: label, unit_price_net, currency, unit, rationale, evidence_ids

Confidence guidelines:
- 0.8-1.0: Strong evidence from multiple sources, prices converge
- 0.5-0.79: Moderate evidence, some extrapolation or single-source
- 0.2-0.49: Weak evidence, significant assumptions
- 0.0-0.19: Very little evidence, rough estimate\
"""


def _build_pricing_synthesizer_agent() -> Agent:
    """Create the agent with the current dynamically selected model."""
    current_model = get_model_for_agent("pricing_synthesizer")
    logger.debug("Building pricing_synthesizer_agent with model: %s", current_model)
    agent = Agent(
        current_model,
        output_type=PriceSuggestion3,
        deps_type=SynthesizerDeps,
        system_prompt=SYSTEM_PROMPT,
        retries=2,
        model_settings={"temperature": 0.2},
    )
    return agent


pricing_synthesizer_agent = _build_pricing_synthesizer_agent()


@pricing_synthesizer_agent.instructions
def build_synthesis_context(ctx: RunContext[SynthesizerDeps]) -> str:
    """Build the dynamic prompt with all evidence buckets."""
    deps = ctx.deps
    lines = [
        "ITEM TO PRICE:",
        f"  req_id: {deps.req_id}",
        f"  Description: {deps.description}",
        f"  Unit: {deps.unit}",
        f"  Quantity: {deps.qty}",
    ]

    # Catalog evidence
    lines.append(f"\nCATALOG EVIDENCE ({len(deps.catalog_prices)} entries):")
    if deps.catalog_prices:
        for i, c in enumerate(deps.catalog_prices, 1):
            price_str = f"{c.get('net_price', 'N/A')} {c.get('currency', 'EUR')}"
            lines.append(
                f"  C{i}. [{c.get('article_id', c.get('id', '?'))}] "
                f"{c.get('name', '')} | {c.get('unit', '')} | {price_str} "
                f"| relevance: {c.get('relevance_score', 'N/A')}"
            )
    else:
        lines.append("  No catalog data available.")

    # Web evidence
    lines.append(f"\nWEB QUOTE EVIDENCE ({len(deps.web_quotes)} entries):")
    if deps.web_quotes:
        for i, w in enumerate(deps.web_quotes, 1):
            vat_str = "(inc. VAT)" if w.get("vat_included") else "(ex. VAT)"
            lines.append(
                f"  W{i}. {w.get('vendor', '?')} | "
                f"{w.get('product_name', '')[:60]} | "
                f"{w.get('unit_price', 'N/A')} {w.get('currency', 'EUR')} {vat_str} | "
                f"conf: {w.get('confidence', 'N/A')}"
            )
    else:
        lines.append("  No web quotes available.")

    # Historical evidence
    lines.append(f"\nHISTORICAL BOQ EVIDENCE ({len(deps.historical_prices)} entries):")
    if deps.historical_prices:
        for i, h in enumerate(deps.historical_prices, 1):
            lines.append(
                f"  H{i}. [{h.get('source_boq_id', '?')}] "
                f"sim: {h.get('similarity', 0):.3f} | "
                f"{h.get('unit_price', 0)} EUR/{h.get('unit', '?')} | "
                f"date: {h.get('file_date', 'unknown')}"
            )
    else:
        lines.append("  No historical data available.")

    lines.append(
        "\nProduce exactly 3 PricePoints (low, mid, high) based on all available evidence. "
        "All prices must be NET (ex-VAT) per unit in EUR."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def synthesize_price(
    req_id: str,
    description: str,
    unit: str,
    qty: float,
    catalog_prices: list[dict],
    web_quotes: list[dict],
    historical_prices: list[dict],
) -> PriceSuggestion3:
    """Run the pricing_synthesizer agent to produce 3 price points.

    Parameters
    ----------
    req_id : str
        Requirement ID.
    description : str
        Material/item description.
    unit : str
        Unit of measure.
    qty : float
        Quantity needed.
    catalog_prices : list[dict]
        Article catalog candidates (from article_context).
    web_quotes : list[dict]
        Web quotes (from search_agent).
    historical_prices : list[dict]
        Historical BOQ prices (from RAG).

    Returns
    -------
    PriceSuggestion3
        Three price points with confidence and assumptions.
    """
    # Filter out zero/null prices from evidence
    catalog_clean = [
        c for c in catalog_prices
        if c.get("net_price") and c["net_price"] > 0
    ]
    web_clean = [
        w for w in web_quotes
        if w.get("unit_price") and w["unit_price"] > 0
    ]
    historical_clean = [
        h for h in historical_prices
        if h.get("unit_price") and h["unit_price"] > 0
    ]

    logger.info(
        "Synthesizing price for %s: %d catalog, %d web, %d historical evidence",
        req_id,
        len(catalog_clean),
        len(web_clean),
        len(historical_clean),
    )

    deps = SynthesizerDeps(
        req_id=req_id,
        description=description,
        unit=unit,
        qty=qty,
        catalog_prices=catalog_clean,
        web_quotes=web_clean,
        historical_prices=historical_clean,
    )

    result = await run_with_settings(
        "pricing_synthesizer",
        pricing_synthesizer_agent,
        "Produce 3 price points (low, mid, high) for this item based on "
        "all available evidence. All prices NET (ex-VAT) per unit in EUR.",
        deps=deps,
    )

    output = result.output
    logger.info(
        "Synthesizer returned: low=%.2f mid=%.2f high=%.2f conf=%.2f",
        output.points[0].unit_price_net,
        output.points[1].unit_price_net,
        output.points[2].unit_price_net,
        output.confidence,
    )

    return output
