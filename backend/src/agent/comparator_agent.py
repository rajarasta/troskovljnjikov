"""Comparator agent: finds and scores historic BoQ matches.

Uses PydanticAI with two deterministic tools (search_historic, fetch_similar)
that query historic_units / historic_lines tables in SQLite.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import aiosqlite
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.agent.schemas import ClassResult, CompResult
from src.agent.tools.historic import (
    search_historic_by_taxonomy as _search_historic_by_taxonomy,
    fetch_similar as _fetch_similar,
)
from src.config import LLM_BASE_URL, LLM_MODEL_NAME

COMPARATOR_SYSTEM_PROMPT = """\
Ti si agent za usporedbu građevinskih stavki s historijskim podacima. Tvoj zadatak je:
1. Primi klasifikaciju stavke (taxonomy_id, taxonomy_label, confidence).
2. Koristi alat `search_historic` da pronađeš slične historijske stavke u bazi.
3. Koristi alat `fetch_similar` da dohvatiš potpune podatke za pojedinu historijsku stavku.
4. Za svaku pronađenu stavku odredi:
   - match_confidence: koliko se historijska stavka poklapa s trenutnom
   - confidence_breakdown: text_similarity, unit_match, hierarchy_match, description_overlap
   - matching_sub_items, missing_sub_items, extra_sub_items
   - qty_delta_pct: postotna razlika u količinama
   - matched_lines: pripadajuće cjenovne linije
5. Generiraj kratki sažetak usporedbe.

Odgovaraj ISKLJUČIVO u traženom JSON formatu.
"""


@dataclass
class ComparatorDeps:
    """Dependencies for the Comparator agent."""

    db: aiosqlite.Connection
    classification: ClassResult


def create_comparator_agent() -> Agent[ComparatorDeps, CompResult]:
    """Factory: build and return a configured Comparator agent."""
    model = OpenAIChatModel(
        LLM_MODEL_NAME,
        provider=OpenAIProvider(base_url=LLM_BASE_URL, api_key="not-needed"),
    )

    agent: Agent[ComparatorDeps, CompResult] = Agent(
        model=model,
        output_type=CompResult,
        system_prompt=COMPARATOR_SYSTEM_PROMPT,
        name="comparator",
    )

    @agent.tool
    async def search_historic(
        ctx: RunContext[ComparatorDeps],
        taxonomy_id: str,
        keywords: str = "",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Pretraži historijske stavke filtrirane po taxonomy_id, opcionalno s FTS ključnim riječima."""
        return await _search_historic_by_taxonomy(ctx.deps.db, taxonomy_id, keywords, limit)

    @agent.tool
    async def fetch_similar(
        ctx: RunContext[ComparatorDeps],
        unit_id: int,
    ) -> Optional[dict[str, Any]]:
        """Dohvati potpune podatke za jednu historijsku stavku po ID-u."""
        return await _fetch_similar(ctx.deps.db, unit_id)

    return agent
