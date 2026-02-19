"""Pricing Pipeline Models — SQLAlchemy ORM + Pydantic schemas for the
multi-agent pricing orchestrator.

SQLAlchemy:
- Article: persistent article catalog
- PricingRun: run metadata + artifacts

Pydantic:
- MaterialRequirement, ArticleCandidate, CatalogMatch,
  HistoricalPriceEvidence, PricePoint, PriceSuggestion3
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON

from app.database import Base


# ---------------------------------------------------------------------------
# SQLAlchemy ORM models
# ---------------------------------------------------------------------------


class Article(Base):
    """Persistent article catalog entry (pre-loaded from ERP / CSV)."""

    __tablename__ = "articles"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    unit = Column(String, default="kom")
    net_price = Column(Float, nullable=True)
    currency = Column(String, default="EUR")
    vat_rate = Column(Float, default=0.25)
    supplier = Column(String, nullable=True)
    category = Column(String, nullable=True)
    sku = Column(String, nullable=True)
    ean = Column(String, nullable=True)
    pack_qty = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PricingRun(Base):
    """Persistent record of a pricing pipeline execution."""

    __tablename__ = "pricing_runs"

    id = Column(String, primary_key=True)
    source_file = Column(String, nullable=False)
    status = Column(String, default="init")
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    item_count = Column(Integer, default=0)
    artifacts = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Pydantic schemas (inter-stage data transfer)
# ---------------------------------------------------------------------------


class MaterialRequirement(BaseModel):
    """A single material requirement extracted from the project XML."""

    req_id: str = Field(description="Unique ID for this requirement")
    description: str
    qty: float
    unit: str = "kom"
    derived_from: str = Field(
        default="", description="XML xpath or section that sourced this"
    )
    confidence: float = Field(ge=0, le=1, default=0.8)
    suggested_article_ids: list[str] = Field(default_factory=list)
    notes: str = ""


class ArticleCandidate(BaseModel):
    """A single article candidate with relevance score."""

    article_id: str
    name: str
    unit: str
    net_price: float | None = None
    relevance_score: float = Field(ge=0, le=1)
    match_reason: str = ""


class CatalogMatch(BaseModel):
    """Maps a MaterialRequirement to Article candidates."""

    req_id: str
    article_candidates: list[ArticleCandidate] = Field(default_factory=list)
    enrichment_notes: str = ""


class HistoricalPriceEvidence(BaseModel):
    """Historical price data point from ChromaDB."""

    source_boq_id: str
    matched_description: str = ""
    similarity: float
    unit_price: float
    unit: str
    file_date: str = ""
    file_id: str = ""


class PricePoint(BaseModel):
    """One of three price points (low/mid/high)."""

    label: Literal["low", "mid", "high"]
    unit_price_net: float
    currency: str = "EUR"
    unit: str
    rationale: str
    evidence_ids: list[str] = Field(
        default_factory=list, description="IDs of evidence used"
    )


class PriceSuggestion3(BaseModel):
    """3-point price output for a single material requirement."""

    req_id: str
    description: str
    unit: str
    points: list[PricePoint] = Field(min_length=3, max_length=3)
    confidence: float = Field(ge=0, le=1)
    assumptions: list[str] = Field(default_factory=list)


class PricingPipelineResult(BaseModel):
    """Complete output of one pricing pipeline run."""

    run_id: str
    source_file: str
    material_count: int
    suggestions: list[PriceSuggestion3]
    unresolved: list[MaterialRequirement] = Field(default_factory=list)
    timing: dict[str, float] = Field(default_factory=dict)
