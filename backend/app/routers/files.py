from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.boq import BoQFile, BoQItem
from app.schemas.boq import BoQItemSchema, FileInfo

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
