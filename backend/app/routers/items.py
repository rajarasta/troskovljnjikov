"""Item and match endpoints — thin wrappers around match_service."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.boq import BoQItem
from app.schemas.boq import (
    BoQItemSchema,
    MatchRequest,
    MatchResponse,
    PriceHistoryRequest,
    PriceHistoryResponse,
)
from app.services.match_service import find_matches, get_price_history

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


@router.post("/items/{item_id}/drawing")
async def upload_drawing(
    item_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a drawing image and attach it to a BoQ item."""
    item = db.query(BoQItem).filter(BoQItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    upload_dir = Path("uploads/drawings")
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename).suffix or ".png"
    dest = upload_dir / f"{item_id}{ext}"
    content = await file.read()
    dest.write_bytes(content)

    item.drawing_path = str(dest)
    db.commit()
    return {"drawing_path": str(dest)}


@router.post("/match", response_model=MatchResponse)
def match_items(
    req: MatchRequest,
    db: Session = Depends(get_db),
):
    """Search for historical price data via RAG against request description."""
    return find_matches(req, db)


@router.post("/price-history", response_model=PriceHistoryResponse)
def price_history(
    req: PriceHistoryRequest,
    db: Session = Depends(get_db),
):
    """Search for historical price instances across all indexed files."""
    return get_price_history(req, db)
