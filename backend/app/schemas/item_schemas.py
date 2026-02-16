"""Item-related schemas."""

from pydantic import BaseModel


class BoQItemSchema(BaseModel):
    id: str
    file_id: str
    sheet_name: str | None
    row: int
    item_number: str | None
    description: str
    full_description: str | None
    parent_item_number: str | None
    unit: str | None
    quantity: float
    unit_price: float
    total: float
    project_name: str | None
    date: str | None
    item_type: str | None = None
    material_price: float | None = None
    labor_price: float | None = None
    material_total: float | None = None
    labor_total: float | None = None
    notes: str | None = None
    drawing_path: str | None = None
    llm_response: str | None = None
    file_name: str | None = None

    model_config = {"from_attributes": True}


class StatusUpdate(BaseModel):
    status: str
    notes: str | None = None


class CellUpdate(BaseModel):
    sheet: str
    row: int
    col: int
    value: str | float | None
