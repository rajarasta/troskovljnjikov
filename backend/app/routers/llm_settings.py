"""LLM settings endpoints — per-agent temperature, system prompt & model control."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings as app_settings
from app.services.llm_settings import (
    get_all_settings,
    get_current_model_name,
    get_settings,
    reset_agent,
    set_model_name,
    set_settings,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class UpdateRequest(BaseModel):
    temperature: float | None = None
    knowledge_prompt: str | None = None
    instruction_prompt: str | None = None
    enabled: bool | None = None


class SetModelRequest(BaseModel):
    model_name: str


# ---------------------------------------------------------------------------
# Global model endpoints (must be above /{agent_id} to avoid route collision)
# ---------------------------------------------------------------------------


@router.get("/llm-settings/global/models")
async def list_available_models():
    """Query llama-server /v1/models and return available models + current selection."""
    current = get_current_model_name()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{app_settings.LLM_BASE_URL}/models")
            resp.raise_for_status()
            data = resp.json()
            models = [m["id"] for m in data.get("data", [])]
    except Exception as exc:
        logger.warning("Failed to query /v1/models: %s", exc)
        # Return just the current model so the UI can still render
        models = [current]
    return {"models": models, "current": current}


@router.get("/llm-settings/global/model")
def get_current_model():
    """Return the currently selected global model name."""
    return {"model": get_current_model_name()}


@router.put("/llm-settings/global/model")
def update_current_model(req: SetModelRequest):
    """Set the global model name for all agents."""
    name = set_model_name(req.model_name)
    return {"model": name}


# ---------------------------------------------------------------------------
# Per-agent endpoints
# ---------------------------------------------------------------------------


@router.get("/llm-settings")
def list_settings():
    """Return settings for all agents (defaults merged with overrides)."""
    return get_all_settings()


@router.get("/llm-settings/{agent_id}")
def get_agent_settings(agent_id: str):
    """Return settings for a single agent."""
    try:
        return get_settings(agent_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")


@router.put("/llm-settings/{agent_id}")
def update_agent_settings(agent_id: str, req: UpdateRequest):
    """Update temperature and/or system_prompt for an agent."""
    try:
        return set_settings(
            agent_id,
            temperature=req.temperature,
            knowledge_prompt=req.knowledge_prompt,
            instruction_prompt=req.instruction_prompt,
            enabled=req.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/llm-settings/{agent_id}/reset")
def reset_agent_settings(agent_id: str):
    """Revert an agent to its default settings."""
    return reset_agent(agent_id)
