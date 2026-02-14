"""
Pricer Agent - Suggests unit prices for BOQ items using LLM reasoning.

Given a BOQ item description, its unit, quantity, and a set of historical
matches with known prices, the agent suggests an appropriate unit price
with a confidence range and explanation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import settings

# ---------------------------------------------------------------------------
# Pydantic models for structured output
# ---------------------------------------------------------------------------


class PriceSuggestion(BaseModel):
    """Unit price suggestion with confidence and reasoning."""

    suggested_price: float = Field(
        description="Suggested unit price in the project currency",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the suggestion (0.0 to 1.0)",
    )
    reasoning: str = Field(
        description="Explanation of how the price was derived and key factors considered",
    )
    price_range_min: float = Field(
        description="Lower bound of the plausible price range",
    )
    price_range_max: float = Field(
        description="Upper bound of the plausible price range",
    )


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


@dataclass
class HistoricalPrice:
    """A single historical price data point."""

    description: str
    unit: str
    unit_price: float
    quantity: float | None = None
    total: float | None = None
    file_name: str = ""
    match_confidence: int = 0


@dataclass
class PricerDeps:
    """Dependencies passed to the pricer agent at runtime."""

    description: str
    """The BOQ item description to price."""

    unit: str
    """Unit of measure (m, m2, m3, kom, kg, etc.)."""

    quantity: float | None = None
    """Quantity of the item (may be None if unknown)."""

    historical_prices: list[HistoricalPrice] = field(default_factory=list)
    """Historical matches with known prices for reference."""


# ---------------------------------------------------------------------------
# LLM model & agent
# ---------------------------------------------------------------------------

_provider = OpenAIProvider(base_url=settings.LLM_BASE_URL)
_model = OpenAIChatModel(model_name=settings.LLM_MODEL_NAME, provider=_provider)

SYSTEM_PROMPT = """\
You are a construction cost estimator specializing in Croatian construction projects. \
Given a BOQ (Bill of Quantities) item and historical prices for similar items, suggest \
an appropriate unit price with reasoning.

Guidelines:
1. **Historical reference** - Weight prices from closely matching items more heavily. \
Items with higher match confidence should influence your estimate more.
2. **Price adjustments** - Consider whether historical prices need adjustment for:
   - Different specifications or quality levels
   - Scope differences (the same work type but different complexity)
   - Quantity effects (bulk discounts for large quantities, premiums for small ones)
3. **Unit consistency** - Ensure the suggested price is per the correct unit. \
If historical items use different units, convert appropriately.
4. **Outlier handling** - If one historical price is dramatically different from others, \
note it but don't let it dominate your estimate.
5. **Confidence** - Be honest about uncertainty:
   - 0.8-1.0: Strong historical evidence, closely matching items
   - 0.5-0.79: Moderate evidence, some extrapolation needed
   - 0.2-0.49: Weak evidence, significant uncertainty
   - 0.0-0.19: Very little evidence, rough estimate only
6. **Price range** - Provide a realistic min/max range that accounts for market \
variability and specification differences.

Always express prices as positive numbers. Use the same currency as the historical data.\
"""

pricer_agent = Agent(
    _model,
    output_type=PriceSuggestion,
    deps_type=PricerDeps,
    system_prompt=SYSTEM_PROMPT,
    retries=2,
    model_settings={"temperature": 0.1},
)


@pricer_agent.instructions
def build_pricing_context(ctx: RunContext[PricerDeps]) -> str:
    """Build the dynamic prompt with item details and historical prices."""
    deps = ctx.deps
    lines = [
        "ITEM TO PRICE:",
        f"  Description: {deps.description}",
        f"  Unit: {deps.unit}",
    ]
    if deps.quantity is not None:
        lines.append(f"  Quantity: {deps.quantity}")

    if deps.historical_prices:
        lines.append("\nHISTORICAL REFERENCE PRICES:")
        for i, hp in enumerate(deps.historical_prices, 1):
            qty_str = f", Qty: {hp.quantity}" if hp.quantity is not None else ""
            total_str = f", Total: {hp.total}" if hp.total is not None else ""
            lines.append(
                f"  {i}. [{hp.match_confidence}% match] "
                f"Unit Price: {hp.unit_price} / {hp.unit}{qty_str}{total_str}\n"
                f"     {hp.description}\n"
                f"     (from: {hp.file_name})"
            )
    else:
        lines.append("\nNo historical reference prices available.")
        lines.append("Provide your best estimate based on general construction knowledge.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def suggest_price(
    description: str,
    unit: str,
    quantity: float | None = None,
    historical_prices: list[dict] | None = None,
) -> PriceSuggestion:
    """Suggest a unit price for a BOQ item based on historical data.

    Parameters
    ----------
    description : str
        The BOQ item description.
    unit : str
        Unit of measure (e.g. "m2", "kom", "m3").
    quantity : float, optional
        Item quantity (used for context, not required).
    historical_prices : list[dict], optional
        Historical price data points. Each dict should have: description,
        unit, unit_price, and optionally: quantity, total, file_name,
        match_confidence.

    Returns
    -------
    PriceSuggestion
        Suggested price with confidence, reasoning, and price range.
    """
    hp_list: list[HistoricalPrice] = []
    if historical_prices:
        for hp in historical_prices:
            hp_list.append(
                HistoricalPrice(
                    description=hp.get("description", ""),
                    unit=hp.get("unit", ""),
                    unit_price=float(hp.get("unit_price", hp.get("unitPrice", 0))),
                    quantity=hp.get("quantity"),
                    total=hp.get("total"),
                    file_name=hp.get("file_name", hp.get("fileName", "")),
                    match_confidence=int(hp.get("match_confidence", hp.get("confidence", 0))),
                )
            )

    deps = PricerDeps(
        description=description,
        unit=unit,
        quantity=quantity,
        historical_prices=hp_list,
    )

    result = await pricer_agent.run(
        "Suggest a unit price for this BOQ item based on the historical data provided.",
        deps=deps,
    )
    return result.output
