"""LLM endpoint discovery & registry for llama.cpp/llama-server instances.

Scans common ports to auto-discover running LLM servers, maintains a registry
in `data/llm_endpoints.json`, and tracks which endpoint is "active" for local LLM use.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

REGISTRY_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "llm_endpoints.json"
COMMON_PORTS = [8008, 8040, 8080, 8095, 8096, 8110, 11434]  # 11434 = Ollama default
COMMON_HOSTS = ["localhost", "127.0.0.1"]
PROBE_TIMEOUT = 2.0


class EndpointInfo(BaseModel):
    """Information about an LLM endpoint."""

    url: str  # e.g., "http://localhost:8095/v1"
    status: Literal["online", "offline", "unknown"]  # health check result
    models: list[str] = []  # model IDs from /v1/models
    is_active: bool = False  # currently selected for local LLM
    last_checked: str | None = None  # ISO timestamp


# In-memory registry + active endpoint
_endpoints: list[EndpointInfo] = []
_active_url: str | None = None
_initialized = False


def _load_registry() -> None:
    """Load endpoint registry from JSON file."""
    global _endpoints, _active_url, _initialized

    if REGISTRY_PATH.exists():
        try:
            data = json.loads(REGISTRY_PATH.read_text())
            _endpoints = [EndpointInfo(**ep) for ep in data.get("endpoints", [])]
            _active_url = data.get("active_url")
            # Ensure only one is marked active
            for ep in _endpoints:
                ep.is_active = ep.url == _active_url
            logger.info(f"Loaded {len(_endpoints)} endpoints from registry")
        except Exception as exc:
            logger.warning(f"Failed to load endpoint registry: {exc}")
            _endpoints = []
            _active_url = None
    else:
        _endpoints = []
        _active_url = None

    _initialized = True


def _save_registry() -> None:
    """Save endpoint registry to JSON file."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "endpoints": [ep.model_dump() for ep in _endpoints],
        "active_url": _active_url,
    }
    REGISTRY_PATH.write_text(json.dumps(data, indent=2))


async def probe_endpoint(url: str) -> EndpointInfo:
    """Probe a single endpoint and return its status.

    Tries:
    1. GET {url}/models → OpenAI-compatible API
    2. GET {url}/health → llama.cpp health check
    """
    if not url.startswith("http"):
        url = f"http://{url}"
    # Ensure /v1 is in the URL if not already there
    if not url.endswith("/v1"):
        if not url.endswith("/"):
            url += "/"
        url += "v1"

    status: Literal["online", "offline", "unknown"] = "unknown"
    models: list[str] = []
    now = datetime.utcnow().isoformat() + "Z"

    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT) as client:
            # Try /models endpoint (OpenAI-compatible)
            try:
                resp = await client.get(f"{url}/models")
                resp.raise_for_status()
                data = resp.json()
                models = [m.get("id", m.get("name", "")) for m in data.get("data", [])]
                status = "online"
                logger.debug(f"Probed {url} → online, found {len(models)} models")
                return EndpointInfo(
                    url=url,
                    status=status,
                    models=models,
                    is_active=False,
                    last_checked=now,
                )
            except Exception as e:
                logger.debug(f"Failed /models check on {url}: {e}")

            # Fall back to /health (llama.cpp specific)
            try:
                base_url = url.rstrip("/v1")
                resp = await client.get(f"{base_url}/health")
                resp.raise_for_status()
                status = "online"
                logger.debug(f"Probed {url} → online (health check)")
                return EndpointInfo(
                    url=url,
                    status=status,
                    models=[],
                    is_active=False,
                    last_checked=now,
                )
            except Exception:
                pass

    except asyncio.TimeoutError:
        logger.debug(f"Probe timeout for {url}")
    except Exception as e:
        logger.debug(f"Probe error for {url}: {e}")

    status = "offline"
    return EndpointInfo(
        url=url,
        status=status,
        models=models,
        is_active=False,
        last_checked=now,
    )


async def scan_common_ports(
    hosts: list[str] | None = None, ports: list[int] | None = None
) -> list[EndpointInfo]:
    """Scan common ports and return all discovered endpoints.

    Probes all (host, port) combinations concurrently.
    """
    if hosts is None:
        hosts = COMMON_HOSTS
    if ports is None:
        ports = COMMON_PORTS

    tasks = []
    for host in hosts:
        for port in ports:
            url = f"http://{host}:{port}/v1"
            tasks.append(probe_endpoint(url))

    results = await asyncio.gather(*tasks, return_exceptions=False)
    discovered = [r for r in results if r.status == "online"]

    logger.info(f"Port scan complete: found {len(discovered)} online endpoints")
    return discovered


def get_endpoints() -> list[EndpointInfo]:
    """Return all registered endpoints."""
    if not _initialized:
        _load_registry()
    return _endpoints


def get_active_url() -> str:
    """Return the URL of the active endpoint.

    If none is set, tries to use the one marked active in the registry,
    or falls back to config's LLM_BASE_URL.
    """
    global _active_url
    if not _initialized:
        _load_registry()

    if _active_url:
        return _active_url

    # Fallback to config setting
    from app.config import settings

    return settings.LLM_BASE_URL


def add_endpoint(url: str) -> list[EndpointInfo]:
    """Register a new endpoint. Returns updated endpoint list."""
    if not _initialized:
        _load_registry()

    # Normalize URL
    if not url.startswith("http"):
        url = f"http://{url}"
    if not url.endswith("/v1"):
        if not url.endswith("/"):
            url += "/"
        url += "v1"

    # Check if already exists
    if any(ep.url == url for ep in _endpoints):
        logger.warning(f"Endpoint {url} already registered")
        return _endpoints

    # Add new endpoint (probing happens separately)
    ep = EndpointInfo(url=url, status="unknown", models=[], is_active=False)
    _endpoints.append(ep)
    _save_registry()
    logger.info(f"Added endpoint: {url}")
    return _endpoints


def remove_endpoint(url: str) -> list[EndpointInfo]:
    """Remove an endpoint from the registry."""
    global _active_url
    if not _initialized:
        _load_registry()

    before = len(_endpoints)
    _endpoints[:] = [ep for ep in _endpoints if ep.url != url]

    if len(_endpoints) < before:
        # If we just removed the active one, clear it
        if _active_url == url:
            _active_url = None
        _save_registry()
        logger.info(f"Removed endpoint: {url}")

    return _endpoints


def set_active_url(url: str) -> None:
    """Set the active endpoint URL and invalidate model caches."""
    global _active_url
    if not _initialized:
        _load_registry()

    # Update all endpoints' is_active flag
    for ep in _endpoints:
        ep.is_active = ep.url == url

    _active_url = url
    _save_registry()

    # Invalidate model cache in llm_settings so it rebuilds the provider
    from app.services import llm_settings

    llm_settings._cached_model = None
    llm_settings._cached_model_name = None
    llm_settings._provider = None

    logger.info(f"Active endpoint set to: {url}")


def merge_discovered_endpoints(discovered: list[EndpointInfo]) -> None:
    """Merge newly discovered endpoints into the registry.

    Updates existing endpoints' status if URL already registered,
    adds new ones if not.
    """
    if not _initialized:
        _load_registry()

    for new_ep in discovered:
        existing = next((ep for ep in _endpoints if ep.url == new_ep.url), None)
        if existing:
            existing.status = new_ep.status
            existing.models = new_ep.models
            existing.last_checked = new_ep.last_checked
        else:
            _endpoints.append(new_ep)

    # If no active endpoint is set and we have online endpoints, set the first one
    global _active_url
    if not _active_url:
        online = [ep for ep in _endpoints if ep.status == "online"]
        if online:
            _active_url = online[0].url
            online[0].is_active = True

    _save_registry()
    logger.info(f"Merged {len(discovered)} discovered endpoints into registry")


# Load on module import
_load_registry()
