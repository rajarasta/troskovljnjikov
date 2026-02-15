from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.boq import BoQItem
from app.schemas.boq import (
    BoQItemSchema,
    MatchRequest,
    MatchResponse,
    MatchResult,
)
from app.services.rag import search as rag_search

router = APIRouter()


@router.get("/items", response_model=list[BoQItemSchema])
def list_items(
    file_id: str | None = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(BoQItem)
    if file_id:
        query = query.filter(BoQItem.file_id == file_id)
    items = query.order_by(BoQItem.row).offset(offset).limit(limit).all()
    return items


@router.post("/match", response_model=MatchResponse)
def match_items(
    req: MatchRequest,
    db: Session = Depends(get_db),
):
    hits = rag_search(
        query_text=req.description,
        top_k=req.max_results,
    )

    # Fetch full BoQItem records for each hit
    hit_ids = [h["id"] for h in hits]
    if not hit_ids:
        return MatchResponse(matches=[], stats=_empty_stats())

    items_by_id = {
        item.id: item
        for item in db.query(BoQItem).filter(BoQItem.id.in_(hit_ids)).all()
    }

    results: list[MatchResult] = []
    prices: list[float] = []
    for hit in hits:
        item = items_by_id.get(hit["id"])
        if not item:
            continue
        similarity = hit["similarity"]
        if similarity < req.threshold:
            continue

        qty_comp = None
        if req.quantity is not None:
            qty_comp = _quantity_comparison(req.quantity, item.quantity or 0)

        results.append(MatchResult(
            item=BoQItemSchema.model_validate(item),
            similarity=similarity,
            quantity_comparison=qty_comp,
        ))
        if item.unit_price and item.unit_price > 0:
            prices.append(item.unit_price)

    stats = {
        "count": len(results),
        "avgPrice": sum(prices) / len(prices) if prices else 0,
        "minPrice": min(prices) if prices else 0,
        "maxPrice": max(prices) if prices else 0,
        "priceRange": (max(prices) - min(prices)) if prices else 0,
        "statusCounts": {},
    }
    return MatchResponse(matches=results, stats=stats)


def _empty_stats() -> dict[str, Any]:
    return {
        "count": 0, "avgPrice": 0, "minPrice": 0,
        "maxPrice": 0, "priceRange": 0, "statusCounts": {},
    }


def _quantity_comparison(selected_qty: float, match_qty: float) -> dict[str, Any]:
    if selected_qty == 0 and match_qty == 0:
        return {"hasData": False, "label": "N/A", "color": "gray"}
    if selected_qty == 0:
        return {"hasData": True, "label": str(match_qty), "color": "blue"}
    if match_qty == 0:
        return {"hasData": True, "label": "No qty", "color": "gray"}
    ratio = match_qty / selected_qty
    pct = ((match_qty - selected_qty) / selected_qty) * 100.0
    if 0.9 <= ratio <= 1.1:
        color = "green"
        label = "Same" if abs(pct) < 1 else f"{'+' if pct > 0 else ''}{pct:.0f}%"
    elif 0.5 <= ratio <= 2.0:
        color = "amber"
        label = f"{'+' if pct > 0 else ''}{pct:.0f}%"
    else:
        color = "red"
        label = f"{ratio * 100:.0f}%" if ratio < 1 else f"{ratio:.1f}x"
    return {"hasData": True, "ratio": ratio, "percentDiff": pct, "label": label, "color": color}
