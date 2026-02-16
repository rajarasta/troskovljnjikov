"""File-related schemas."""

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
    raw_preview: dict[str, list[list[str]]] | None = None
    header_rows: dict[str, int] | None = None
    column_mapping: dict | None = None
    date_source: str | None = None
    indexed_at: datetime

    model_config = {"from_attributes": True}
