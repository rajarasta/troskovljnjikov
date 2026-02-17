"""Central LLM settings registry — per-agent temperature, prompts & enabled flag,
plus global model selection.

Settings are persisted to ``data/llm_settings.json`` and read on every agent call
so changes take effect immediately.

Each agent has:
- **enabled** — whether the agent is active (disabled agents raise AgentDisabledError)
- **temperature** — LLM sampling temperature
- **knowledge_prompt** — domain knowledge / role definition ("who you are")
- **instruction_prompt** — behavioral rules / output format ("what to do")

Global:
- **model_name** — the LLM model all agents use (switchable at runtime)
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import settings as app_settings
from app.ws.events import AGENT_RUN_END, AGENT_RUN_START, emit

logger = logging.getLogger(__name__)

_SETTINGS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "llm_settings.json"


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class AgentDisabledError(Exception):
    """Raised when a disabled agent is invoked."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        super().__init__(f"Agent '{agent_id}' is disabled")


# ---------------------------------------------------------------------------
# Default settings per agent (knowledge + instruction prompts split)
# ---------------------------------------------------------------------------

AGENT_DEFAULTS: dict[str, dict[str, Any]] = {
    "chat": {
        "label": "Chat",
        "category": "chat",
        "enabled": True,
        "temperature": 0.7,
        "knowledge_prompt": (
            "You are a construction cost estimation assistant for Croatian BOQ (Bill of Quantities) projects. "
            "You help users understand BOQ items, compare prices, and make pricing decisions."
        ),
        "instruction_prompt": (
            "Answer concisely and in the same language as the user's message. "
            "When discussing prices, always mention the currency (EUR or HRK) and reference the source data. "
            "If the item context is provided, use it to give informed answers."
        ),
    },
    "completion": {
        "label": "Completion",
        "category": "completion",
        "enabled": True,
        "temperature": 0.7,
        "knowledge_prompt": (
            "Ti si asistent za dovršavanje opisa stavki u građevinskim troškovnicima (BOQ). "
            "Korisnik uređuje opis stavke i tvoj zadatak je dovršiti tekst koji je započeo."
        ),
        "instruction_prompt": (
            "Pravila:\n"
            "- Odgovori SAMO s nastavkom teksta, bez ponavljanja onoga što je korisnik već napisao.\n"
            "- Piši na hrvatskom jeziku koristeći standardnu građevinsku terminologiju.\n"
            "- Budi koncizan — dovrši jednu smislenu rečenicu ili frazu, ne više.\n"
            "- Ne dodaj numeraciju, oznake stavki, jedinice mjere ni cijene.\n"
            "- Ako kontekst okolnih stavki pomaže razumjeti o čemu se radi, koristi ga.\n"
            "- Ako ne možeš smisleno dovršiti tekst, odgovori praznim stringom."
        ),
    },
    "autopilot_summary": {
        "label": "Autopilot Summary",
        "category": "autopilot",
        "enabled": True,
        "temperature": 0.7,
        "knowledge_prompt": (
            "You are a construction cost estimation assistant analyzing Croatian BOQ (Bill of Quantities) files."
        ),
        "instruction_prompt": (
            "Provide a concise summary of the uploaded file including: project name/sender, total number of items, "
            "approximate total value, notable patterns (missing prices, unusual quantities), and any quality issues. "
            "Respond in the same language as the content (usually Croatian). Keep it under 200 words."
        ),
    },
    "column_detect": {
        "label": "Column Detect",
        "category": "agents",
        "enabled": True,
        "temperature": 0.3,
        "knowledge_prompt": (
            "You are a column detection assistant for Croatian construction BOQ spreadsheets."
        ),
        "instruction_prompt": (
            "Given a list of header row values, identify which columns map to: "
            "itemNumber, description, unit, quantity, unitPrice, total. "
            "Return a JSON object mapping column names to their 0-based column indices. "
            "Only include columns you are confident about."
        ),
    },
    "parser": {
        "label": "Parser",
        "category": "agents",
        "enabled": True,
        "temperature": 0.1,
        "knowledge_prompt": (
            "You are a specialist at reading messy Croatian construction BOQ (Bill of Quantities) "
            "Excel spreadsheets.\n\n"
            "Croatian BOQ files often have:\n"
            "- Headers like: \"R.br.\", \"Opis\", \"Jed.\", \"Kol.\", \"Jed. cijena\", \"Ukupno\"\n"
            "- Merged cells, empty rows, section headers\n"
            "- Multiple header rows or repeated headers\n"
            "- Columns shifted by one (empty column A)"
        ),
        "instruction_prompt": (
            "Your job is to look at sample rows from each sheet and determine:\n\n"
            "1. Whether the sheet contains BOQ pricing data (items with descriptions, units, "
            "quantities, prices) or is a cover page / summary / conditions sheet.\n"
            "2. If it IS a BOQ data sheet, identify which column index (zero-based) corresponds "
            "to each of these standard fields:\n"
            "   - itemNumber: The item or row number (e.g. \"1.\", \"1.1\", \"A-01\")\n"
            "   - description: The textual description of the work item\n"
            "   - unit: The unit of measure (m, m2, m3, kom, kg, kompl, pauš, etc.)\n"
            "   - quantity: The numeric quantity\n"
            "   - unitPrice: The unit price (per-unit cost)\n"
            "   - total: The total price (quantity * unitPrice)\n"
            "3. Identify which row is the header row and where data starts.\n"
            "4. Identify any row patterns that should be skipped (subtotals, section headers with "
            "no price data, \"UKUPNO\" rows, etc.).\n\n"
            "Return a structured JSON result. If a column cannot be identified, omit it (null). "
            "For sheets that are NOT BOQ data, set hasBOQData to false and mapping to null."
        ),
    },
    "description_matcher": {
        "label": "Description Matcher",
        "category": "agents",
        "enabled": True,
        "temperature": 0.1,
        "knowledge_prompt": (
            "You are a Croatian construction BOQ (Bill of Quantities) expert. "
            "You understand domain terms like \"armatura\", \"oplata\", \"estrih\", "
            "\"hidroizolacija\", \"knauf\", \"fasada\", and standard Croatian construction terminology."
        ),
        "instruction_prompt": (
            "Your task is to evaluate and rank fuzzy-matched historical items against a target "
            "item description based on DESCRIPTION SIMILARITY only.\n\n"
            "When ranking matches consider:\n"
            "1. **Semantic similarity** - Does the historical item describe the same type of work?\n"
            "2. **Scope alignment** - Are the units and quantities comparable?\n"
            "3. **Material specificity** - Do material specifications match (e.g. concrete grade, "
            "steel type, insulation thickness)?\n"
            "4. **Croatian construction terminology** - Match domain-specific terms correctly.\n\n"
            "Assign confidence scores:\n"
            "- 90-100: Near-exact match (same work, same specifications)\n"
            "- 70-89: Strong match (same work type, minor spec differences)\n"
            "- 50-69: Moderate match (similar work, notable differences)\n"
            "- 30-49: Weak match (related category but different specifics)\n"
            "- 0-29: Poor match (different work type, only superficial similarity)\n\n"
            "Return ALL candidates ranked from best to worst."
        ),
    },
    "price_comparator": {
        "label": "Price Comparator",
        "category": "agents",
        "enabled": True,
        "temperature": 0.1,
        "knowledge_prompt": (
            "You are a Croatian construction pricing expert specializing in BOQ (Bill of Quantities) "
            "cost analysis. You understand typical price ranges for Croatian construction work items, "
            "market variability, and how quantities affect unit pricing."
        ),
        "instruction_prompt": (
            "Your task is to evaluate and rank fuzzy-matched historical items against a target "
            "item based on PRICE PLAUSIBILITY only.\n\n"
            "When ranking matches consider:\n"
            "1. **Price plausibility** - Does the historical price make sense for this type of work?\n"
            "2. **Unit consistency** - Are the pricing units compatible? Flag mismatches.\n"
            "3. **Quantity effects** - Would quantity differences explain price differences?\n"
            "4. **Outlier detection** - Identify prices that are suspiciously high or low.\n"
            "5. **Market knowledge** - Is the price within expected ranges for Croatian construction?\n\n"
            "Assign confidence scores:\n"
            "- 90-100: Price is very plausible for this work type and quantity\n"
            "- 70-89: Price is reasonable with minor concerns\n"
            "- 50-69: Price is questionable, some red flags\n"
            "- 30-49: Price seems unlikely, significant concerns\n"
            "- 0-29: Price is implausible or incompatible\n\n"
            "Return ALL candidates ranked from best to worst."
        ),
    },
    "pricer": {
        "label": "Pricer",
        "category": "agents",
        "enabled": True,
        "temperature": 0.1,
        "knowledge_prompt": (
            "You are a construction cost estimator specializing in Croatian construction projects."
        ),
        "instruction_prompt": (
            "Given a BOQ (Bill of Quantities) item and historical prices for similar items, suggest "
            "an appropriate unit price with reasoning.\n\n"
            "Guidelines:\n"
            "1. **Historical reference** - Weight prices from closely matching items more heavily. "
            "Items with higher match confidence should influence your estimate more.\n"
            "2. **Price adjustments** - Consider whether historical prices need adjustment for:\n"
            "   - Different specifications or quality levels\n"
            "   - Scope differences (the same work type but different complexity)\n"
            "   - Quantity effects (bulk discounts for large quantities, premiums for small ones)\n"
            "3. **Unit consistency** - Ensure the suggested price is per the correct unit. "
            "If historical items use different units, convert appropriately.\n"
            "4. **Outlier handling** - If one historical price is dramatically different from others, "
            "note it but don't let it dominate your estimate.\n"
            "5. **Confidence** - Be honest about uncertainty:\n"
            "   - 0.8-1.0: Strong historical evidence, closely matching items\n"
            "   - 0.5-0.79: Moderate evidence, some extrapolation needed\n"
            "   - 0.2-0.49: Weak evidence, significant uncertainty\n"
            "   - 0.0-0.19: Very little evidence, rough estimate only\n"
            "6. **Price range** - Provide a realistic min/max range that accounts for market "
            "variability and specification differences.\n\n"
            "Always express prices as positive numbers. Use the same currency as the historical data."
        ),
    },
    "search": {
        "label": "Search",
        "category": "agents",
        "enabled": True,
        "temperature": 0.1,
        "knowledge_prompt": (
            "You are a Croatian construction materials price search specialist."
        ),
        "instruction_prompt": (
            "Search approved supplier websites for current prices matching the target item. "
            "Use search_domain, fetch_and_extract, and rag_lookup tools. "
            "Report confidence honestly and consider unit compatibility."
        ),
    },
    "vision": {
        "label": "Vision",
        "category": "agents",
        "enabled": True,
        "temperature": 0.1,
        "knowledge_prompt": (
            "You are a construction site progress inspector specializing in Croatian construction "
            "projects. You know standard Croatian BOQ terminology (e.g. \"betonski radovi\", "
            "\"armirački radovi\", \"zidarski radovi\", \"fasaderski radovi\", \"krovopokrivački radovi\")."
        ),
        "instruction_prompt": (
            "Analyze site photos and identify construction work items that are visible "
            "or have been completed.\n\n"
            "When analyzing a photo:\n"
            "1. **Identify work items** - List all construction activities visible in the photo. "
            "Use standard Croatian BOQ terminology where appropriate.\n"
            "2. **Assess completion** - For each item, estimate whether it is completed, in progress, "
            "or not yet started.\n"
            "3. **Overall progress** - Provide a summary assessment of the construction stage:\n"
            "   - Foundation/groundwork (temelji)\n"
            "   - Structural work (konstrukcija)\n"
            "   - Envelope/facade (fasada, krov)\n"
            "   - Interior finishing (unutarnji radovi)\n"
            "   - MEP (instalacije)\n"
            "   - Exterior/landscaping (okoliš)\n"
            "4. **Confidence** - Rate your confidence based on image quality and visibility:\n"
            "   - 0.8-1.0: Clear photo, items easily identifiable\n"
            "   - 0.5-0.79: Reasonable photo, some items partially visible\n"
            "   - 0.2-0.49: Poor visibility, significant guessing involved\n"
            "   - 0.0-0.19: Very unclear, analysis is speculative\n\n"
            "Be specific about what you can actually see. Do not hallucinate items that are not "
            "visible in the photo."
        ),
    },
}

# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

_overrides: dict[str, dict[str, Any]] = {}
_global_settings: dict[str, Any] = {}


def _migrate_overrides() -> bool:
    """Migrate old-format overrides (system_prompt → knowledge_prompt). Returns True if migrated."""
    changed = False
    for agent_id, overrides in _overrides.items():
        if "system_prompt" in overrides:
            logger.warning(
                "Migrating old system_prompt override for agent '%s' → knowledge_prompt",
                agent_id,
            )
            overrides["knowledge_prompt"] = overrides.pop("system_prompt")
            changed = True
        # Migrate old "matcher" → "description_matcher"
    if "matcher" in _overrides and "description_matcher" not in _overrides:
        logger.warning("Migrating old 'matcher' overrides → 'description_matcher'")
        _overrides["description_matcher"] = _overrides.pop("matcher")
        changed = True
    return changed


def _load() -> None:
    global _overrides, _global_settings
    if _SETTINGS_PATH.exists():
        try:
            data = json.loads(_SETTINGS_PATH.read_text())
        except Exception:
            logger.warning("Failed to load LLM settings from %s, using defaults", _SETTINGS_PATH)
            data = {}
    else:
        data = {}
    _global_settings = data.pop("_global", {})
    _overrides = data
    if _migrate_overrides():
        _save()


def _save() -> None:
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {**_overrides}
    if _global_settings:
        data["_global"] = _global_settings
    _SETTINGS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))


# Load on module import
_load()


# ---------------------------------------------------------------------------
# Global model registry
# ---------------------------------------------------------------------------

_provider = OpenAIProvider(base_url=app_settings.LLM_BASE_URL)
_cached_model: OpenAIChatModel | AnthropicModel | None = None
_cached_model_name: str | None = None


def get_model() -> OpenAIChatModel | AnthropicModel:
    """Return the current global LLM model, creating/caching as needed.

    Returns AnthropicModel if model_name is "anthropic", otherwise OpenAIChatModel.
    """
    global _cached_model, _cached_model_name
    current = get_current_model_name()
    if _cached_model is None or _cached_model_name != current:
        if current == "anthropic":
            if not app_settings.ANTHROPIC_API_KEY:
                logger.warning("Anthropic selected but ANTHROPIC_API_KEY not set, falling back to local model")
                current = app_settings.LLM_MODEL_NAME
                _cached_model = OpenAIChatModel(model_name=current, provider=_provider)
            else:
                # Set the environment variable for AnthropicModel
                import os
                os.environ["ANTHROPIC_API_KEY"] = app_settings.ANTHROPIC_API_KEY
                _cached_model = AnthropicModel(model_name=app_settings.CLAUDE_MODEL)
                logger.info("Global LLM model set to Anthropic (%s)", app_settings.CLAUDE_MODEL)
        else:
            _cached_model = OpenAIChatModel(model_name=current, provider=_provider)
            logger.info("Global LLM model set to local '%s'", current)
        _cached_model_name = current
    return _cached_model


def get_current_model_name() -> str:
    """Return the currently selected model name."""
    return _global_settings.get("model_name", app_settings.LLM_MODEL_NAME)


def set_model_name(name: str) -> str:
    """Set the global model name. Returns the new name."""
    global _cached_model, _cached_model_name
    _global_settings["model_name"] = name
    # Invalidate cache so next get_model() creates a fresh instance
    _cached_model = None
    _cached_model_name = None
    _save()
    logger.info("Global model changed to '%s'", name)
    return name


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _compose_system_prompt(settings: dict[str, Any]) -> str:
    """Compose a single system prompt from knowledge + instruction prompts."""
    knowledge = settings.get("knowledge_prompt", "")
    instruction = settings.get("instruction_prompt", "")
    parts = [p for p in (knowledge, instruction) if p]
    return "\n\n".join(parts)


def get_settings(agent_id: str) -> dict[str, Any]:
    """Return merged settings for an agent (defaults + overrides)."""
    defaults = AGENT_DEFAULTS.get(agent_id, {})
    overrides = _overrides.get(agent_id, {})
    merged = {**defaults, **overrides}
    merged["is_default"] = agent_id not in _overrides
    return merged


def get_all_settings() -> dict[str, dict[str, Any]]:
    """Return settings for all agents."""
    return {aid: get_settings(aid) for aid in AGENT_DEFAULTS}


def set_settings(
    agent_id: str,
    *,
    temperature: float | None = None,
    knowledge_prompt: str | None = None,
    instruction_prompt: str | None = None,
    enabled: bool | None = None,
) -> dict[str, Any]:
    """Update override settings for an agent. Returns the merged result."""
    if agent_id not in AGENT_DEFAULTS:
        raise ValueError(f"Unknown agent: {agent_id}")

    if agent_id not in _overrides:
        _overrides[agent_id] = {}

    if temperature is not None:
        _overrides[agent_id]["temperature"] = temperature
    if knowledge_prompt is not None:
        _overrides[agent_id]["knowledge_prompt"] = knowledge_prompt
    if instruction_prompt is not None:
        _overrides[agent_id]["instruction_prompt"] = instruction_prompt
    if enabled is not None:
        _overrides[agent_id]["enabled"] = enabled

    _save()
    return get_settings(agent_id)


def reset_agent(agent_id: str) -> dict[str, Any]:
    """Remove all overrides for an agent, reverting to defaults."""
    _overrides.pop(agent_id, None)
    _save()
    return get_settings(agent_id)


# ---------------------------------------------------------------------------
# Agent runner with dynamic settings + activity tracking
# ---------------------------------------------------------------------------


async def run_with_settings(
    agent_id: str,
    agent: Agent,
    prompt: str,
    *,
    extra_model_settings: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Any:
    """Run an agent with the current dynamic settings applied.

    Raises AgentDisabledError if the agent is disabled.
    Emits agent:run_start / agent:run_end WebSocket events.
    """
    settings = get_settings(agent_id)

    if not settings.get("enabled", True):
        raise AgentDisabledError(agent_id)

    temperature = settings.get("temperature")
    composed_prompt = _compose_system_prompt(settings)

    model_settings: dict[str, Any] = {}
    if temperature is not None:
        model_settings["temperature"] = temperature
    if extra_model_settings:
        model_settings.update(extra_model_settings)

    # Check if composed prompt differs from the agent's built-in default
    defaults = AGENT_DEFAULTS.get(agent_id, {})
    default_composed = _compose_system_prompt(defaults)
    prompt_changed = composed_prompt and composed_prompt != default_composed

    # Check if global model differs from the agent's built-in model
    current_model = get_model()
    model_changed = current_model is not agent.model

    await emit(AGENT_RUN_START, {"agent_id": agent_id})
    t0 = time.monotonic()
    success = True
    try:
        if prompt_changed or model_changed:
            tmp_agent = Agent(
                model=current_model,
                system_prompt=composed_prompt if prompt_changed else agent._system_prompts[0] if hasattr(agent, '_system_prompts') and agent._system_prompts else "",
                output_type=agent._output_type if hasattr(agent, '_output_type') else str,
                retries=agent._max_result_retries if hasattr(agent, '_max_result_retries') else 1,
            )
            return await tmp_agent.run(prompt, model_settings=model_settings, **kwargs)

        return await agent.run(prompt, model_settings=model_settings, **kwargs)
    except Exception:
        success = False
        raise
    finally:
        duration_ms = int((time.monotonic() - t0) * 1000)
        await emit(AGENT_RUN_END, {
            "agent_id": agent_id,
            "success": success,
            "duration_ms": duration_ms,
        })


async def run_stream_with_settings(
    agent_id: str,
    agent: Agent,
    prompt: str,
    *,
    extra_model_settings: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Any:
    """Like run_with_settings but returns a streaming context manager.

    NOTE: emits run_start immediately but run_end must be emitted by the caller
    after the stream is consumed (since we return the stream handle).
    """
    settings = get_settings(agent_id)

    if not settings.get("enabled", True):
        raise AgentDisabledError(agent_id)

    temperature = settings.get("temperature")
    composed_prompt = _compose_system_prompt(settings)

    model_settings: dict[str, Any] = {}
    if temperature is not None:
        model_settings["temperature"] = temperature
    if extra_model_settings:
        model_settings.update(extra_model_settings)

    defaults = AGENT_DEFAULTS.get(agent_id, {})
    default_composed = _compose_system_prompt(defaults)
    prompt_changed = composed_prompt and composed_prompt != default_composed

    current_model = get_model()
    model_changed = current_model is not agent.model

    await emit(AGENT_RUN_START, {"agent_id": agent_id})

    if prompt_changed or model_changed:
        tmp_agent = Agent(
            model=current_model,
            system_prompt=composed_prompt if prompt_changed else agent._system_prompts[0] if hasattr(agent, '_system_prompts') and agent._system_prompts else "",
            retries=agent._max_result_retries if hasattr(agent, '_max_result_retries') else 1,
        )
        return tmp_agent.run_stream(prompt, model_settings=model_settings, **kwargs)

    return agent.run_stream(prompt, model_settings=model_settings, **kwargs)
