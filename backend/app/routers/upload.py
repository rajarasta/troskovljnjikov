from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.boq import BoQFile, BoQItem, BoQUnit
from app.schemas.boq import FileUploadResponse
from app.services.autopilot import run_autopilot
from app.services.indexer import index_file
from app.services.rag import index_items as rag_index_items, index_for_search

router = APIRouter()

# XLSX file magic bytes (signature)
XLSX_MAGIC_BYTES = b'PK\x03\x04'  # ZIP file signature


def _validate_file_size(file_bytes: bytes) -> None:
    """Validate file size against MAX_UPLOAD_SIZE_MB setting."""
    max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB}MB",
        )


def _validate_file_type(filename: str | None, file_bytes: bytes) -> None:
    """Validate file type by extension and magic bytes."""
    if not filename:
        raise HTTPException(status_code=400, detail="File name is required")

    # Check extension
    valid_extensions = {".xlsx", ".xls", ".csv", ".xml"}
    file_ext = Path(filename).suffix.lower()
    if file_ext not in valid_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Accepted types: {', '.join(valid_extensions)}",
        )

    # Check magic bytes for XLSX (ZIP archive)
    if file_ext == ".xlsx":
        if not file_bytes.startswith(XLSX_MAGIC_BYTES):
            raise HTTPException(
                status_code=400,
                detail="Invalid XLSX file. File signature does not match.",
            )

    # Check magic bytes for XML
    if file_ext == ".xml":
        stripped = file_bytes.lstrip()
        if not stripped.startswith((b"<?xml", b"<")):
            raise HTTPException(
                status_code=400,
                detail="Invalid XML file. File does not appear to be valid XML.",
            )


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # Read file into memory
    file_bytes = await file.read()

    # Validate file size FIRST (before any processing)
    _validate_file_size(file_bytes)

    # Validate file type (extension + magic bytes)
    _validate_file_type(file.filename, file_bytes)

    file_id = str(uuid.uuid4())

    # Create temporary upload directory with cleanup on error
    uploads_dir = Path("data/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    stored_path = uploads_dir / f"{file_id}.xlsx"

    try:
        # Save original file to disk for Excel view
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
            column_mapping=result["file"].get("columnMappings"),
            missing_data=result["file"].get("missingData"),
            raw_preview=result["file"].get("rawPreview"),
            header_rows=result["file"].get("headerRows"),
            date_source="upload",
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
                item_type=item_data.get("itemType"),
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

        # Index items into RAG for vector search (dual-level)
        index_for_search(
            file_id=file_id,
            items=result["items"],
            units=result.get("units", []),
            file_date=result["file"].get("date"),
        )

        # Trigger autopilot in background (batch match + LLM summary + price suggestions)
        asyncio.create_task(run_autopilot(
            file_id=file_id,
            items=result["items"],
            units=result.get("units", []),
            file_info=result["file"],
        ))

        return FileUploadResponse(
            file_id=file_id,
            file_name=file.filename or "unknown.xlsx",
            sheets=result["file"].get("sheets", []),
            item_count=result["file"]["itemCount"],
        )
    except HTTPException:
        raise
    except Exception as e:
        # Clean up file on error
        if stored_path.exists():
            try:
                stored_path.unlink()
            except Exception as cleanup_error:
                print(f"Failed to clean up file {stored_path}: {cleanup_error}")
        raise HTTPException(status_code=500, detail="Failed to save file data") from e
