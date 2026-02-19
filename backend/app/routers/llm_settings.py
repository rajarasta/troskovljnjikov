"""LLM settings endpoints — per-agent temperature, system prompt & model control."""

from __future__ import annotations

import asyncio
import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings as app_settings
from app.services import llm_discovery
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


class AddEndpointRequest(BaseModel):
    url: str


class SetActiveEndpointRequest(BaseModel):
    url: str


# ---------------------------------------------------------------------------
# Global model endpoints (must be above /{agent_id} to avoid route collision)
# ---------------------------------------------------------------------------


@router.get("/llm-settings/global/models")
async def list_available_models():
    """Return available model providers (anthropic + local llama-server models)."""
    current = get_current_model_name()

    # Always include Anthropic option if API key is configured
    models = []
    if app_settings.ANTHROPIC_API_KEY and app_settings.ANTHROPIC_API_KEY != "":
        models.append("anthropic")

    # Also try to get local llama-server models from active endpoint
    active_url = llm_discovery.get_active_url()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{active_url}/models")
            resp.raise_for_status()
            data = resp.json()
            local_models = [m["id"] for m in data.get("data", [])]
            models.extend(local_models)
    except Exception as exc:
        logger.warning("Failed to query llama-server /v1/models at %s: %s", active_url, exc)

    # Fallback: if no models available, return current or defaults
    if not models:
        models = [current] if current else ["ministral-3b"]

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
# LLM Endpoint Management
# ---------------------------------------------------------------------------


@router.get("/llm-settings/endpoints")
def list_endpoints():
    """Return all registered LLM endpoints."""
    endpoints = llm_discovery.get_endpoints()
    return {"endpoints": endpoints}


@router.post("/llm-settings/endpoints")
def add_endpoint(req: AddEndpointRequest):
    """Register a new LLM endpoint."""
    endpoints = llm_discovery.add_endpoint(req.url)
    return {"endpoints": endpoints}


@router.delete("/llm-settings/endpoints")
def remove_endpoint(req: AddEndpointRequest):
    """Remove an endpoint from the registry."""
    endpoints = llm_discovery.remove_endpoint(req.url)
    return {"endpoints": endpoints}


@router.post("/llm-settings/endpoints/scan")
async def scan_endpoints():
    """Scan common ports for LLM endpoints."""
    discovered = await llm_discovery.scan_common_ports()
    llm_discovery.merge_discovered_endpoints(discovered)
    all_endpoints = llm_discovery.get_endpoints()
    return {"endpoints": all_endpoints}


@router.post("/llm-settings/endpoints/health")
async def check_endpoint_health(req: AddEndpointRequest):
    """Probe a specific endpoint for health/models."""
    endpoint_info = await llm_discovery.probe_endpoint(req.url)
    return {"endpoint": endpoint_info}


@router.put("/llm-settings/endpoints/active")
def set_active_endpoint(req: SetActiveEndpointRequest):
    """Set the active endpoint for local LLM."""
    # Verify endpoint exists in registry
    endpoints = llm_discovery.get_endpoints()
    if not any(ep.url == req.url for ep in endpoints):
        raise HTTPException(status_code=404, detail=f"Endpoint {req.url} not found")

    llm_discovery.set_active_url(req.url)
    return {"active_url": req.url}


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
