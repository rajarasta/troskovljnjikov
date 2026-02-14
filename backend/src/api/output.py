from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .upload import get_current_boq

router = APIRouter()


class LineUpdate(BaseModel):
    item_number: str
    unit_price: float
    accepted: bool = True


class OutputUpdate(BaseModel):
    line_updates: list[LineUpdate]


# In-memory storage for user edits
_output_data: dict[str, list[LineUpdate]] = {}


def get_output_data() -> dict[str, list[LineUpdate]]:
    return _output_data


@router.put("/output/{unit_id}")
async def save_output(unit_id: str, body: OutputUpdate):
    boq = get_current_boq()
    if not boq:
        raise HTTPException(404, "No BoQ uploaded yet")
    found = any(u.id == unit_id for u in boq.units)
    if not found:
        raise HTTPException(404, f"Unit {unit_id} not found")
    _output_data[unit_id] = body.line_updates
    return {"status": "saved", "unit_id": unit_id}
