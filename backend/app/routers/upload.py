from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.boq import BoQFile, BoQItem, BoQUnit
from app.schemas.boq import FileUploadResponse
from app.services.boq_indexer import index_file
from app.services.rag import index_items as rag_index_items

router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    file_bytes = await file.read()
    file_id = str(uuid.uuid4())

    # Save original file to disk for Excel view
    uploads_dir = Path("data/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    stored_path = uploads_dir / f"{file_id}.xlsx"
    stored_path.write_bytes(file_bytes)

    result = index_file(
        file_path=file_id,
        file_bytes=file_bytes,
        file_date=datetime.utcnow(),
    )

    if not result["success"]:
        raise HTTPException(status_code=422, detail=result.get("error", "Failed to parse file"))

    # Persist file record
    db_file = BoQFile(
        id=file_id,
        file_name=file.filename or "unknown.xlsx",
        file_path=file_id,
        stored_path=str(stored_path),
        file_type=(file.filename or "").rsplit(".", 1)[-1] if file.filename else "xlsx",
        file_date=datetime.utcnow(),
        sheet_count=result["file"]["sheetCount"],
        item_count=result["file"]["itemCount"],
        project_name=result["file"].get("projectName"),
        column_mapping=None,
        missing_data=result["file"].get("missingData"),
        raw_preview=result["file"].get("rawPreview"),
        indexed_at=datetime.utcnow(),
    )
    db.add(db_file)

    # Persist items
    for item_data in result["items"]:
        item_id = f"{file_id}:{item_data.get('sheetName', '')}:{item_data['row']}"
        db_item = BoQItem(
            id=item_id,
            file_id=file_id,
            sheet_name=item_data.get("sheetName"),
            row=item_data["row"],
            item_number=item_data.get("itemNumber"),
            description=item_data["description"],
            full_description=item_data.get("fullDescription"),
            parent_item_number=item_data.get("parentItemNumber"),
            unit=item_data.get("unit"),
            quantity=item_data.get("quantity", 0),
            unit_price=item_data.get("unitPrice", 0),
            total=item_data.get("total", 0),
            unit_id=None,
            project_name=item_data.get("projectName"),
            date=item_data.get("date"),
        )
        db.add(db_item)

    # Persist units
    for unit_data in result.get("units", []):
        db_unit = BoQUnit(
            id=unit_data["id"],
            file_id=file_id,
            sheet_name=unit_data["sheetName"],
            parent_item_number=unit_data["parentItemNumber"],
            parent_title=unit_data.get("parentTitle"),
            parent_description=unit_data.get("parentDescription"),
            start_row=unit_data["startRow"],
            end_row=unit_data["endRow"],
            item_ids=unit_data["itemIds"],
            subtotal=unit_data.get("subtotal"),
            item_count=unit_data.get("itemCount", 0),
        )
        db.add(db_unit)

    db.commit()

    # Index items into RAG for vector search
    parent_map = {
        u.get("parentItemNumber", ""): u.get("parentDescription") or u.get("parentTitle") or ""
        for u in result.get("units", [])
    }
    rag_index_items(file_id, result["items"], parent_map)

    return FileUploadResponse(
        file_id=file_id,
        file_name=file.filename or "unknown.xlsx",
        sheets=result["file"].get("sheets", []),
        item_count=result["file"]["itemCount"],
    )
