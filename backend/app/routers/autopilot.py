"""Autopilot REST endpoints - serve cached batch match and price results."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.routers.items import _process_hits, _build_stats
from app.schemas.boq import MatchResponse
from app.services.autopilot import (
    get_all_cached_matches,
    get_all_cached_prices,
    get_all_confidences,
    get_cached_matches,
    get_cached_price,
    get_status,
)

router = APIRouter()


@router.get("/autopilot/{file_id}/status")
def autopilot_status(file_id: str):
    return get_status(file_id)


@router.get("/autopilot/{file_id}/confidences")
def autopilot_confidences(file_id: str):
    return get_all_confidences(file_id)


@router.get("/autopilot/{file_id}/prices")
def autopilot_prices(file_id: str):
    return get_all_cached_prices(file_id)


@router.get("/autopilot/{file_id}/matches/{item_id:path}")
def autopilot_matches(file_id: str, item_id: str):
    result = get_cached_matches(file_id, item_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No cached matches for this item")
    return result


@router.get("/autopilot/{file_id}/matches-resolved/{item_id:path}", response_model=MatchResponse)
def autopilot_matches_resolved(
    file_id: str,
    item_id: str,
    quantity: float = 0,
    db: Session = Depends(get_db),
):
    """Resolve cached autopilot matches to full MatchResult objects (reuses items.py logic)."""
    cached = get_cached_matches(file_id, item_id)
    if cached is None:
        raise HTTPException(status_code=404, detail="No cached matches for this item")

    results, prices = _process_hits(cached, settings.MATCH_THRESHOLD, quantity or None, db)
    return MatchResponse(matches=results, stats=_build_stats(prices))
