from datetime import datetime

from pydantic import BaseModel, field_validator


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
    raw_preview: dict[str, list[list[str]]] | None = None
    date_source: str | None = None
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
    item_type: str | None = None
    material_price: float | None = None
    labor_price: float | None = None
    material_total: float | None = None
    labor_total: float | None = None
    notes: str | None = None
    drawing_path: str | None = None
    llm_response: str | None = None

    model_config = {"from_attributes": True}


class PriceHistoryRequest(BaseModel):
    description: str
    top_k: int = 50
    similarity_threshold: float = 0.3


class PriceHistoryInstance(BaseModel):
    file_name: str
    project_name: str | None = None
    file_date: str | None = None
    date_source: str | None = None
    similarity: float
    entity_type: str  # "unit" or "item"
    sub_items: list[dict] | None = None  # for units
    subtotal: float | None = None
    unit: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    total: float | None = None


class PriceHistoryResponse(BaseModel):
    query: str
    match_count: int
    instances: list[PriceHistoryInstance]
    stats: dict


class MatchRequest(BaseModel):
    description: str
    quantity: float | None = None
    unit: str | None = None
    item_number: str | None = None
    threshold: float = 0.3
    max_results: int = 20
    # Optional: file context for composite unit detection (0-based row indices)
    file_id: str | None = None
    start_row: int | None = None
    end_row: int | None = None


class MatchResult(BaseModel):
    item: BoQItemSchema
    similarity: float
    quantity_comparison: dict | None = None


class MatchGroup(BaseModel):
    """Matches for a single sub-item within a composite unit."""
    sub_item: BoQItemSchema
    matches: list[MatchResult]
    stats: dict


class MatchResponse(BaseModel):
    matches: list[MatchResult]
    stats: dict
    groups: list[MatchGroup] | None = None
    is_composite: bool = False
    parent_description: str | None = None


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
    id: str
    item_id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id_to_str(cls, v: object) -> str:
        return str(v)
