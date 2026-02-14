"""Pydantic schemas for the 3-stage agent pipeline.

Field names aligned with Streamlit frontend models (boq_app/models.py).
These schemas are shared between:
- Backend pipeline (agent outputs)
- SSE events (serialized to JSON)
- Streamlit frontend (UI models consume these directly)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, computed_field


# --- Shared: Confidence Breakdown (used by Comparator + UI confidence bars) ---

class ConfidenceBreakdown(BaseModel):
    """Per-factor confidence scores for the UI confidence panel."""
    text_similarity: float = Field(ge=0, le=1)
    unit_match: float = Field(ge=0, le=1)
    hierarchy_match: float = Field(ge=0, le=1)
    description_overlap: float = Field(ge=0, le=1)

    @computed_field
    @property
    def overall(self) -> float:
        """Weighted average: text 40%, unit 25%, hierarchy 20%, description 15%."""
        return round(
            self.text_similarity * 0.4
            + self.unit_match * 0.25
            + self.hierarchy_match * 0.2
            + self.description_overlap * 0.15,
            4,
        )


# --- Shared: Reasoning log entry (consumed by reasoning panel) ---
# Frontend field: agent_name (not agent), entry_type for styling

class ReasoningEntry(BaseModel):
    """Single entry in the LLM reasoning log."""
    agent_name: str  # "classifier", "comparator", "pricer", "system"
    message: str
    entry_type: str = "info"  # "thinking", "result", "error", "info"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# --- Agent 1: Classifier output ---

class Deviation(BaseModel):
    field: str
    standard_value: str
    actual_value: str
    description: str


class ClassResult(BaseModel):
    taxonomy_id: str
    taxonomy_label: str
    confidence: float = Field(ge=0, le=1)
    deviations: list[Deviation] = []
    unmatched_rows: list[int] = []


# --- Agent 2: Comparator output ---
# Frontend fields: match_id, source_file, year, match_confidence,
#   confidence_breakdown, matched_lines (not historic_unit_id etc.)

class HistoricPriceLine(BaseModel):
    item_number: str = ""
    description: str
    unit_of_measure: str
    quantity: float
    unit_price: float
    total: Optional[float] = None


class HistoricComparison(BaseModel):
    match_id: int
    project_name: str
    source_file: str = ""
    year: int = 0
    match_confidence: float = 0.0  # overall score (float for frontend)
    confidence_breakdown: ConfidenceBreakdown
    matching_sub_items: list[str] = []
    missing_sub_items: list[str] = []
    extra_sub_items: list[str] = []
    qty_delta_pct: float = 0.0
    matched_lines: list[HistoricPriceLine] = []
    avg_unit_price: float = 0.0
    total: float = 0.0


class CompResult(BaseModel):
    classification: ClassResult
    matches: list[HistoricComparison] = []
    summary: str = ""


# --- Agent 3: Pricer output ---

class PriceRange(BaseModel):
    low: float
    high: float
    median: float


class LinePriceSuggestion(BaseModel):
    item_number: str
    suggested_price: float
    confidence: float = Field(ge=0, le=1)
    price_range: PriceRange
    reasoning: str = ""


class PriceResult(BaseModel):
    line_prices: list[LinePriceSuggestion] = []
    overall_reasoning: str = ""


# --- Pipeline stats (consumed by stats footer) ---
# Frontend field: num_matches (not match_count), currency

class PipelineStats(BaseModel):
    """Aggregate stats emitted at pipeline completion."""
    avg_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0
    num_matches: int = 0
    total_suggestions: int = 0
    currency: str = "EUR"
