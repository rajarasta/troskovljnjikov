# LLM Agent Pipeline + Streamlit UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace deterministic price averaging with a 3-stage PydanticAI agent pipeline (Classifier → Comparator → Pricer) and build a futuristic Streamlit UI with glassmorphism theming and full LLM observability.

**Architecture:** Three PydanticAI agents chained sequentially, each with 2-3 focused tools. Pipeline orchestrator yields SSE events with timestamps, agent badges, and confidence breakdowns. Streamlit frontend consumes events via `st.empty()` live updates. Backend stubs start with mock data, hot-swap to real FastAPI.

**Tech Stack:** PydanticAI, FastAPI, aiosqlite, SQLite FTS5, sse-starlette, httpx, Streamlit, pytest

**Worktree split:**
- **Backend (Tasks 1-13):** `.worktrees/boq-editor` branch `feature/boq-editor`
- **Streamlit UI (Tasks 14-21):** `.worktrees/boq-streamlit-ui` branch `feature/boq-streamlit-ui`

**Run commands from:** `backend/` for backend tasks, `boq-streamlit-ui` root for Streamlit tasks

**Model alignment:** Backend schemas adapt to match existing frontend field names (see Task 2).

---

## Task 1: Test Infrastructure

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Modify: `backend/pyproject.toml` (add pytest dependency)

**Step 1: Add pytest to dev dependencies**

In `backend/pyproject.toml`, add after the `[tool.uv]` section:

```toml
[dependency-groups]
dev = ["pytest>=8.0", "pytest-asyncio>=0.24"]
```

**Step 2: Install dependencies**

Run: `cd backend && uv sync`
Expected: Dependencies install including pytest and pytest-asyncio

**Step 3: Create test infrastructure**

Create `backend/tests/__init__.py` (empty file).

Create `backend/tests/conftest.py`:

```python
"""Shared test fixtures for the backend test suite."""

import asyncio
from pathlib import Path

import aiosqlite
import pytest

from src.db.schema import SCHEMA_SQL


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db(tmp_path: Path):
    """Create a fresh in-memory SQLite database with schema applied."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.executescript(SCHEMA_SQL)
    await conn.commit()
    yield conn
    await conn.close()
```

**Step 4: Verify pytest runs**

Run: `cd backend && uv run pytest tests/ -v --co`
Expected: "no tests ran" (collection only, no errors)

**Step 5: Commit**

```bash
git add backend/pyproject.toml backend/tests/
git commit -m "chore: add pytest infrastructure"
```

---

## Task 2: Pipeline Schemas

**Files:**
- Create: `backend/src/agent/schemas.py`
- Create: `backend/tests/test_schemas.py`

**Step 1: Write the failing test**

Create `backend/tests/test_schemas.py`:

```python
"""Tests for agent pipeline schemas.

Field names aligned with Streamlit frontend models in boq_app/models.py:
  ReasoningEntry.agent_name  (not .agent)
  HistoricComparison.match_id  (not .historic_unit_id)
  HistoricComparison.source_file  (not .source_filename)
  HistoricComparison.year  (not .project_year)
  HistoricComparison.match_confidence  (float, overall score)
  HistoricComparison.confidence_breakdown  (ConfidenceBreakdown object)
  HistoricComparison.matched_lines  (not .price_lines)
  PipelineStats.num_matches  (not .match_count)
"""

from src.agent.schemas import (
    ClassResult,
    CompResult,
    ConfidenceBreakdown,
    Deviation,
    HistoricComparison,
    HistoricPriceLine,
    LinePriceSuggestion,
    PriceRange,
    PriceResult,
    ReasoningEntry,
)


def test_class_result_minimal():
    result = ClassResult(
        taxonomy_id="hidroizolacija-ravnog-krova",
        taxonomy_label="Hidroizolacija ravnog krova",
        confidence=0.85,
    )
    assert result.taxonomy_id == "hidroizolacija-ravnog-krova"
    assert result.deviations == []
    assert result.unmatched_rows == []


def test_class_result_with_deviations():
    result = ClassResult(
        taxonomy_id="toplinska-izolacija",
        taxonomy_label="Toplinska izolacija",
        confidence=0.72,
        deviations=[
            Deviation(
                field="thickness",
                standard_value="0.3cm",
                actual_value="0.4cm",
                description="Debljina veća od standardne",
            )
        ],
        unmatched_rows=[5, 8],
    )
    assert len(result.deviations) == 1
    assert result.deviations[0].field == "thickness"
    assert result.unmatched_rows == [5, 8]


def test_confidence_breakdown():
    breakdown = ConfidenceBreakdown(
        text_similarity=0.85,
        unit_match=1.0,
        hierarchy_match=0.7,
        description_overlap=0.6,
    )
    assert breakdown.overall == 0.7875  # weighted average
    assert breakdown.text_similarity == 0.85


def test_historic_comparison_with_breakdown():
    comp = HistoricComparison(
        match_id=42,
        project_name="Kaufland Osijek",
        source_file="KAUFLAND OSIJEK - ugovorni troškovnik.xlsx",
        year=2025,
        match_confidence=0.8425,
        confidence_breakdown=ConfidenceBreakdown(
            text_similarity=0.88,
            unit_match=1.0,
            hierarchy_match=0.7,
            description_overlap=0.65,
        ),
        matching_sub_items=["beton C40/50"],
        missing_sub_items=[],
        extra_sub_items=["armatura"],
        qty_delta_pct=-8.0,
        matched_lines=[
            HistoricPriceLine(
                item_number="3.2.1.a.",
                description="Beton",
                unit_of_measure="m³",
                quantity=120.0,
                unit_price=95.0,
                total=11400.0,
            )
        ],
    )
    assert comp.year == 2025
    assert comp.qty_delta_pct == -8.0
    assert comp.confidence_breakdown.overall > 0.7
    assert comp.match_confidence == 0.8425


def test_comp_result():
    classification = ClassResult(
        taxonomy_id="betonski-radovi",
        taxonomy_label="Betonski radovi",
        confidence=0.9,
    )
    result = CompResult(
        classification=classification,
        matches=[
            HistoricComparison(
                match_id=42,
                project_name="Kaufland Osijek",
                source_file="k.xlsx",
                year=2025,
                match_confidence=0.84,
                confidence_breakdown=ConfidenceBreakdown(
                    text_similarity=0.88,
                    unit_match=1.0,
                    hierarchy_match=0.7,
                    description_overlap=0.65,
                ),
                matched_lines=[
                    HistoricPriceLine(
                        description="Beton",
                        unit_of_measure="m³",
                        quantity=120.0,
                        unit_price=95.0,
                    )
                ],
            )
        ],
        summary="1 slična stavka pronađena",
    )
    assert len(result.matches) == 1
    assert result.matches[0].project_name == "Kaufland Osijek"


def test_price_result():
    result = PriceResult(
        line_prices=[
            LinePriceSuggestion(
                item_number="3.1.1.1.a.",
                suggested_price=45.0,
                confidence=0.8,
                price_range=PriceRange(low=38.0, high=52.0, median=44.5),
                reasoning="Prosjek 4 historijske cijene",
            )
        ],
        overall_reasoning="Cijena u skladu s historijskim podacima",
    )
    assert result.line_prices[0].suggested_price == 45.0
    assert result.line_prices[0].price_range.median == 44.5


def test_reasoning_entry():
    entry = ReasoningEntry(
        agent_name="classifier",
        message="Pronađen tip: Hidroizolacija ravnog krova (confidence: 0.85)",
        entry_type="result",
    )
    assert entry.agent_name == "classifier"
    assert entry.entry_type == "result"
    assert entry.timestamp  # auto-generated
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.agent.schemas'`

**Step 3: Implement schemas**

Create `backend/src/agent/schemas.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_schemas.py -v`
Expected: 7 passed

**Step 5: Commit**

```bash
git add backend/src/agent/schemas.py backend/tests/test_schemas.py
git commit -m "feat: add pipeline schemas with ConfidenceBreakdown and ReasoningEntry"
```

---

## Task 3: DB Schema — Standard Units Table

**Files:**
- Modify: `backend/src/db/schema.py`
- Create: `backend/tests/test_db_schema.py`

**Step 1: Write the failing test**

Create `backend/tests/test_db_schema.py`:

```python
"""Tests for database schema including standard_units."""

import pytest
import pytest_asyncio
import aiosqlite

from src.db.schema import SCHEMA_SQL


@pytest_asyncio.fixture
async def db():
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.executescript(SCHEMA_SQL)
    await conn.commit()
    yield conn
    await conn.close()


@pytest.mark.asyncio
async def test_standard_units_table_exists(db):
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='standard_units'"
    )
    row = await cursor.fetchone()
    assert row is not None


@pytest.mark.asyncio
async def test_standard_units_fts_exists(db):
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='standard_units_fts'"
    )
    row = await cursor.fetchone()
    assert row is not None


@pytest.mark.asyncio
async def test_insert_and_search_standard_unit(db):
    await db.execute(
        "INSERT INTO standard_units (id, label, description, category, expected_sub_items, expected_units) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            "hidroizolacija-ravnog-krova",
            "Hidroizolacija ravnog krova",
            "Izvedba hidroizolacije ravnog krova s bitumenskim trakama",
            "Krovopokrivački radovi",
            '["parna brana", "toplinska izolacija", "hidroizolacijska membrana"]',
            '["m²", "m"]',
        ),
    )
    await db.commit()

    cursor = await db.execute(
        "SELECT * FROM standard_units_fts WHERE standard_units_fts MATCH ?",
        ("hidroizolacija",),
    )
    rows = await cursor.fetchall()
    assert len(rows) >= 1


@pytest.mark.asyncio
async def test_historic_units_has_taxonomy_id(db):
    cursor = await db.execute(
        "INSERT INTO projects (name, source_filename, format, import_date) VALUES (?, ?, ?, ?)",
        ("Test Project", "test.xlsx", "eurospin", "2026-01-01"),
    )
    project_id = cursor.lastrowid

    await db.execute(
        "INSERT INTO standard_units (id, label, description, category, expected_sub_items, expected_units) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("test-type", "Test", "Test desc", "Test cat", "[]", "[]"),
    )

    await db.execute(
        "INSERT INTO historic_units (project_id, item_number, title, description, taxonomy_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (project_id, "3.1.", "Test Unit", "A test", "test-type"),
    )
    await db.commit()

    cursor = await db.execute("SELECT taxonomy_id FROM historic_units WHERE item_number = '3.1.'")
    row = await cursor.fetchone()
    assert row["taxonomy_id"] == "test-type"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_db_schema.py -v`
Expected: FAIL — `standard_units` table doesn't exist

**Step 3: Update schema**

Replace `backend/src/db/schema.py` entirely:

```python
"""SQLite schema for historic BoQ storage."""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    client TEXT DEFAULT '',
    location TEXT DEFAULT '',
    import_date TEXT NOT NULL,
    source_filename TEXT NOT NULL,
    format TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS standard_units (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    expected_sub_items TEXT NOT NULL DEFAULT '[]',
    expected_units TEXT NOT NULL DEFAULT '[]',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS standard_units_fts USING fts5(
    label,
    description,
    expected_sub_items,
    content=standard_units,
    content_rowid=rowid,
    tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS standard_units_ai AFTER INSERT ON standard_units BEGIN
    INSERT INTO standard_units_fts(rowid, label, description, expected_sub_items)
    VALUES (new.rowid, new.label, new.description, new.expected_sub_items);
END;

CREATE TRIGGER IF NOT EXISTS standard_units_ad AFTER DELETE ON standard_units BEGIN
    INSERT INTO standard_units_fts(standard_units_fts, rowid, label, description, expected_sub_items)
    VALUES ('delete', old.rowid, old.label, old.description, old.expected_sub_items);
END;

CREATE TABLE IF NOT EXISTS historic_units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    item_number TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    parent_section TEXT DEFAULT '',
    parent_chapter TEXT DEFAULT '',
    taxonomy_id TEXT REFERENCES standard_units(id)
);

CREATE TABLE IF NOT EXISTS historic_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id INTEGER NOT NULL REFERENCES historic_units(id),
    item_number TEXT NOT NULL,
    description TEXT DEFAULT '',
    unit_of_measure TEXT NOT NULL DEFAULT '',
    quantity REAL NOT NULL DEFAULT 0,
    unit_price REAL,
    total REAL
);

CREATE VIRTUAL TABLE IF NOT EXISTS historic_units_fts USING fts5(
    title,
    description,
    content=historic_units,
    content_rowid=id,
    tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS historic_units_ai AFTER INSERT ON historic_units BEGIN
    INSERT INTO historic_units_fts(rowid, title, description)
    VALUES (new.id, new.title, new.description);
END;

CREATE TRIGGER IF NOT EXISTS historic_units_ad AFTER DELETE ON historic_units BEGIN
    INSERT INTO historic_units_fts(historic_units_fts, rowid, title, description)
    VALUES ('delete', old.id, old.title, old.description);
END;

CREATE INDEX IF NOT EXISTS idx_historic_lines_unit
    ON historic_lines(unit_of_measure);

CREATE INDEX IF NOT EXISTS idx_historic_units_project
    ON historic_units(project_id);

CREATE INDEX IF NOT EXISTS idx_historic_units_taxonomy
    ON historic_units(taxonomy_id);
"""
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_db_schema.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add backend/src/db/schema.py backend/tests/test_db_schema.py
git commit -m "feat: add standard_units table and taxonomy_id to historic_units"
```

---

## Tasks 4-10: Backend Tools & Agents

Tasks 4-10 are unchanged from the original plan. See original plan sections for:

- **Task 4**: Taxonomy Tools (`match_taxonomy`, `check_schema`)
- **Task 5**: Historic Tools (`search_historic_by_taxonomy`, `fetch_similar`)
- **Task 6**: Pricing Tools (`diff_historic`)
- **Task 7**: External Tools (`search_web`, `summarize`)
- **Task 8**: Classifier Agent
- **Task 9**: Comparator Agent
- **Task 10**: Pricer Agent

---

## Task 11: Pipeline Orchestrator

**Files:**
- Create: `backend/src/agent/pipeline.py`
- Create: `backend/tests/test_pipeline.py`

**Step 1: Write the failing test**

Create `backend/tests/test_pipeline.py`:

```python
"""Tests for the pipeline orchestrator.

Tests the event sequence without a running LLM by mocking agent.run().
"""

from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.agent.pipeline import run_pipeline, PIPELINE_STAGES
from src.agent.schemas import (
    ClassResult,
    CompResult,
    ConfidenceBreakdown,
    HistoricComparison,
    HistoricPriceLine,
    LinePriceSuggestion,
    PriceRange,
    PriceResult,
)
from src.models.boq import LogicalUnit, PricedLine


@pytest.fixture
def sample_unit():
    return LogicalUnit(
        item_number="3.1.1.",
        title="Hidroizolacija ravnog krova",
        description="Izvedba hidroizolacije",
        priced_lines=[
            PricedLine(item_number="3.1.1.a.", description="Parna brana", unit="m²", quantity=200.0),
        ],
    )


def test_pipeline_stages_defined():
    assert len(PIPELINE_STAGES) == 6
    assert PIPELINE_STAGES[0] == "upload"
    assert PIPELINE_STAGES[-1] == "review"


@pytest.mark.asyncio
async def test_pipeline_yields_correct_event_sequence(sample_unit):
    mock_class_result = ClassResult(
        taxonomy_id="hidro", taxonomy_label="Hidro", confidence=0.9
    )
    mock_comp_result = CompResult(
        classification=mock_class_result,
        matches=[
            HistoricComparison(
                match_id=1,
                project_name="Test Project",
                source_file="test.xlsx",
                year=2025,
                match_confidence=0.84,
                confidence_breakdown=ConfidenceBreakdown(
                    text_similarity=0.88,
                    unit_match=1.0,
                    hierarchy_match=0.7,
                    description_overlap=0.65,
                ),
                matched_lines=[HistoricPriceLine(description="Parna brana", unit_of_measure="m²", quantity=250, unit_price=12.5)],
            )
        ],
        summary="Found 1 match",
    )
    mock_price_result = PriceResult(
        line_prices=[
            LinePriceSuggestion(
                item_number="3.1.1.a.",
                suggested_price=12.5,
                confidence=0.8,
                price_range=PriceRange(low=10.0, high=15.0, median=12.5),
                reasoning="Based on 1 match",
            )
        ],
        overall_reasoning="Price OK",
    )

    with patch("src.agent.pipeline.create_classifier_agent") as mock_cls, \
         patch("src.agent.pipeline.create_comparator_agent") as mock_cmp, \
         patch("src.agent.pipeline.create_pricer_agent") as mock_prc, \
         patch("src.agent.pipeline.get_db") as mock_get_db:

        mock_get_db.return_value = AsyncMock()

        for mock_factory, mock_result in [
            (mock_cls, mock_class_result),
            (mock_cmp, mock_comp_result),
            (mock_prc, mock_price_result),
        ]:
            mock_agent = MagicMock()
            mock_run_result = MagicMock()
            mock_run_result.output = mock_result
            mock_agent.run = AsyncMock(return_value=mock_run_result)
            mock_factory.return_value = mock_agent

        events = []
        async for event_type, data in run_pipeline(sample_unit):
            events.append((event_type, data))

        event_types = [e[0] for e in events]

        # Pipeline stage events
        assert "pipeline_stage" in event_types
        # Agent events
        assert "reasoning" in event_types
        assert "classification" in event_types
        assert "historic_match" in event_types
        assert "confidence_breakdown" in event_types
        assert "suggestion" in event_types
        assert "stats" in event_types
        assert "complete" in event_types

        # Correct order
        assert event_types.index("classification") < event_types.index("historic_match")
        assert event_types.index("historic_match") < event_types.index("suggestion")
        assert event_types.index("suggestion") < event_types.index("complete")

        # Reasoning entries have agent_name badge (aligned with frontend)
        reasoning_events = [e for e in events if e[0] == "reasoning"]
        agents_seen = {e[1]["agent_name"] for e in reasoning_events}
        assert "classifier" in agents_seen
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement pipeline orchestrator**

Create `backend/src/agent/pipeline.py`:

```python
"""Pipeline orchestrator: runs Classifier → Comparator → Pricer sequentially.

Emits rich SSE events for the Streamlit UI:
- pipeline_stage: current stage for pipeline bar
- reasoning: log entries with agent badge + timestamp
- classification, historic_match, confidence_breakdown, suggestion: data events
- stats: aggregate stats for footer
- complete: pipeline finished
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from ..db.database import get_db
from ..models.boq import LogicalUnit
from .classifier_agent import ClassifierDeps, create_classifier_agent
from .comparator_agent import ComparatorDeps, create_comparator_agent
from .pricer_agent import PricerDeps, create_pricer_agent
from .schemas import PipelineStats, ReasoningEntry

# Pipeline bar stages (matches Streamlit header component)
PIPELINE_STAGES = ["upload", "parse", "index", "match", "suggest", "review"]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reasoning(agent_name: str, message: str, entry_type: str = "info") -> tuple[str, dict[str, Any]]:
    entry = ReasoningEntry(agent_name=agent_name, message=message, entry_type=entry_type)
    return ("reasoning", entry.model_dump())


def _stage(stage: str) -> tuple[str, dict[str, Any]]:
    return ("pipeline_stage", {"stage": stage, "timestamp": _ts()})


def _format_unit_for_classifier(unit: LogicalUnit) -> str:
    lines = [f"Stavka: {unit.item_number} — {unit.title}"]
    if unit.description:
        lines.append(f"Opis: {unit.description}")
    if unit.priced_lines:
        lines.append("Podstavke:")
        for pl in unit.priced_lines:
            lines.append(f"  {pl.item_number}: {pl.description} [{pl.unit}] količina={pl.quantity}")
    return "\n".join(lines)


def _format_for_comparator(classification_json: str) -> str:
    return f"Klasificirana stavka:\n{classification_json}\n\nPronađi historijske stavke istog tipa i usporedi ih."


def _format_for_pricer(unit: LogicalUnit, comparison_json: str) -> str:
    lines = [f"Trenutna stavka: {unit.item_number} — {unit.title}"]
    lines.append("Trenutne podstavke (JSON):")
    current_lines = [
        {"item_number": pl.item_number, "description": pl.description, "unit": pl.unit, "quantity": pl.quantity}
        for pl in unit.priced_lines
    ]
    lines.append(json.dumps(current_lines, ensure_ascii=False))
    lines.append(f"\nHistorijske usporedbe:\n{comparison_json}")
    lines.append("\nPredloži cijenu za svaku podstavku.")
    return "\n".join(lines)


async def run_pipeline(unit: LogicalUnit) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """Run the 3-stage agent pipeline for a logical unit.

    Yields (event_type, data) tuples for SSE streaming.
    Events include timestamps and agent badges for the Streamlit reasoning panel.
    """
    db = await get_db()

    # --- Stage 1: Classifier (pipeline: index) ---
    yield _stage("index")
    yield _reasoning("classifier", f"Klasificiram stavku: {unit.title}")

    classifier = create_classifier_agent()
    class_result = await classifier.run(
        _format_unit_for_classifier(unit),
        deps=ClassifierDeps(db=db),
    )
    classification = class_result.output

    yield ("classification", classification.model_dump())
    yield _reasoning("classifier",
        f"Pronađen tip: {classification.taxonomy_label} (confidence: {classification.confidence})")

    if classification.deviations:
        devs = ", ".join(d.description for d in classification.deviations)
        yield _reasoning("classifier", f"Odstupanja od standarda: {devs}")

    # --- Stage 2: Comparator (pipeline: match) ---
    yield _stage("match")
    yield _reasoning("comparator", f"Tražim historijske stavke za tip: {classification.taxonomy_id}")

    comparator = create_comparator_agent()
    classification_json = classification.model_dump_json()
    comp_result = await comparator.run(
        _format_for_comparator(classification_json),
        deps=ComparatorDeps(db=db, classification=classification),
    )
    comparison = comp_result.output

    yield _reasoning("comparator",
        f"Pronađeno {len(comparison.matches)} historijskih podudaranja")

    for match in comparison.matches:
        yield ("historic_match", match.model_dump())
        yield ("confidence_breakdown", {
            "match_id": match.match_id,
            "project_name": match.project_name,
            "breakdown": match.confidence_breakdown.model_dump(),
        })
        yield _reasoning("comparator",
            f"  {match.project_name} ({match.year}): "
            f"sličnost {match.confidence_breakdown.overall:.0%}, "
            f"qty Δ {match.qty_delta_pct:+.1f}%")

    # --- Stage 3: Pricer (pipeline: suggest) ---
    yield _stage("suggest")
    yield _reasoning("pricer", "Analiziram cijene na temelju historijskih podataka")

    pricer = create_pricer_agent()
    comparison_json = comparison.model_dump_json()
    price_result = await pricer.run(
        _format_for_pricer(unit, comparison_json),
        deps=PricerDeps(comparison=comparison),
    )

    all_prices = []
    for suggestion in price_result.output.line_prices:
        yield ("suggestion", suggestion.model_dump())
        all_prices.append(suggestion.suggested_price)
        yield _reasoning("pricer",
            f"  {suggestion.item_number}: {suggestion.suggested_price:.2f} EUR "
            f"(confidence: {suggestion.confidence:.0%})")

    if price_result.output.overall_reasoning:
        yield _reasoning("pricer", price_result.output.overall_reasoning)

    # --- Stats for footer ---
    stats = PipelineStats(
        avg_price=sum(all_prices) / len(all_prices) if all_prices else 0,
        min_price=min(all_prices) if all_prices else 0,
        max_price=max(all_prices) if all_prices else 0,
        num_matches=len(comparison.matches),
        total_suggestions=len(all_prices),
    )
    yield ("stats", stats.model_dump())

    # --- Complete (pipeline: review) ---
    yield _stage("review")
    yield ("complete", {})
```

**Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_pipeline.py -v`
Expected: 2 passed

**Step 5: Commit**

```bash
git add backend/src/agent/pipeline.py backend/tests/test_pipeline.py
git commit -m "feat: add pipeline orchestrator with rich SSE events for Streamlit UI"
```

---

## Task 12: API Integration

Unchanged from original plan. Swap `run_price_suggestion()` for `run_pipeline()` in `api/agent.py`, add `api/taxonomy.py`, update `api/router.py`, delete `price_agent.py`.

---

## Task 13: Historic Import with Classification

Unchanged from original plan. Add `update_unit_taxonomy()` to `historic_repo.py`.

---

## Task 14: Streamlit Skeleton & Theming — DONE (Batch 1)

**Status:** Complete in `.worktrees/boq-streamlit-ui` on branch `feature/boq-streamlit-ui`.

**What was built (differs from original plan):**

- Layout: **2-column** `[2, 5]` (not 3-column) — left (navigator + carousel), right (unified panel)
- Default theme: **Light frosted glass** — `rgba(255,255,255,0.55)` on `#eef2f8` (not dark navy)
- CSS: **~660 lines** in `styles.py` (7 CSS module functions, much richer than planned)
- Entry point: `boq_ui.py` → imports `boq_app.app` (fixes relative import issue)
- 3 themes: minority_report (light, default), blueprint (dark blue), construction_site (warm amber)

**Files:** `boq_app/app.py`, `themes.py`, `styles.py`, `.streamlit/config.toml`, `boq_ui.py`

---

## Task 15: Streamlit Data Models & Mock Data — DONE (Batch 1)

**Status:** Complete in `.worktrees/boq-streamlit-ui`.

**What was built (differs from original plan):**

- Models include extra enums: `MatchStatus`, `PipelineStepStatus`
- Extra models: `PriceStatsUI`, `PipelineStepUI` (not in plan)
- `ConfidenceBreakdownUI` does **NOT** have `overall` computed field (needs adding)
- Field names use frontend conventions: `agent_name`, `match_id`, `source_file`, `year`, etc.
- Mock data: **7 items** (chapters + work items), **5 matches** (richer than planned 3/2)
- State manager has richer helpers: `get_selected_item()`, `update_pipeline_step()`, etc.

**Files:** `boq_app/models.py`, `mock_data.py`, `state.py`

**Action needed in Batch 2:** Add `overall` computed field to `ConfidenceBreakdownUI`.

---

## Task 16: Streamlit Components — DONE (Batch 1)

**Status:** Complete in `.worktrees/boq-streamlit-ui`.

**What was built (differs from original plan):**

Actual component architecture consolidates into **4 active components** (not 7 flat):

| Active Component | What it does |
|-----------------|--------------|
| `header.py` | Title + pipeline dot bar + theme selector |
| `navigator.py` | Hierarchical tree via `st.radio()` + CSS indent |
| `match_carousel.py` | Stacked cards with depth layering, DETAILS/APPLY buttons |
| `unit_panel.py` | **Unified** 5-section panel: header, priced lines, stats, confidence, reasoning |

Legacy files exist but are **unused** (delete in Batch 2 polish):
`item_detail.py`, `match_cards.py`, `reasoning_panel.py`, `confidence_panel.py`, `stats_footer.py`

**Files:** `boq_app/components/header.py`, `navigator.py`, `match_carousel.py`, `unit_panel.py`

---

## Task 17: Streamlit Interactivity

**Worktree:** `.worktrees/boq-streamlit-ui`

**Files:**
- Modify: `boq_app/app.py`
- Modify: `boq_app/models.py` (add `overall` computed field to `ConfidenceBreakdownUI`)
- Modify: `boq_app/components/navigator.py`
- Modify: `boq_app/components/match_carousel.py`
- Modify: `boq_app/components/unit_panel.py`

**Step 1: Add `overall` computed field to ConfidenceBreakdownUI**

In `boq_app/models.py`, add `computed_field` import and the `overall` property to `ConfidenceBreakdownUI`:

```python
from pydantic import BaseModel, Field, computed_field

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
```

**Step 2: Verify navigator selection works**

Navigator in `navigator.py` uses `st.radio()` to update `selected_item_id`. Click items and verify `unit_panel.py` updates. If it doesn't, check `on_change` callback wiring.

**Step 3: Verify APPLY button works**

In `match_carousel.py`, `_apply_match()` copies historic prices to priced lines. Click APPLY on a match card, verify the priced lines table in `unit_panel.py` shows updated prices.

**Step 4: Wire file upload handler**

Add `st.file_uploader()` in `header.py`. On upload:
- Read bytes from uploaded file
- Call `parse_uploaded_file(content, filename)` (mock initially, see Task 18)
- Populate `app_state["parsed_file"]` with result
- Advance pipeline stage from "upload" to "parse"

**Step 5: Verify DETAILS expansion toggle**

In `match_carousel.py`, DETAILS button expands to show full historic priced lines table. Uses session state to track expanded cards.

**Step 6: Add st.fragment() for independent panel reruns**

Wrap navigator and unit_panel render functions with `@st.fragment` decorator to avoid full-page reruns when clicking within one panel.

**Step 7: Run and verify**

Run: `cd .worktrees/boq-streamlit-ui && uv run streamlit run boq_ui.py`
Expected: Click navigator → detail updates. Click APPLY → prices copy. Upload → data loads.

**Step 8: Commit**

```bash
git add boq_app/
git commit -m "feat: wire interactivity (navigator, APPLY, upload, expand, st.fragment)"
```

---

## Task 18: Backend Integration

**Worktree:** `.worktrees/boq-streamlit-ui`

**Files:**
- Create: `boq_app/backend.py`
- Modify: `boq_app/app.py`

**Step 1: Create backend integration module**

Create `boq_app/backend.py`:

```python
"""Backend integration: mock data stubs → real FastAPI.

Phase 1 (USE_REAL_BACKEND=false): Returns mock data + local xlsx parsing via analyze_xlsx.py.
Phase 2 (USE_REAL_BACKEND=true): Calls FastAPI endpoints via httpx.

Field names match frontend models (agent_name, match_id, source_file, year, etc.)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import AsyncGenerator

import httpx

from models import ParsedFileUI, BoQItemUI, PricedLineUI, HistoricMatchUI, ReasoningEntryUI
from mock_data import generate_mock_matches, generate_mock_reasoning_log

USE_REAL_BACKEND = os.getenv("BOQ_REAL_BACKEND", "false").lower() == "true"
BACKEND_URL = os.getenv("BOQ_BACKEND_URL", "http://localhost:8081/api")

# Path to analyze_xlsx.py at repo root (for local xlsx parsing)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def parse_uploaded_file_sync(content: bytes, filename: str) -> ParsedFileUI:
    """Parse an uploaded Excel file using analyze_xlsx.py.

    Uses the repo-root analyze_xlsx.py for real xlsx parsing,
    converting its output to frontend models.
    """
    try:
        from analyze_xlsx import analyze_file
        from io import BytesIO

        result = analyze_file(BytesIO(content), filename)
        items = []
        for i, unit in enumerate(result.get("units", [])):
            priced_lines = [
                PricedLineUI(
                    item_number=pl.get("item_number", ""),
                    description=pl.get("description", ""),
                    unit=pl.get("unit", ""),
                    quantity=pl.get("quantity", 0.0),
                    unit_price=pl.get("unit_price"),
                    total=pl.get("total"),
                )
                for pl in unit.get("priced_lines", [])
            ]
            items.append(BoQItemUI(
                id=f"unit-{i}",
                item_number=unit.get("item_number", ""),
                title=unit.get("title", ""),
                description=unit.get("description", ""),
                level=unit.get("level", 3),
                priced_lines=priced_lines,
            ))
        return ParsedFileUI(
            filename=filename,
            format_detected=result.get("format", "unknown"),
            sheet_name=result.get("sheet_name", ""),
            chapter_title=result.get("chapter_title", ""),
            items=items,
        )
    except Exception as e:
        # Fallback: return empty file with error info
        return ParsedFileUI(
            filename=filename,
            format_detected="error",
            sheet_name="",
            chapter_title=f"Parse error: {e}",
            items=[],
        )


async def parse_uploaded_file(content: bytes, filename: str) -> ParsedFileUI:
    """Parse an uploaded Excel file."""
    if not USE_REAL_BACKEND:
        return parse_uploaded_file_sync(content, filename)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BACKEND_URL}/upload",
            files={"file": (filename, content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        resp.raise_for_status()
        return ParsedFileUI(**resp.json())


async def search_historic_matches(unit_id: str) -> list[HistoricMatchUI]:
    """Search for historic matches for a given unit."""
    if not USE_REAL_BACKEND:
        return generate_mock_matches()

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BACKEND_URL}/historic/search", params={"q": unit_id})
        resp.raise_for_status()
        return [HistoricMatchUI(**m) for m in resp.json()]


async def run_suggestions(unit_id: str) -> AsyncGenerator[tuple[str, dict], None]:
    """Stream SSE events from the agent pipeline.

    Yields (event_type, data) tuples matching the backend pipeline format.
    Field names use frontend conventions (agent_name, match_id, etc.)
    """
    if not USE_REAL_BACKEND:
        for entry in generate_mock_reasoning_log():
            yield ("reasoning", entry.model_dump())
            await asyncio.sleep(0.1)
        yield ("complete", {})
        return

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{BACKEND_URL}/agent/suggest",
            json={"unit_id": unit_id},
        ) as resp:
            event_type = ""
            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                elif line.startswith("data:"):
                    data = json.loads(line[5:].strip())
                    yield (event_type, data)
```

**Step 2: Wire into app.py**

Update `boq_app/app.py` to call `backend.py` functions:
- File upload → `asyncio.run(parse_uploaded_file(content, filename))`
- Unit selection → `asyncio.run(search_historic_matches(unit_id))`
- "Run Analysis" button → stream `run_suggestions()` via `st.empty()` live updates

**Step 3: Test with real xlsx files**

Run: `cd .worktrees/boq-streamlit-ui && uv run streamlit run boq_ui.py`
Upload files from `vanjski-podaci/primjeri-excel-ponuda/` (30 xlsx files).
Expected: Files parse, navigator populates, Croatian characters display correctly.

**Step 4: Test with real backend (when available)**

Run: `BOQ_REAL_BACKEND=true uv run streamlit run boq_ui.py`
Prerequisites: FastAPI backend at :8081 (from `.worktrees/boq-editor`), llama-server at :8080.

**Step 5: Commit**

```bash
git add boq_app/backend.py boq_app/app.py
git commit -m "feat: add backend integration with local xlsx parsing and mock/real toggle"
```

---

## Task 19: Polish

**Worktree:** `.worktrees/boq-streamlit-ui`

**Files:**
- Modify: `boq_app/styles.py`
- Delete: `boq_app/components/item_detail.py` (unused legacy)
- Delete: `boq_app/components/match_cards.py` (unused legacy)
- Delete: `boq_app/components/reasoning_panel.py` (unused legacy)
- Delete: `boq_app/components/confidence_panel.py` (unused legacy)
- Delete: `boq_app/components/stats_footer.py` (unused legacy)

**Step 1: Delete unused legacy component files**

Remove: `item_detail.py`, `match_cards.py`, `reasoning_panel.py`, `confidence_panel.py`, `stats_footer.py`
Verify `components/__init__.py` doesn't import them.

**Step 2: Verify all 3 themes work**

Switch themes via header selectbox. Verify:
- Minority Report: light frosted glass, blue accents on `#eef2f8`
- Blueprint: dark blue with white/cyan accents
- Construction Site: warm beige/orange

**Step 3: Test Croatian character encoding**

Upload xlsx files and verify: č, ć, š, ž, đ display correctly in navigator, detail panel, and match cards.

**Step 4: backdrop-filter fallback**

Add fallback in `styles.py` for browsers without `backdrop-filter` support:

```css
@supports not (backdrop-filter: blur(20px)) {
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255, 255, 255, 0.85) !important;
    }
}
```

**Step 5: Commit**

```bash
git add -A boq_app/
git commit -m "polish: remove legacy components, verify themes, add blur fallback"
```

---

## Task 20: Run All Backend Tests

**Worktree:** `.worktrees/boq-editor`

**Step 1: Run full test suite**

Run: `cd .worktrees/boq-editor/backend && uv run pytest tests/ -v`
Expected: All tests pass (~24 tests)

**Step 2: Fix any failures and commit**

---

## Task 21: End-to-End Smoke Test

**Prerequisites:** llama-server running at `http://localhost:8080/v1`

**Step 1: Start backend** (in `.worktrees/boq-editor`)

Run: `cd .worktrees/boq-editor/backend && uv run uvicorn src.main:app --host 127.0.0.1 --port 8081 --reload`

**Step 2: Seed taxonomy**

```bash
curl -X POST http://localhost:8081/api/taxonomy/seed \
  -H "Content-Type: application/json" \
  -d '{
    "units": [
      {
        "id": "hidroizolacija-ravnog-krova",
        "label": "Hidroizolacija ravnog krova",
        "description": "Izvedba hidroizolacije ravnog krova s bitumenskim trakama uključujući parnu branu i toplinsku izolaciju",
        "category": "Krovopokrivački radovi",
        "expected_sub_items": ["parna brana", "toplinska izolacija", "hidroizolacijska membrana"],
        "expected_units": ["m²", "m"]
      }
    ]
  }'
```

**Step 3: Start Streamlit with real backend** (in `.worktrees/boq-streamlit-ui`)

Run: `cd .worktrees/boq-streamlit-ui && BOQ_REAL_BACKEND=true uv run streamlit run boq_ui.py`

**Step 4: Verify end-to-end flow**

1. Upload an xlsx from `vanjski-podaci/`
2. Navigator populates
3. Click a unit → unified panel shows item detail, priced lines, stats
4. Click "Run Analysis" → reasoning section in unit panel streams live
5. Match carousel shows cards with confidence bars and QTY deltas
6. APPLY button copies prices to priced lines table
7. Stats section shows AVG/MIN/MAX/MATCHES
8. Theme switcher changes palette across all panels
