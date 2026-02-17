"""Match and price history schemas."""

from pydantic import BaseModel

from .item_schemas import BoQItemSchema


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
    use_llm_ranking: bool = False


class MatchResult(BaseModel):
    item: BoQItemSchema
    similarity: float
    quantity_comparison: dict | None = None
    llm_confidence: int | None = None
    llm_reasoning: str | None = None


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
