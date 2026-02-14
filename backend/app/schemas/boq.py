from datetime import datetime

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    file_id: str
    file_name: str
    sheets: list[dict]
    item_count: int


class FileInfo(BaseModel):
    id: str
    file_name: str
    file_type: str
    project_name: str | None
    item_count: int
    sheet_count: int
    indexed_at: datetime

    model_config = {"from_attributes": True}


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

    model_config = {"from_attributes": True}


class MatchRequest(BaseModel):
    description: str
    quantity: float | None = None
    threshold: float = 0.3
    max_results: int = 20


class MatchResult(BaseModel):
    item: BoQItemSchema
    similarity: float
    quantity_comparison: dict | None = None


class MatchResponse(BaseModel):
    matches: list[MatchResult]
    stats: dict


class StatusUpdate(BaseModel):
    status: str
    notes: str | None = None


class CellUpdate(BaseModel):
    sheet: str
    row: int
    col: int
    value: str | float | None


class ChatRequest(BaseModel):
    message: str


class ChatMessageSchema(BaseModel):
    id: int
    item_id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
