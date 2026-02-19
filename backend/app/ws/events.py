"""Event Dispatcher - creates and broadcasts WebSocket events."""
from __future__ import annotations

import logging
from typing import Any

from app.schemas.ws_events import WSEvent
from app.ws.manager import manager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Event type constants
# ---------------------------------------------------------------------------

# Pipeline lifecycle
PIPELINE_STAGE_CHANGED = "pipeline:stage_changed"

# Agent lifecycle
AGENT_SPAWN = "agent:spawn"
AGENT_PROGRESS = "agent:progress"
AGENT_RESULT = "agent:result"
AGENT_ERROR = "agent:error"
AGENT_RUN_START = "agent:run_start"
AGENT_RUN_END = "agent:run_end"

# Domain events
MATCH_FOUND = "match:found"
PRICE_SUGGESTED = "price:suggested"
FILE_INDEXED = "file:indexed"
COLUMN_DETECTED = "column:detected"

# Autopilot events
AUTOPILOT_SUMMARY_TOKEN = "autopilot:summary_token"
AUTOPILOT_MATCH_PROGRESS = "autopilot:match_progress"
AUTOPILOT_MATCH_RESULT = "autopilot:match_result"
AUTOPILOT_PRICE_SUGGESTED = "autopilot:price_suggested"
AUTOPILOT_COMPLETE = "autopilot:complete"
AUTOPILOT_ERROR = "autopilot:error"

# Chat streaming events
CHAT_TOKEN = "chat:token"
CHAT_COMPLETE = "chat:complete"

# Web price search events
SEARCH_STARTED = "search:started"
SEARCH_PROGRESS = "search:progress"
SEARCH_QUOTE_FOUND = "search:quote_found"
SEARCH_COMPLETE = "search:complete"

# Pricing pipeline events
PRICING_STAGE_CHANGED = "pricing:stage_changed"
PRICING_ITEM_PROGRESS = "pricing:item_progress"
PRICING_ITEM_RESULT = "pricing:item_result"
PRICING_COMPLETE = "pricing:complete"
PRICING_ERROR = "pricing:error"


async def emit(
    event_type: str,
    payload: dict[str, Any],
    pipeline_id: str | None = None,
) -> None:
    """Create a WSEvent and broadcast it to all connected WebSocket clients.

    Args:
        event_type: One of the event type constants defined above.
        payload: Arbitrary data to include in the event.
        pipeline_id: Optional pipeline identifier to tag the event with.
    """
    event = WSEvent(
        type=event_type,
        pipeline_id=pipeline_id,
        payload=payload,
    )
    logger.debug("Emitting event %s (pipeline=%s)", event_type, pipeline_id)
    await manager.broadcast(event.model_dump())
