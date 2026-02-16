"""Inline autocomplete endpoint — returns LLM-generated text completions for BoQ descriptions."""
from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import settings
from app.services.llm_settings import run_with_settings

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ContextItem(BaseModel):
    item_number: str | None = None
    description: str


class CompletionRequest(BaseModel):
    prefix: str
    context: list[ContextItem] = []


class CompletionResponse(BaseModel):
    suggestion: str


# ---------------------------------------------------------------------------
# PydanticAI agent for completion
# ---------------------------------------------------------------------------

_completion_model = OpenAIModel(
    settings.LLM_MODEL_NAME,
    provider=OpenAIProvider(base_url=settings.LLM_BASE_URL),
)

completion_agent = Agent(
    model=_completion_model,
    system_prompt=(
        "Ti si asistent za dovršavanje opisa stavki u građevinskim troškovnicima (BOQ). "
        "Korisnik uređuje opis stavke i tvoj zadatak je dovršiti tekst koji je započeo. "
        "Pravila:\n"
        "- Odgovori SAMO s nastavkom teksta, bez ponavljanja onoga što je korisnik već napisao.\n"
        "- Piši na hrvatskom jeziku koristeći standardnu građevinsku terminologiju.\n"
        "- Budi koncizan — dovrši jednu smislenu rečenicu ili frazu, ne više.\n"
        "- Ne dodaj numeraciju, oznake stavki, jedinice mjere ni cijene.\n"
        "- Ako kontekst okolnih stavki pomaže razumjeti o čemu se radi, koristi ga.\n"
        "- Ako ne možeš smisleno dovršiti tekst, odgovori praznim stringom."
    ),
)


def _strip_prefix_echo(prefix: str, suggestion: str) -> str:
    """Remove the prefix if the LLM echoed it back at the start of the suggestion."""
    stripped = suggestion.strip()
    prefix_stripped = prefix.strip()
    if stripped.lower().startswith(prefix_stripped.lower()):
        stripped = stripped[len(prefix_stripped):].lstrip()
    return stripped


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/suggest/complete", response_model=CompletionResponse)
async def suggest_completion(req: CompletionRequest):
    """Generate an inline text completion for a BoQ item description."""
    if not req.prefix.strip():
        return CompletionResponse(suggestion="")

    # Build prompt with context
    prompt_parts: list[str] = []

    if req.context:
        prompt_parts.append("=== Okolne stavke ===")
        for ctx in req.context[:5]:  # limit context to 5 items
            num = ctx.item_number or "?"
            prompt_parts.append(f"{num}: {ctx.description}")
        prompt_parts.append("")

    prompt_parts.append("=== Dovrši ovaj tekst ===")
    prompt_parts.append(req.prefix)

    full_prompt = "\n".join(prompt_parts)

    try:
        result = await run_with_settings(
            "completion", completion_agent, full_prompt,
            extra_model_settings={"max_tokens": 80},
        )
        suggestion = _strip_prefix_echo(req.prefix, result.output)
        return CompletionResponse(suggestion=suggestion)
    except Exception as exc:
        logger.exception("Completion LLM call failed")
        return CompletionResponse(suggestion="")
