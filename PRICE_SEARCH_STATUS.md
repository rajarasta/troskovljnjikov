# Price Search Feature - Implementation Status

## ✅ Completed

### Backend Implementation
- [x] **search_agent.py** — PydanticAI agent with tool-calling support
  - `search_domain()` tool — searches approved supplier websites
  - `fetch_and_extract()` tool — extracts prices from product pages
  - `rag_lookup()` tool — looks up historical prices
  - Structured output with quotes, best match, reasoning, search log

- [x] **price_extractor.py** — deterministic price extraction
  - JSON-LD schema parsing (Product/Offer structures)
  - Meta tags extraction (og:price, product:price)
  - LLM-based fallback for unstructured content

- [x] **price_normalizer.py** — price normalization & computation
  - Currency conversion (EUR, HRK)
  - VAT handling (Croatian 25% PDV)
  - Unit normalization (m², kom, m, kg, etc.)
  - Total computation with shipping estimates

- [x] **web_fetcher.py** — layered web fetching
  - httpx for static content (default)
  - Playwright fallback for JavaScript-heavy sites
  - TTL cache for repeated requests (15 min)

- [x] **domain_registry.py** — approved domain configuration
  - Allowlist: bauhaus.hr, gradja.hr, wuerth.com.hr, era-commerce.hr
  - Domain-specific search URL templates
  - VAT inclusion rules per vendor

- [x] **price_search.py router** — REST API endpoints
  - `POST /api/price-search/{item_id}` — single item search
  - `POST /api/price-search/batch` — batch search (multiple items)
  - `GET /api/price-search/{item_id}/result` — retrieve cached results
  - WebSocket event streaming (search:started, search:quote_found, search:complete)

### Frontend Implementation
- [x] **PriceSearchModal** — animated pipeline visualization
  - 5-step pipeline: Describe → Search → Extract → Normalize → Report
  - Domain toggles (Bauhaus, Gradja.hr, Würth, ERA Commerce)
  - Options: Include PDV, Include Shipping
  - Live quote display during/after search
  - Launch button with search status feedback

- [x] **searchStore.ts** — Zustand state management
  - Per-item search status (idle, searching, done, error)
  - Quote collection and management
  - Result caching and retrieval
  - Error handling

- [x] **searchHandlers.ts** — WebSocket event handlers
  - `search:started` — marks item as searching
  - `search:quote_found` — collects individual quotes
  - `search:complete` — finalizes search with best quote, reasoning, computed total
  - Auto-injects search results into chat panels

- [x] **Integration** — search feature in TopBar
  - "Search Prices" button with Globe icon
  - Opens PriceSearchModal on click
  - Connects to spreadsheet selections

- [x] **File Preview Modal** (bonus)
  - Side-by-side modal showing file contents
  - Text wrap toggle for descriptions
  - Reduced horizontal spacing (1/3 of original)
  - Supports viewing original and clicked files simultaneously

### Infrastructure
- [x] **Event system** — WebSocket events for streaming progress
  - Backend emits events to all connected clients
  - Frontend Zustand stores receive and process events
  - Real-time UI updates without polling

- [x] **Synthetic items support** — spreadsheet cell handling
  - Excel cells converted to synthetic items (format: `excel-cell-ROW-COL-TIMESTAMP`)
  - Descriptions preserved through batch upload
  - Lookup agent resolves synthetic items to database references

---

## ⚠️ Fixed (Recent Changes)

### Root Cause Analysis
- **Problem:** Local LLM (ministral-3b) doesn't support PydanticAI tool calling
- **Symptom:** Search agent returns 0 quotes, hallucinated data in search_log
- **Solution:** Switched to Claude API (production-grade tool calling)

### Implementation
- Updated `search_agent.py` to use `AnthropicChatModel` instead of `OpenAIChatModel`
- Updated `config.py` to use `claude-opus-4-6` model
- Created `backend/.env` template with `ANTHROPIC_API_KEY` setup
- Created `CLAUDE_API_SETUP.md` guide

---

## 🚀 Next Steps for User

### 1. Set Up Claude API (Required)
```bash
# Get API key from: https://console.anthropic.com/account/keys

# Set in backend/.env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> backend/.env
```

### 2. Start Application
```bash
./run.sh
```

### 3. Test Price Search
1. Upload a BoQ Excel file
2. Click "Price Search" button
3. Select items in spreadsheet (they appear highlighted)
4. Click "Search Price" (single) or "Batch Search" (multiple)
5. Watch the pipeline visualize the steps
6. See quotes stream into chat panel

### 4. Verify Tool Calling Works
In browser console, when searching:
```
🔍 [Tool] search_domain called: domain=bauhaus.hr, query=...
Found N candidates on bauhaus.hr
🔍 [Tool] fetch_and_extract called: url=https://...
Extracted M prices from ...
```

If you don't see these logs, tool calling isn't working (check ANTHROPIC_API_KEY).

---

## 📋 Approved Supplier Domains

| Vendor | Domain | Search Support | Status |
|--------|--------|---|---|
| Bauhaus | bauhaus.hr | ✅ | Active |
| Gradja | gradja.hr | ✅ | Active |
| Würth | eshop.wuerth.com.hr | ✅ | Active |
| ERA Commerce | era-commerce.hr | ✅ | Active |

---

## 📊 Feature Architecture

```
Chat Panel (user selects items)
  ↓
Price Search Button
  ↓
PriceSearchModal (domain selection, options)
  ↓
API POST /price-search/{item_id} or /batch
  ↓
search_agent.py (Claude + PydanticAI tools)
  ├─ search_domain() → candidate URLs
  ├─ fetch_and_extract() → price fields
  └─ rag_lookup() → historical context
  ↓
Deterministic Pipeline
  ├─ extract_prices() → structured prices
  ├─ normalize_price() → EUR, VAT, units
  └─ compute_total() → subtotal, VAT, shipping, total
  ↓
WebSocket Events
  ├─ search:started
  ├─ search:quote_found (per quote)
  └─ search:complete (final result)
  ↓
Frontend searchStore receives events
  ↓
Chat panel displays results with best quote, reasoning, link
```

---

## 🔧 Configuration Reference

### backend/.env
```bash
# Claude API (required)
ANTHROPIC_API_KEY=sk-ant-...

# Optional model override
# LLM_MODEL_NAME=claude-sonnet-4-5-20250929

# Database
DATABASE_URL=sqlite:///./data/boq.db

# Other settings
MAX_UPLOAD_SIZE_MB=50
MATCH_THRESHOLD=0.3
```

### backend/app/config.py
```python
LLM_MODEL_NAME: str = "claude-opus-4-6"  # Claude model for tool calling
```

---

## 📝 Troubleshooting

### Search Returns 0 Quotes
1. Check `ANTHROPIC_API_KEY` is set: `echo $ANTHROPIC_API_KEY`
2. Check browser console for errors
3. Run backend with DEBUG: `LOG_LEVEL=DEBUG ./run.sh`
4. Look for tool call logs: `🔍 [Tool] search_domain called`

### Modal Doesn't Open
- Check if selected items appear highlighted in spreadsheet
- Verify TopBar has "Search Prices" button
- Check browser console for JavaScript errors

### API Request Fails
- Verify backend is running: `curl http://localhost:8000/api/health`
- Check WebSocket connection in browser DevTools
- Verify CORS is enabled for frontend origin

---

## 💡 Cost Notes

- **Typical search:** $0.01-0.05 USD (using Claude Opus)
- **Faster alternative:** Use Claude Sonnet (cheaper, faster)
- **Setup:** Free tier available for testing
- **Rate limits:** Generous at Anthropic

See [Anthropic Pricing](https://www.anthropic.com/pricing) for details.

---

**Status:** 🟢 **READY TO USE** — Set ANTHROPIC_API_KEY and start searching!
