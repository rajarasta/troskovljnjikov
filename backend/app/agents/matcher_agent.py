"""
Matcher Agent - Ranks fuzzy matches for BOQ items using LLM reasoning.

Given a target item description and a list of candidate matches from the
historical database, the agent ranks them by relevance and provides
per-match confidence scores and reasoning.
"""
from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import settings

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
# Dependencies
# ---------------------------------------------------------------------------


@dataclass
class MatcherDeps:
    """Dependencies passed to the matcher agent at runtime."""

    description: str
    """The target BOQ item description to match against."""

    candidates: list[dict]
    """
    Top fuzzy-match candidates from the search index.
    Each dict should have at minimum: id, description, unit, unitPrice, total,
    fileName, score.
    """


# ---------------------------------------------------------------------------
# LLM model & agent
# ---------------------------------------------------------------------------

_provider = OpenAIProvider(base_url=settings.LLM_BASE_URL)
_model = OpenAIChatModel(model_name=settings.LLM_MODEL_NAME, provider=_provider)

SYSTEM_PROMPT = """\
You are a Croatian construction BOQ (Bill of Quantities) expert. Your task is to \
evaluate and rank fuzzy-matched historical items against a target item description.

When ranking matches consider:
1. **Semantic similarity** - Does the historical item describe the same type of work?
2. **Scope alignment** - Are the units and quantities comparable?
3. **Material specificity** - Do material specifications match (e.g. concrete grade, \
steel type, insulation thickness)?
4. **Croatian construction terminology** - Understand domain terms like "armatura", \
"oplata", "estrih", "hidroizolacija", "knauf", "fasada", etc.
5. **Price plausibility** - Does the historical price make sense for this type of work?

Assign confidence scores:
- 90-100: Near-exact match (same work, same specifications)
- 70-89: Strong match (same work type, minor spec differences)
- 50-69: Moderate match (similar work, notable differences)
- 30-49: Weak match (related category but different specifics)
- 0-29: Poor match (different work type, only superficial similarity)

Return ALL candidates ranked from best to worst.\
"""

matcher_agent = Agent(
    _model,
    output_type=MatchRanking,
    deps_type=MatcherDeps,
    system_prompt=SYSTEM_PROMPT,
    retries=2,
    model_settings={"temperature": 0.1},
)


@matcher_agent.instructions
def build_match_context(ctx: RunContext[MatcherDeps]) -> str:
    """Build the dynamic prompt with the target description and candidates."""
    deps = ctx.deps
    lines = [
        f"TARGET ITEM DESCRIPTION:\n{deps.description}\n",
        "CANDIDATE MATCHES (from fuzzy search):",
    ]
    for i, c in enumerate(deps.candidates, 1):
        price_info = ""
        if c.get("unitPrice"):
            price_info = f", Unit Price: {c['unitPrice']}"
        if c.get("total"):
            price_info += f", Total: {c['total']}"
        lines.append(
            f"  {i}. [ID: {c.get('id', 'unknown')}] "
            f"(score: {c.get('score', 'N/A')}, unit: {c.get('unit', 'N/A')}"
            f"{price_info}, file: {c.get('fileName', 'N/A')})\n"
            f"     {c.get('description', '')}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def rank_matches(
    description: str,
    candidates: list[dict],
) -> MatchRanking:
    """Rank fuzzy-matched historical items for a BOQ description.

    Parameters
    ----------
    description : str
        The target BOQ item description to find matches for.
    candidates : list[dict]
        Top fuzzy-match candidates (up to 10) from the search index. Each dict
        should contain at least: id, description, unit, unitPrice, total,
        fileName, score.

    Returns
    -------
    MatchRanking
        Ranked matches with confidence scores and reasoning.
    """
    deps = MatcherDeps(description=description, candidates=candidates[:10])

    result = await matcher_agent.run(
        "Rank the candidate matches for the target item. "
        "Evaluate each candidate and assign confidence scores.",
        deps=deps,
    )
    return result.output
