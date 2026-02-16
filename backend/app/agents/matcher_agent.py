"""
Matcher Agents — Description Matcher + Price Comparator running in parallel.

The description_matcher focuses on semantic/description similarity.
The price_comparator focuses on price plausibility.
Both produce RankedMatch lists which are merged with weighted scoring.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import settings
from app.services.llm_settings import AgentDisabledError, get_settings, run_with_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models for structured output
# ---------------------------------------------------------------------------


class RankedMatch(BaseModel):
    """A single ranked match result."""

    item_id: str = Field(description="Unique identifier of the matched historical item")
    rank: int = Field(description="Rank position (1 = best match)")
    confidence: int = Field(
        ge=0,
        le=100,
        description="Confidence score 0-100 that this is a correct match",
    )
    reasoning: str = Field(
        description="Brief explanation of why this item was ranked here",
    )


class MatchRanking(BaseModel):
    """Complete ranking result for a set of candidate matches."""

    ranked_matches: list[RankedMatch] = Field(
        description="Candidate matches ordered by relevance (best first)",
    )
    reasoning: str = Field(
        description="Overall reasoning about the matching quality and key differentiators",
    )


# ---------------------------------------------------------------------------
# Dependencies (shared by both agents)
# ---------------------------------------------------------------------------


@dataclass
class MatcherDeps:
    """Dependencies passed to both matcher agents at runtime."""

    description: str
    """The target BOQ item description to match against."""

    candidates: list[dict]
    """
    Top fuzzy-match candidates from the search index.
    Each dict should have at minimum: id, description, unit, unitPrice, total,
    fileName, score.
    """


# ---------------------------------------------------------------------------
# Description Matcher Agent
# ---------------------------------------------------------------------------

_provider = OpenAIProvider(base_url=settings.LLM_BASE_URL)
_model = OpenAIChatModel(model_name=settings.LLM_MODEL_NAME, provider=_provider)

DESCRIPTION_SYSTEM_PROMPT = """\
You are a Croatian construction BOQ (Bill of Quantities) expert. \
You understand domain terms like "armatura", "oplata", "estrih", \
"hidroizolacija", "knauf", "fasada", and standard Croatian construction terminology.

Your task is to evaluate and rank fuzzy-matched historical items against a target \
item description based on DESCRIPTION SIMILARITY only.

When ranking matches consider:
1. **Semantic similarity** - Does the historical item describe the same type of work?
2. **Scope alignment** - Are the units and quantities comparable?
3. **Material specificity** - Do material specifications match (e.g. concrete grade, \
steel type, insulation thickness)?
4. **Croatian construction terminology** - Match domain-specific terms correctly.

Assign confidence scores:
- 90-100: Near-exact match (same work, same specifications)
- 70-89: Strong match (same work type, minor spec differences)
- 50-69: Moderate match (similar work, notable differences)
- 30-49: Weak match (related category but different specifics)
- 0-29: Poor match (different work type, only superficial similarity)

Return ALL candidates ranked from best to worst.\
"""

description_matcher_agent = Agent(
    _model,
    output_type=MatchRanking,
    deps_type=MatcherDeps,
    system_prompt=DESCRIPTION_SYSTEM_PROMPT,
    retries=2,
    model_settings={"temperature": 0.1},
)


@description_matcher_agent.instructions
def build_description_context(ctx: RunContext[MatcherDeps]) -> str:
    """Build the dynamic prompt with the target description and candidates."""
    deps = ctx.deps
    lines = [
        f"TARGET ITEM DESCRIPTION:\n{deps.description}\n",
        "CANDIDATE MATCHES (from fuzzy search):",
    ]
    for i, c in enumerate(deps.candidates, 1):
        lines.append(
            f"  {i}. [ID: {c.get('id', 'unknown')}] "
            f"(score: {c.get('score', 'N/A')}, unit: {c.get('unit', 'N/A')}, "
            f"file: {c.get('fileName', 'N/A')})\n"
            f"     {c.get('description', '')}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Price Comparator Agent
# ---------------------------------------------------------------------------

PRICE_SYSTEM_PROMPT = """\
You are a Croatian construction pricing expert specializing in BOQ (Bill of Quantities) \
cost analysis. You understand typical price ranges for Croatian construction work items, \
market variability, and how quantities affect unit pricing.

Your task is to evaluate and rank fuzzy-matched historical items against a target \
item based on PRICE PLAUSIBILITY only.

When ranking matches consider:
1. **Price plausibility** - Does the historical price make sense for this type of work?
2. **Unit consistency** - Are the pricing units compatible? Flag mismatches.
3. **Quantity effects** - Would quantity differences explain price differences?
4. **Outlier detection** - Identify prices that are suspiciously high or low.
5. **Market knowledge** - Is the price within expected ranges for Croatian construction?

Assign confidence scores:
- 90-100: Price is very plausible for this work type and quantity
- 70-89: Price is reasonable with minor concerns
- 50-69: Price is questionable, some red flags
- 30-49: Price seems unlikely, significant concerns
- 0-29: Price is implausible or incompatible

Return ALL candidates ranked from best to worst.\
"""

price_comparator_agent = Agent(
    _model,
    output_type=MatchRanking,
    deps_type=MatcherDeps,
    system_prompt=PRICE_SYSTEM_PROMPT,
    retries=2,
    model_settings={"temperature": 0.1},
)


@price_comparator_agent.instructions
def build_price_context(ctx: RunContext[MatcherDeps]) -> str:
    """Build the dynamic prompt emphasizing price data."""
    deps = ctx.deps
    lines = [
        f"TARGET ITEM DESCRIPTION:\n{deps.description}\n",
        "CANDIDATE MATCHES WITH PRICE DATA:",
    ]
    for i, c in enumerate(deps.candidates, 1):
        price_info = ""
        if c.get("unitPrice"):
            price_info = f", Unit Price: {c['unitPrice']}"
        if c.get("total"):
            price_info += f", Total: {c['total']}"
        lines.append(
            f"  {i}. [ID: {c.get('id', 'unknown')}] "
            f"(unit: {c.get('unit', 'N/A')}{price_info}, "
            f"file: {c.get('fileName', 'N/A')})\n"
            f"     {c.get('description', '')}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------

DESC_WEIGHT = 0.6
PRICE_WEIGHT = 0.4


def _merge_rankings(
    desc_result: MatchRanking | None,
    price_result: MatchRanking | None,
    candidate_ids: list[str],
) -> MatchRanking:
    """Merge description and price rankings with weighted confidence scores."""
    desc_by_id: dict[str, RankedMatch] = {}
    price_by_id: dict[str, RankedMatch] = {}

    if desc_result:
        desc_by_id = {m.item_id: m for m in desc_result.ranked_matches}
    if price_result:
        price_by_id = {m.item_id: m for m in price_result.ranked_matches}

    all_ids = set(desc_by_id.keys()) | set(price_by_id.keys()) | set(candidate_ids)

    merged: list[RankedMatch] = []
    for item_id in all_ids:
        desc_match = desc_by_id.get(item_id)
        price_match = price_by_id.get(item_id)

        if desc_match and price_match:
            conf = int(desc_match.confidence * DESC_WEIGHT + price_match.confidence * PRICE_WEIGHT)
            reasoning = f"Description: {desc_match.reasoning} | Price: {price_match.reasoning}"
        elif desc_match:
            conf = desc_match.confidence
            reasoning = f"Description: {desc_match.reasoning}"
        elif price_match:
            conf = price_match.confidence
            reasoning = f"Price: {price_match.reasoning}"
        else:
            conf = 0
            reasoning = "Not evaluated by either agent"

        merged.append(RankedMatch(
            item_id=item_id,
            rank=0,
            confidence=max(0, min(100, conf)),
            reasoning=reasoning,
        ))

    merged.sort(key=lambda m: m.confidence, reverse=True)
    for i, m in enumerate(merged, 1):
        m.rank = i

    reasoning_parts = []
    if desc_result:
        reasoning_parts.append(f"Description analysis: {desc_result.reasoning}")
    if price_result:
        reasoning_parts.append(f"Price analysis: {price_result.reasoning}")

    return MatchRanking(
        ranked_matches=merged,
        reasoning=" | ".join(reasoning_parts) if reasoning_parts else "No agents were enabled",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def rank_matches(
    description: str,
    candidates: list[dict],
) -> MatchRanking:
    """Rank fuzzy-matched historical items using parallel description + price agents.

    If one agent is disabled, only the other runs. If both disabled, returns
    empty ranking.
    """
    capped = candidates[:10]
    deps = MatcherDeps(description=description, candidates=capped)
    candidate_ids = [c.get("id", "unknown") for c in capped]

    tasks: list[tuple[str, asyncio.Task]] = []

    desc_settings = get_settings("description_matcher")
    price_settings = get_settings("price_comparator")

    if desc_settings.get("enabled", True):
        tasks.append((
            "desc",
            asyncio.create_task(run_with_settings(
                "description_matcher", description_matcher_agent,
                "Rank the candidate matches for the target item based on description similarity.",
                deps=deps,
            )),
        ))

    if price_settings.get("enabled", True):
        tasks.append((
            "price",
            asyncio.create_task(run_with_settings(
                "price_comparator", price_comparator_agent,
                "Rank the candidate matches for the target item based on price plausibility.",
                deps=deps,
            )),
        ))

    if not tasks:
        return MatchRanking(
            ranked_matches=[],
            reasoning="Both description_matcher and price_comparator agents are disabled",
        )

    results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)

    desc_result: MatchRanking | None = None
    price_result: MatchRanking | None = None

    for (label, _task), result in zip(tasks, results):
        if isinstance(result, Exception):
            if not isinstance(result, AgentDisabledError):
                logger.warning("Matcher agent '%s' failed: %s", label, result)
            continue
        if label == "desc":
            desc_result = result.output
        elif label == "price":
            price_result = result.output

    return _merge_rankings(desc_result, price_result, candidate_ids)
