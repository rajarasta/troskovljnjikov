from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.boq import BoQFile, BoQItem
from app.schemas.boq import BoQItemSchema, FileInfo
from app.services.workbook_converter import xlsx_to_workbook_data


# Cache converted workbook data — avoids re-parsing xlsx on every click.
# Key: (file_id, stored_path).  Max 8 files in cache.
@lru_cache(maxsize=8)
def _cached_workbook_data(file_id: str, stored_path: str) -> dict:
    return xlsx_to_workbook_data(stored_path)

router = APIRouter()


@router.get("/files", response_model=list[FileInfo])
def list_files(db: Session = Depends(get_db)):
    files = db.query(BoQFile).order_by(BoQFile.indexed_at.desc()).all()
    return files


@router.get("/files/{file_id}", response_model=FileInfo)
def get_file(file_id: str, db: Session = Depends(get_db)):
    f = db.query(BoQFile).filter(BoQFile.id == file_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    return f


@router.get("/files/{file_id}/items", response_model=list[BoQItemSchema])
def get_file_items(file_id: str, db: Session = Depends(get_db)):
    f = db.query(BoQFile).filter(BoQFile.id == file_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    items = db.query(BoQItem).filter(BoQItem.file_id == file_id).order_by(BoQItem.row).all()
    return items


@router.delete("/files/{file_id}")
def delete_file(file_id: str, db: Session = Depends(get_db)):
    f = db.query(BoQFile).filter(BoQFile.id == file_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    db.delete(f)
    db.commit()
    return {"ok": True}


@router.get("/files/{file_id}/xlsx")
def get_file_xlsx(file_id: str, db: Session = Depends(get_db)):
    f = db.query(BoQFile).filter(BoQFile.id == file_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    if not f.stored_path or not Path(f.stored_path).is_file():
        raise HTTPException(status_code=404, detail="Original xlsx file not available")
    return FileResponse(
        path=f.stored_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f.file_name,
    )


@router.get("/files/{file_id}/workbook-data")
def get_workbook_data(file_id: str, db: Session = Depends(get_db)):
    f = db.query(BoQFile).filter(BoQFile.id == file_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    if not f.stored_path or not Path(f.stored_path).is_file():
        raise HTTPException(status_code=404, detail="Original xlsx file not available")
    return _cached_workbook_data(f.id, f.stored_path)
