from __future__ import annotations

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
from app.services.boq_matcher import (
    calculate_match_stats,
    calculate_quantity_comparison,
    find_similar_descriptions,
)

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
    # Load all historical items from DB
    all_items = db.query(BoQItem).all()

    # Convert ORM objects to dicts for the matcher
    item_dicts = []
    for item in all_items:
        item_dicts.append({
            "id": item.id,
            "fileId": item.file_id,
            "sheetName": item.sheet_name,
            "row": item.row,
            "itemNumber": item.item_number,
            "description": item.description,
            "fullDescription": item.full_description,
            "parentItemNumber": item.parent_item_number,
            "unit": item.unit,
            "quantity": item.quantity or 0,
            "unitPrice": item.unit_price or 0,
            "total": item.total or 0,
            "projectName": item.project_name,
            "date": item.date,
        })

    matches = find_similar_descriptions(
        query=req.description,
        items=item_dicts,
        threshold=req.threshold,
        max_results=req.max_results,
        query_unit=req.unit,
        query_code=req.item_number,
    )

    stats = calculate_match_stats(matches)

    results = []
    for m in matches:
        qty_comp = None
        if req.quantity is not None:
            qty_comp = calculate_quantity_comparison(req.quantity, m.get("quantity", 0))

        results.append(MatchResult(
            item=BoQItemSchema(
                id=m["id"],
                file_id=m["fileId"],
                sheet_name=m.get("sheetName"),
                row=m["row"],
                item_number=m.get("itemNumber"),
                description=m["description"],
                full_description=m.get("fullDescription"),
                parent_item_number=m.get("parentItemNumber"),
                unit=m.get("unit"),
                quantity=m.get("quantity", 0),
                unit_price=m.get("unitPrice", 0),
                total=m.get("total", 0),
                project_name=m.get("projectName"),
                date=m.get("date"),
            ),
            similarity=m.get("similarity", 0),
            quantity_comparison=qty_comp,
        ))

    return MatchResponse(matches=results, stats=stats)
