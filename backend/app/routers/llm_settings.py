"""LLM settings endpoints — per-agent temperature & system prompt control."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.llm_settings import get_all_settings, get_settings, reset_agent, set_settings

router = APIRouter()


class UpdateRequest(BaseModel):
    temperature: float | None = None
    knowledge_prompt: str | None = None
    instruction_prompt: str | None = None
    enabled: bool | None = None


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
