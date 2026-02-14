# LLM Agent Pipeline Design

## Summary

Replace the deterministic price averaging in `price_agent.py` with a 3-stage PydanticAI agent pipeline. Each agent has 2-3 focused tools, keeping the decision space small enough for the local Ministral-3B model. The pipeline streams SSE events to the existing React frontend.

## Core Concept

Standard unit types are the normalization layer. Instead of format-specific parsers, we define a taxonomy of standard construction BoQ unit types (e.g., "Hidroizolacija ravnog krova"). Every uploaded Excel gets mapped into these standard types via LLM classification. Historic data is indexed by taxonomy_id, enabling cross-format comparison.

## Architecture

```
POST /api/agent/suggest  (existing endpoint)

for each LogicalUnit from parsed Excel:

  ┌──────────────────────┐
  │ Agent 1: Classifier  │
  │ Input:  raw rows     │──→ SSE: classification event
  │ Output: ClassResult  │     { taxonomy_id, confidence, deviations[] }
  │ Tools:               │
  │  - match_taxonomy()  │
  │  - check_schema()    │
  └──────────┬───────────┘
             ↓
  ┌──────────────────────┐
  │ Agent 2: Comparator  │
  │ Input:  ClassResult  │──→ SSE: historic_match events
  │ Output: CompResult   │     { matches[], summary }
  │ Tools:               │
  │  - search_historic() │
  │  - fetch_similar()   │
  └──────────┬───────────┘
             ↓
  ┌──────────────────────┐
  │ Agent 3: Pricer      │
  │ Input:  CompResult   │──→ SSE: suggestion events
  │ Output: PriceResult  │     { line_prices[], reasoning }
  │ Tools:               │
  │  - diff_historic()   │
  │  - search_web()      │
  │  - summarize()       │
  └──────────────────────┘
```

## File Structure

New files in `backend/src/agent/`:

```
agent/
├── pipeline.py           # Orchestrator: runs 3 agents, yields SSE events
├── classifier_agent.py   # Agent 1 + its tools
├── comparator_agent.py   # Agent 2 + its tools
├── pricer_agent.py       # Agent 3 + its tools
├── schemas.py            # ClassResult, CompResult, PriceResult
└── tools/
    ├── taxonomy.py       # match_taxonomy(), check_schema()
    ├── historic.py       # search_historic(), fetch_similar()
    ├── pricing.py        # diff_historic()
    └── external.py       # search_web(), summarize()
```

Deleted: `agent/price_agent.py` (replaced by pipeline).

## Agent 1: Classifier

**Purpose**: Map raw Excel rows to a standard taxonomy type. Identify deviations.

**System prompt**:
```
Ti si klasifikator građevinskih stavki. Dobivat ćeš redove iz Excel troškovnika.
Koristi alate za provjeru protiv standardne taksonomije.
Vrati taxonomy_id i popis odstupanja od standarda.
```

**Structured output**:

```python
class ClassResult(BaseModel):
    taxonomy_id: str              # "hidroizolacija-ravnog-krova"
    taxonomy_label: str           # "Hidroizolacija ravnog krova"
    confidence: float             # 0.0 - 1.0
    deviations: list[Deviation]
    unmatched_rows: list[int]

class Deviation(BaseModel):
    field: str          # "thickness", "material", "sub_item"
    standard_value: str # "0.3cm"
    actual_value: str   # "0.4cm"
    description: str    # "Debljina veća od standardne"
```

**Tools**:

| Tool | Input | Output | Deterministic |
|------|-------|--------|---------------|
| `match_taxonomy(description: str)` | Unit title/description text | Top-3 taxonomy matches with FTS5 scores | Yes |
| `check_schema(taxonomy_id: str, rows: list[dict])` | Taxonomy ID + extracted row data | Diff of present vs expected sub-items and units | Yes |

**SSE events**: `classification_start`, `reasoning` (streamed), `classification`.

## Agent 2: Comparator

**Purpose**: Find historic units of the same taxonomy type. Surface similarities and differences.

**System prompt**:
```
Ti si uspoređivač građevinskih stavki. Dobivaš klasificiranu stavku s taxonomy_id.
Koristi alate za pretragu historijskih podataka i pronalaženje sličnih stavki.
Vrati popis podudaranja s razlikama.
```

**Structured output**:

```python
class CompResult(BaseModel):
    classification: ClassResult
    matches: list[HistoricComparison]
    summary: str

class HistoricComparison(BaseModel):
    historic_unit_id: int
    project_name: str
    similarity_score: float
    matching_sub_items: list[str]
    missing_sub_items: list[str]
    extra_sub_items: list[str]
    price_lines: list[HistoricPriceLine]

class HistoricPriceLine(BaseModel):
    description: str
    unit_of_measure: str
    quantity: float
    unit_price: float
```

**Tools**:

| Tool | Input | Output | Deterministic |
|------|-------|--------|---------------|
| `search_historic(taxonomy_id: str, keywords: str)` | Taxonomy ID + search terms | Up to 5 historic units with price lines, filtered by taxonomy_id + FTS5 | Yes |
| `fetch_similar(unit_id: int)` | Historic unit ID | Full unit detail with all sub-items, description, pricing | Yes |

**SSE events**: `comparison_start`, `historic_match` (one per match), `reasoning`, `comparison_complete`.

## Agent 3: Pricer

**Purpose**: Reason about pricing using diffs, web data, and summarization.

**System prompt**:
```
Ti si stručnjak za određivanje cijena građevinskih radova.
Dobivaš klasificiranu stavku i historijske usporedbe.
Analiziraj razlike između trenutne stavke i historijskih podataka.
Koristi alate za provjeru cijena i predloži realnu cijenu s obrazloženjem.
```

**Structured output**:

```python
class PriceResult(BaseModel):
    line_prices: list[LinePriceSuggestion]
    overall_reasoning: str

class LinePriceSuggestion(BaseModel):
    item_number: str
    suggested_price: float
    confidence: float
    price_range: PriceRange
    reasoning: str

class PriceRange(BaseModel):
    low: float
    high: float
    median: float
```

**Tools**:

| Tool | Input | Output | Deterministic |
|------|-------|--------|---------------|
| `diff_historic(current_lines: list, historic_lines: list)` | Current + historic sub-items | Matched pairs with price deltas, unmatched items | Yes |
| `search_web(query: str)` | Search query for material prices / cost indices | Search result snippets | No |
| `summarize(text: str)` | Long text to condense | Short summary | No (LLM call) |

**SSE events**: `pricing_start`, `reasoning` (streamed), `suggestion` (one per line), `complete`.

## DB Schema Changes

**New table** — `standard_units`:

```sql
CREATE TABLE standard_units (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    expected_sub_items TEXT NOT NULL,  -- JSON array
    expected_units TEXT NOT NULL,       -- JSON array
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE standard_units_fts USING fts5(
    label, description, expected_sub_items,
    content=standard_units, content_rowid=rowid
);
```

**Modified table** — `historic_units` gets a new column:

```sql
ALTER TABLE historic_units ADD COLUMN taxonomy_id TEXT REFERENCES standard_units(id);
CREATE INDEX idx_historic_units_taxonomy ON historic_units(taxonomy_id);
```

**New API endpoints**:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/taxonomy` | List all standard unit types |
| `POST` | `/api/taxonomy/seed` | Bulk import taxonomy from JSON |

## Integration Points

| File | Change |
|------|--------|
| `api/agent.py` | Swap `run_price_suggestion()` for `run_pipeline()` |
| `agent/price_agent.py` | Deleted |
| `api/upload.py` | No change |
| `api/historic.py` | Run classifier when importing to set `taxonomy_id` |
| `db/schema.py` | Add `standard_units` table + FTS5 + alter `historic_units` |
| `db/historic_repo.py` | Add `search_by_taxonomy()` query |
| `frontend/*` | No changes needed — existing event handlers work |

## Model Configuration

All 3 agents use the same local Ministral-3B via OpenAI-compatible API:

```python
provider = OpenAIProvider(base_url="http://localhost:8080/v1")
model = OpenAIChatModel(model_name="ministral", provider=provider)
```

## Taxonomy Seeding Process

1. User annotates standard units from sample files (photos of annotations)
2. Run classifier once over 30 Excel files to generate natural language descriptions
3. Seed `standard_units` table via `POST /api/taxonomy/seed`
4. Import historic data — classifier sets `taxonomy_id` on each `historic_unit`
5. Future uploads get classified against the established taxonomy
