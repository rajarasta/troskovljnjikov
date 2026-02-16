"""Match service — business logic for BoQ item matching and price history.

Extracted from routers/items.py to keep routes thin and logic testable.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.boq import BoQFile, BoQItem, BoQUnit
from app.schemas.boq import (
    BoQItemSchema,
    MatchGroup,
    MatchRequest,
    MatchResponse,
    MatchResult,
    PriceHistoryInstance,
    PriceHistoryRequest,
    PriceHistoryResponse,
)
from app.services.rag import search as rag_search


# ── Stats helpers ──────────────────────────────────────────────────────


def build_stats(prices: list[float]) -> dict[str, Any]:
    return {
        "count": len(prices),
        "avgPrice": sum(prices) / len(prices) if prices else 0,
        "minPrice": min(prices) if prices else 0,
        "maxPrice": max(prices) if prices else 0,
        "priceRange": (max(prices) - min(prices)) if prices else 0,
        "statusCounts": {},
    }


def empty_stats() -> dict[str, Any]:
    return build_stats([])


# ── Quantity comparison ────────────────────────────────────────────────


def quantity_comparison(selected_qty: float, match_qty: float) -> dict[str, Any]:
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


# ── RAG hit processing ─────────────────────────────────────────────────


def process_hits(
    hits: list[dict],
    threshold: float,
    quantity: float | None,
    db: Session,
) -> tuple[list[MatchResult], list[float]]:
    """Process RAG hits into MatchResult objects. Returns (results, prices)."""
    item_hits: list[tuple[dict, str]] = []
    unit_hits: list[tuple[dict, str]] = []
    for h in hits:
        meta = h.get("metadata", {})
        entity = meta.get("entity_type", "item")
        if entity == "unit":
            unit_id = meta.get("unit_id", "")
            if unit_id:
                unit_hits.append((h, unit_id))
        else:
            item_id = meta.get("item_id", "")
            if not item_id:
                item_id = h["id"]
            item_hits.append((h, item_id))

    # Batch-load items and units
    items_by_id = {}
    if item_hits:
        ids = [iid for _, iid in item_hits]
        items_by_id = {
            i.id: i for i in db.query(BoQItem).filter(BoQItem.id.in_(ids)).all()
        }

    units_by_id = {}
    if unit_hits:
        ids = [uid for _, uid in unit_hits]
        units_by_id = {
            u.id: u for u in db.query(BoQUnit).filter(BoQUnit.id.in_(ids)).all()
        }

    file_ids = {u.file_id for u in units_by_id.values()}
    file_ids |= {i.file_id for i in items_by_id.values()}
    files_by_id = {}
    if file_ids:
        files_by_id = {
            f.id: f
            for f in db.query(BoQFile).filter(BoQFile.id.in_(list(file_ids))).all()
        }

    results: list[MatchResult] = []
    prices: list[float] = []

    # Item hits
    for hit, db_id in item_hits:
        item = items_by_id.get(db_id)
        if not item:
            continue
        similarity = hit["similarity"]
        if similarity < threshold:
            continue
        qty_comp = None
        if quantity is not None:
            qty_comp = quantity_comparison(quantity, item.quantity or 0)
        item_schema = BoQItemSchema.model_validate(item)
        db_file = files_by_id.get(item.file_id)
        if db_file:
            item_schema.file_name = db_file.file_name
        results.append(MatchResult(
            item=item_schema,
            similarity=similarity,
            quantity_comparison=qty_comp,
        ))
        if item.unit_price and item.unit_price > 0:
            prices.append(item.unit_price)

    # Unit hits
    for hit, db_unit_id in unit_hits:
        unit = units_by_id.get(db_unit_id)
        if not unit:
            continue
        similarity = hit["similarity"]
        if similarity < threshold:
            continue
        db_file = files_by_id.get(unit.file_id)
        subtotal = unit.subtotal or 0
        item_count = unit.item_count or 1
        synthetic = BoQItemSchema(
            id=unit.id,
            file_id=unit.file_id,
            sheet_name=unit.sheet_name,
            row=unit.start_row,
            item_number=unit.parent_item_number,
            description=unit.parent_description or unit.parent_title or "",
            full_description=unit.parent_description,
            parent_item_number=None,
            unit="komplet",
            quantity=1,
            unit_price=subtotal / item_count if item_count else subtotal,
            total=subtotal,
            project_name=db_file.project_name if db_file else None,
            date=db_file.file_date.isoformat() if db_file and db_file.file_date else None,
            item_type="unit",
            file_name=db_file.file_name if db_file else None,
        )
        qty_comp = None
        if quantity is not None:
            qty_comp = quantity_comparison(quantity, 1)
        results.append(MatchResult(
            item=synthetic, similarity=similarity, quantity_comparison=qty_comp,
        ))
        if subtotal > 0:
            prices.append(subtotal / item_count if item_count else subtotal)

    results.sort(key=lambda r: r.similarity, reverse=True)
    return results, prices


# ── Match entry points ─────────────────────────────────────────────────


def flat_match(req: MatchRequest, db: Session) -> MatchResponse:
    """Standard flat matching: RAG search on combined description text."""
    hits = rag_search(query_text=req.description, top_k=req.max_results)
    if not hits:
        return MatchResponse(matches=[], stats=empty_stats())
    results, prices = process_hits(hits, req.threshold, req.quantity, db)
    return MatchResponse(matches=results, stats=build_stats(prices))


def match_with_row_lookup(req: MatchRequest, db: Session) -> MatchResponse:
    """Composite detection: look up parsed items by file_id + row range."""
    db_items = (
        db.query(BoQItem)
        .filter(
            BoQItem.file_id == req.file_id,
            BoQItem.row >= req.start_row,
            BoQItem.row <= req.end_row,
        )
        .order_by(BoQItem.row)
        .all()
    )

    if not db_items:
        return flat_match(req, db)

    # Detect composite sub-items
    composite_subs = [i for i in db_items if i.item_type == "composite_sub"]
    if not composite_subs:
        return flat_match(req, db)

    # Resolve parent description
    parent_desc: str | None = None
    first_sub = composite_subs[0]
    if first_sub.unit_id:
        parent_unit = db.query(BoQUnit).filter(BoQUnit.id == first_sub.unit_id).first()
        if parent_unit:
            parent_desc = parent_unit.parent_description or parent_unit.parent_title
    if not parent_desc and first_sub.parent_item_number:
        parent_item = (
            db.query(BoQItem)
            .filter(
                BoQItem.file_id == req.file_id,
                BoQItem.item_number == first_sub.parent_item_number,
                BoQItem.item_type == "section_header",
            )
            .first()
        )
        if parent_item:
            parent_desc = parent_item.full_description or parent_item.description

    # Match each sub-item individually
    groups: list[MatchGroup] = []
    all_prices: list[float] = []

    for sub_item in composite_subs:
        query_text = sub_item.full_description or sub_item.description
        hits = rag_search(
            query_text=query_text,
            top_k=req.max_results,
            file_id_exclude=req.file_id,
        )
        group_results, group_prices = process_hits(
            hits, req.threshold, sub_item.quantity or None, db,
        )
        all_prices.extend(group_prices)
        groups.append(MatchGroup(
            sub_item=BoQItemSchema.model_validate(sub_item),
            matches=group_results,
            stats=build_stats(group_prices),
        ))

    return MatchResponse(
        matches=[],
        stats=build_stats(all_prices),
        groups=groups,
        is_composite=True,
        parent_description=parent_desc,
    )


def find_matches(req: MatchRequest, db: Session) -> MatchResponse:
    """Main entry point: dispatches to flat or composite matching."""
    if req.file_id and req.start_row is not None and req.end_row is not None:
        return match_with_row_lookup(req, db)
    return flat_match(req, db)


# ── Price history ──────────────────────────────────────────────────────


def get_price_history(req: PriceHistoryRequest, db: Session) -> PriceHistoryResponse:
    """Search for historical price instances across all indexed files."""
    hits = rag_search(query_text=req.description, top_k=req.top_k)

    instances: list[PriceHistoryInstance] = []
    totals: list[float] = []

    for hit in hits:
        if hit["similarity"] < req.similarity_threshold:
            continue

        metadata = hit.get("metadata", {})
        entity_type = metadata.get("entity_type", "item")
        file_id = metadata.get("file_id", "")

        # Load file metadata
        db_file = db.query(BoQFile).filter(BoQFile.id == file_id).first()
        file_name = db_file.file_name if db_file else ""
        project_name = db_file.project_name if db_file else None
        file_date = db_file.file_date.isoformat() if db_file and db_file.file_date else None
        date_source = db_file.date_source if db_file else None

        if entity_type == "unit":
            unit_id = metadata.get("unit_id", "")
            db_unit = db.query(BoQUnit).filter(BoQUnit.id == unit_id).first()
            sub_items_data: list[dict] = []
            subtotal = None
            if db_unit:
                subtotal = db_unit.subtotal
                child_items = (
                    db.query(BoQItem)
                    .filter(BoQItem.id.in_(db_unit.item_ids or []))
                    .order_by(BoQItem.row)
                    .all()
                )
                for ci in child_items:
                    sub_items_data.append({
                        "label": ci.description,
                        "unit": ci.unit,
                        "quantity": ci.quantity,
                        "unit_price": ci.unit_price,
                        "total": ci.total,
                    })
                if subtotal and subtotal > 0:
                    totals.append(subtotal)

            instances.append(PriceHistoryInstance(
                file_name=file_name,
                project_name=project_name,
                file_date=file_date,
                date_source=date_source,
                similarity=hit["similarity"],
                entity_type="unit",
                sub_items=sub_items_data if sub_items_data else None,
                subtotal=subtotal,
            ))
        else:
            item_id = metadata.get("item_id") or hit["id"]
            db_item = db.query(BoQItem).filter(BoQItem.id == item_id).first()
            if db_item:
                if db_item.total and db_item.total > 0:
                    totals.append(db_item.total)
                instances.append(PriceHistoryInstance(
                    file_name=file_name,
                    project_name=project_name,
                    file_date=file_date,
                    date_source=date_source,
                    similarity=hit["similarity"],
                    entity_type="item",
                    unit=db_item.unit,
                    quantity=db_item.quantity,
                    unit_price=db_item.unit_price,
                    total=db_item.total,
                ))

    instances.sort(key=lambda x: x.file_date or "", reverse=True)

    stats = {
        "count": len(instances),
        "avg_total": sum(totals) / len(totals) if totals else 0,
        "min_total": min(totals) if totals else 0,
        "max_total": max(totals) if totals else 0,
    }

    return PriceHistoryResponse(
        query=req.description,
        match_count=len(instances),
        instances=instances,
        stats=stats,
    )
