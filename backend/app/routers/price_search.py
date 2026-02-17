"""Price Search REST endpoints - trigger and retrieve web price search results."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.boq import BoQItem
from app.agents.search_agent import SearchResult, run_price_search
from app.agents.lookup_agent import (
    is_synthetic_item_id,
    parse_synthetic_item_id,
    resolve_synthetic_item,
)
from app.services.price_normalizer import PricingRules
from app.ws.events import (
    AGENT_ERROR,
    AGENT_RESULT,
    AGENT_SPAWN,
    SEARCH_COMPLETE,
    SEARCH_PROGRESS,
    SEARCH_QUOTE_FOUND,
    SEARCH_STARTED,
    emit,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory result cache
# ---------------------------------------------------------------------------

_result_cache: dict[str, SearchResult] = {}
_status_cache: dict[str, str] = {}  # item_id -> "searching" | "done" | "error"


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class PriceSearchRequest(BaseModel):
    quantity: float | None = None
    include_vat: bool = True
    include_shipping: bool = True
    # For synthetic items: explicit description (for spreadsheet cells)
    description: str | None = None


class BatchSearchRequest(BaseModel):
    item_ids: list[str]
    # Optional: descriptions for synthetic items (indexed by item_id)
    descriptions: dict[str, str] | None = None
    include_vat: bool = True
    include_shipping: bool = True


# ---------------------------------------------------------------------------
# Batch search (must come before single-item to prevent route shadowing)
# ---------------------------------------------------------------------------

@router.post("/price-search/batch")
async def trigger_batch_search(
    req: BatchSearchRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    """Trigger web price search for multiple items."""
    if not req.item_ids:
        raise HTTPException(status_code=400, detail="No item_ids provided")

    logger.debug(f"Batch search requested for {len(req.item_ids)} items")
    logger.debug(f"Descriptions provided: {req.descriptions}")

    # For each item, trigger search in background
    for item_id in req.item_ids:
        if is_synthetic_item_id(item_id):
            # Synthetic cell
            description = (req.descriptions or {}).get(item_id) if req.descriptions else None
            logger.debug(f"Synthetic item {item_id}: description from request = {description!r}")
            if not description:
                description = f"Spreadsheet cell"
                logger.debug(f"  -> Using fallback description: {description!r}")
            _status_cache[item_id] = "searching"
            await emit(AGENT_SPAWN, {"agent": "lookup", "item_id": item_id})
            await emit(AGENT_RESULT, {
                "agent": "lookup",
                "item_id": item_id,
                "resolved": True,
                "description": description,
            })
            background_tasks.add_task(
                _run_search_task,
                item_id=item_id,
                description=description,
                unit="kom",
                quantity=None,
                file_id="",
                include_vat=req.include_vat,
                include_shipping=req.include_shipping,
            )
        else:
            # Real database item
            item = db.query(BoQItem).filter(BoQItem.id == item_id).first()
            if not item:
                logger.warning(f"Item {item_id} not found in database")
                continue
            description = item.full_description or item.description or ""
            if len(description) < 3:
                continue
            _status_cache[item_id] = "searching"
            background_tasks.add_task(
                _run_search_task,
                item_id=item_id,
                description=description,
                unit=item.unit or "kom",
                quantity=item.quantity,
                file_id=item.file_id or "",
                include_vat=req.include_vat,
                include_shipping=req.include_shipping,
            )

    return {"status": "started", "item_count": len(req.item_ids)}


# ---------------------------------------------------------------------------
# Single item search
# ---------------------------------------------------------------------------

@router.post("/price-search/{item_id}")
async def trigger_price_search(
    item_id: str,
    req: PriceSearchRequest | None = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    """Trigger a web price search for a BoQ item. Results stream via WebSocket.

    Supports both real database items and synthetic spreadsheet cell references.
    Synthetic items (format: excel-cell-ROW-COL-TIMESTAMP) are resolved via the lookup agent.
    """
    req = req or PriceSearchRequest()

    # Check if this is a synthetic item (from spreadsheet cell)
    if is_synthetic_item_id(item_id):
        await emit(AGENT_SPAWN, {"agent": "lookup", "item_id": item_id})
        try:
            parsed = parse_synthetic_item_id(item_id)
            if not parsed:
                raise HTTPException(status_code=400, detail="Invalid synthetic item ID format")

            # Use description from request, or create a minimal one
            description = req.description or f"Spreadsheet cell (Row {parsed['row']}, Col {parsed['col']})"
            logger.debug(f"Single-item search: synthetic item {item_id}")
            logger.debug(f"  Description from request: {req.description!r}")
            logger.debug(f"  Final description: {description!r}")

            # Create virtual item
            item = resolve_synthetic_item(item_id, description, "", db)

            await emit(
                AGENT_RESULT,
                {
                    "agent": "lookup",
                    "item_id": item_id,
                    "resolved": True,
                    "description": description,
                },
            )
        except Exception as exc:
            logger.exception("Lookup agent failed for synthetic item %s", item_id)
            await emit(
                AGENT_ERROR,
                {"agent": "lookup", "item_id": item_id, "error": str(exc)},
            )
            raise HTTPException(status_code=400, detail=f"Failed to resolve item: {exc}")
    else:
        # Regular database item lookup
        item = db.query(BoQItem).filter(BoQItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

    description = item.full_description or item.description or ""
    if len(description) < 3:
        raise HTTPException(status_code=400, detail="Item description too short for search")

    _status_cache[item_id] = "searching"
    await emit(SEARCH_STARTED, {"item_id": item_id, "description": description})

    # Run search in background
    background_tasks.add_task(
        _run_search_task,
        item_id=item_id,
        description=description,
        unit=item.unit or "kom",
        quantity=req.quantity or item.quantity or None,
        file_id=item.file_id or "",
        include_vat=req.include_vat,
        include_shipping=req.include_shipping,
    )

    return {"status": "started", "item_id": item_id}


async def _run_search_task(
    item_id: str,
    description: str,
    unit: str,
    quantity: float | None,
    file_id: str,
    include_vat: bool,
    include_shipping: bool,
) -> None:
    """Background task that runs the price search agent and emits WS events."""
    try:
        rules = PricingRules(
            include_vat=include_vat,
            include_shipping=include_shipping,
        )

        result = await run_price_search(
            description=description,
            unit=unit,
            quantity=quantity,
            file_id=file_id,
            pricing_rules=rules,
        )

        # Emit individual quotes
        for quote in result.quotes:
            await emit(SEARCH_QUOTE_FOUND, {
                "item_id": item_id,
                "quote": quote.model_dump(),
            })

        # Cache and emit completion
        _result_cache[item_id] = result
        _status_cache[item_id] = "done"

        await emit(SEARCH_COMPLETE, {
            "item_id": item_id,
            "quote_count": len(result.quotes),
            "best_quote": result.best_quote.model_dump() if result.best_quote else None,
            "computed": result.computed,
            "reasoning": result.reasoning,
            "search_log": result.search_log,
        })

    except Exception as exc:
        logger.exception("Price search failed for %s", item_id)
        _status_cache[item_id] = "error"
        await emit(SEARCH_COMPLETE, {
            "item_id": item_id,
            "error": str(exc),
            "search_log": [],
        })


# ---------------------------------------------------------------------------
# Result retrieval
# ---------------------------------------------------------------------------

@router.get("/price-search/{item_id}/result")
async def get_search_result(item_id: str):
    """Retrieve cached search result for an item."""
    result = _result_cache.get(item_id)
    if result is None:
        status = _status_cache.get(item_id, "idle")
        if status == "searching":
            return {"status": "searching"}
        raise HTTPException(status_code=404, detail="No search result for this item")
    return {"status": "done", "result": result.model_dump()}


@router.get("/price-search/{item_id}/status")
async def get_search_status(item_id: str):
    """Check search status for an item."""
    return {"status": _status_cache.get(item_id, "idle")}
