"""Classifier agent: categorises a BoQ unit against the standard taxonomy.

Uses PydanticAI with two deterministic tools (match_taxonomy, check_schema)
that query the standard_units table in SQLite.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiosqlite
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.agent.schemas import ClassResult
from src.agent.tools.taxonomy import (
    match_taxonomy as _match_taxonomy,
    check_schema as _check_schema,
)
from src.config import LLM_BASE_URL, LLM_MODEL_NAME

CLASSIFIER_SYSTEM_PROMPT = """\
Ti si klasifikator građevinskih stavki. Tvoj zadatak je:
1. Primi opis građevinske stavke (radna stavka iz troškovnika).
2. Koristi alat `match_taxonomy` da pronađeš najprikladniju kategoriju iz baze standardnih jedinica.
3. Koristi alat `check_schema` da provjeriš poklapaju li se podstavke i mjerne jedinice s očekivanim standardom.
4. Na temelju rezultata odredi:
   - taxonomy_id i taxonomy_label najbolje kategorije
   - confidence (0.0-1.0) koliko si siguran u klasifikaciju
   - deviations: lista odstupanja od standarda (neočekivane podstavke, krive mjerne jedinice)
   - unmatched_rows: indeksi redaka koji se ne uklapaju

Odgovaraj ISKLJUČIVO u traženom JSON formatu.
"""


@dataclass
class ClassifierDeps:
    """Dependencies for the Classifier agent."""

    db: aiosqlite.Connection


def create_classifier_agent() -> Agent[ClassifierDeps, ClassResult]:
    """Factory: build and return a configured Classifier agent."""
    model = OpenAIChatModel(
        LLM_MODEL_NAME,
        provider=OpenAIProvider(base_url=LLM_BASE_URL, api_key="not-needed"),
    )

    agent: Agent[ClassifierDeps, ClassResult] = Agent(
        model=model,
        output_type=ClassResult,
        system_prompt=CLASSIFIER_SYSTEM_PROMPT,
        name="classifier",
    )

    @agent.tool
    async def match_taxonomy(
        ctx: RunContext[ClassifierDeps],
        description: str,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """Pretraži bazu standardnih jedinica po opisu. Vraća najbolje rezultate s ocjenom sličnosti."""
        return await _match_taxonomy(ctx.deps.db, description, limit)

    @agent.tool
    async def check_schema(
        ctx: RunContext[ClassifierDeps],
        taxonomy_id: str,
        rows: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Provjeri poklapaju li se podstavke i mjerne jedinice s očekivanim standardom za dani taxonomy_id."""
        return await _check_schema(ctx.deps.db, taxonomy_id, rows)

    return agent
