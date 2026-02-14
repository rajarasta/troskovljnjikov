from fastapi import APIRouter, HTTPException

from ..models.boq import LogicalUnit
from .upload import get_current_boq

router = APIRouter()


@router.get("/units", response_model=list[LogicalUnit])
async def list_units():
    boq = get_current_boq()
    if not boq:
        raise HTTPException(404, "No BoQ uploaded yet")
    return boq.units


@router.get("/units/{unit_id}", response_model=LogicalUnit)
async def get_unit(unit_id: str):
    boq = get_current_boq()
    if not boq:
        raise HTTPException(404, "No BoQ uploaded yet")
    for unit in boq.units:
        if unit.id == unit_id:
            return unit
    raise HTTPException(404, f"Unit {unit_id} not found")
