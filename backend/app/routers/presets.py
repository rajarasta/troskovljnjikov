import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.preset import Preset
from app.schemas.preset import PresetCreate, PresetUpdate, PresetSchema

router = APIRouter()


@router.get("/presets", response_model=list[PresetSchema])
def list_presets(db: Session = Depends(get_db)):
    return db.query(Preset).order_by(Preset.is_default.desc(), Preset.name).all()


@router.get("/presets/{preset_id}", response_model=PresetSchema)
def get_preset(preset_id: str, db: Session = Depends(get_db)):
    preset = db.query(Preset).filter(Preset.id == preset_id).first()
    if not preset:
        raise HTTPException(404, "Preset not found")
    return preset


@router.post("/presets", response_model=PresetSchema, status_code=201)
def create_preset(body: PresetCreate, db: Session = Depends(get_db)):
    preset = Preset(
        id=str(uuid.uuid4()),
        name=body.name,
        description=body.description,
        groups=body.groups,
        is_default=False,
    )
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return preset


@router.put("/presets/{preset_id}", response_model=PresetSchema)
def update_preset(preset_id: str, body: PresetUpdate, db: Session = Depends(get_db)):
    preset = db.query(Preset).filter(Preset.id == preset_id).first()
    if not preset:
        raise HTTPException(404, "Preset not found")
    if preset.is_default:
        raise HTTPException(403, "Cannot modify default presets")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(preset, field, value)
    db.commit()
    db.refresh(preset)
    return preset


@router.delete("/presets/{preset_id}", status_code=204)
def delete_preset(preset_id: str, db: Session = Depends(get_db)):
    preset = db.query(Preset).filter(Preset.id == preset_id).first()
    if not preset:
        raise HTTPException(404, "Preset not found")
    if preset.is_default:
        raise HTTPException(403, "Cannot delete default presets")
    db.delete(preset)
    db.commit()
