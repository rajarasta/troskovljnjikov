"""SSE endpoint for agent price suggestions."""

import json

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from ..models.agent import SuggestRequest
from ..agent.pipeline import run_pipeline
from .upload import get_current_boq

router = APIRouter()


@router.post("/agent/suggest")
async def suggest_prices(body: SuggestRequest):
    boq = get_current_boq()
    if not boq:
        raise HTTPException(404, "No BoQ uploaded yet")

    unit = None
    for u in boq.units:
        if u.id == body.unit_id:
            unit = u
            break
    if not unit:
        raise HTTPException(404, f"Unit {body.unit_id} not found")

    async def event_stream():
        async for event_type, data in run_pipeline(unit):
            yield {"event": event_type, "data": json.dumps(data, ensure_ascii=False)}

    return EventSourceResponse(event_stream())
