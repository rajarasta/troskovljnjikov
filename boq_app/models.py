"""Pydantic UI models for the BoQ Matcher.

These mirror the backend models in .worktrees/boq-editor/backend/src/models/
and add UI-specific fields (match_status, suggested_price, etc.).
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class MatchStatus(str, Enum):
    PENDING = "pending"
    MATCHING = "matching"
    MATCHED = "matched"
    APPLIED = "applied"
    NO_MATCH = "no_match"
    ERROR = "error"


class PipelineStepStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    DONE = "done"
    ERROR = "error"


# --- BoQ Item Models (mirrors boq.py LogicalUnit / PricedLine) ---


class PricedLineUI(BaseModel):
    item_number: str
    description: str = ""
    unit: str = ""
    quantity: float = 0.0
    unit_price: Optional[float] = None
    total: Optional[float] = None
    suggested_price: Optional[float] = None
    suggestion_confidence: Optional[float] = None
    applied_price: Optional[float] = None
    excel_row: int = 0


class BoQItemUI(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    item_number: str
    title: str
    description: str = ""
    level: int = 0  # 0=chapter, 1=section, 2=subsection, 3=work_item
    parent_chapter: str = ""
    parent_section: str = ""
    priced_lines: list[PricedLineUI] = []
    excel_start_row: int = 0
    excel_end_row: int = 0
    match_status: MatchStatus = MatchStatus.PENDING
    total: Optional[float] = None


class ParsedFileUI(BaseModel):
    filename: str
    sheet_name: str
    format_detected: str
    chapter_title: str = ""
    items: list[BoQItemUI] = []
    total_rows: int = 0
    metadata: dict = {}


# --- Historic Match Models (mirrors historic.py) ---


class HistoricMatchLineUI(BaseModel):
    item_number: str
    description: str = ""
    unit_of_measure: str = ""
    quantity: float = 0.0
    unit_price: Optional[float] = None
    total: Optional[float] = None


class ConfidenceBreakdownUI(BaseModel):
    text_similarity: float = 0.0
    unit_match: float = 0.0
    hierarchy_match: float = 0.0
    description_overlap: float = 0.0

    @computed_field
    @property
    def overall(self) -> float:
        return round(
            self.text_similarity * 0.4
            + self.unit_match * 0.25
            + self.hierarchy_match * 0.2
            + self.description_overlap * 0.15,
            4,
        )


class HistoricMatchUI(BaseModel):
    match_id: str
    source_file: str
    project_name: str
    year: str = ""
    match_confidence: float
    confidence_breakdown: ConfidenceBreakdownUI = Field(
        default_factory=ConfidenceBreakdownUI
    )
    qty_delta_pct: float = 0.0
    matched_lines: list[HistoricMatchLineUI] = []
    avg_unit_price: float = 0.0
    total: float = 0.0


# --- Price Stats ---


class PriceStatsUI(BaseModel):
    avg_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0
    num_matches: int = 0
    currency: str = "EUR"


# --- LLM Observability ---


class ReasoningEntryUI(BaseModel):
    timestamp: str
    agent_name: str
    message: str
    entry_type: str = "info"  # "thinking" | "result" | "error" | "info"


class PipelineStepUI(BaseModel):
    name: str
    status: PipelineStepStatus = PipelineStepStatus.PENDING
    detail: str = ""
