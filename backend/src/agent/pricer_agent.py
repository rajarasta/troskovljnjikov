"""Pricer agent: generates price suggestions for BoQ line items.

Uses PydanticAI with three tools:
- diff_historic (deterministic line-item alignment)
- search_web (live market price lookup)
- summarize (LLM-based text summarisation)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.agent.schemas import CompResult, PriceResult
from src.agent.tools.pricing import diff_historic as _diff_historic
from src.agent.tools.external import (
    search_web as _search_web,
    summarize as _summarize,
)
from src.config import LLM_BASE_URL, LLM_MODEL_NAME

PRICER_SYSTEM_PROMPT = """\
Ti si agent za određivanje cijena građevinskih stavki. Tvoj zadatak je:
1. Primi rezultate usporedbe s historijskim podacima (comparison).
2. Koristi alat `diff_historic` da usporediš trenutne podstavke s historijskim cjenovnim linijama.
3. Po potrebi koristi alat `search_web` da pronađeš aktualne tržišne cijene materijala i radova.
4. Koristi alat `summarize` da sažmeš pronađene informacije o cijenama.
5. Za svaku cjenovnu liniju predloži:
   - suggested_price: preporučenu jediničnu cijenu
   - confidence (0.0-1.0): koliko si siguran u prijedlog
   - price_range: raspon cijena (low, high, median)
   - reasoning: kratko obrazloženje prijedloga
6. Generiraj overall_reasoning koji objašnjava ukupni pristup cijenama.

Odgovaraj ISKLJUČIVO u traženom JSON formatu.
"""


@dataclass
class PricerDeps:
    """Dependencies for the Pricer agent."""

    comparison: CompResult


def create_pricer_agent() -> Agent[PricerDeps, PriceResult]:
    """Factory: build and return a configured Pricer agent."""
    model = OpenAIChatModel(
        LLM_MODEL_NAME,
        provider=OpenAIProvider(base_url=LLM_BASE_URL, api_key="not-needed"),
    )

    agent: Agent[PricerDeps, PriceResult] = Agent(
        model=model,
        output_type=PriceResult,
        system_prompt=PRICER_SYSTEM_PROMPT,
        name="pricer",
    )

    @agent.tool
    async def diff_historic(
        ctx: RunContext[PricerDeps],
        current_lines: list[dict[str, Any]],
        historic_lines: list[dict[str, Any]],
        threshold: float = 0.7,
    ) -> dict[str, Any]:
        """Usporedi trenutne podstavke s historijskim cjenovnim linijama po sličnosti opisa i mjernih jedinica."""
        return _diff_historic(current_lines, historic_lines, threshold)

    @agent.tool
    async def search_web(
        ctx: RunContext[PricerDeps],
        query: str,
        max_results: int = 3,
    ) -> list[dict[str, str]]:
        """Pretraži web za aktualne cijene materijala ili građevinskih radova."""
        return await _search_web(query, max_results)

    @agent.tool
    async def summarize(
        ctx: RunContext[PricerDeps],
        text: str,
        max_tokens: int = 200,
    ) -> str:
        """Sažmi tekst koristeći lokalni LLM. Zadržava ključne brojke i cijene."""
        return await _summarize(text, max_tokens)

    return agent
