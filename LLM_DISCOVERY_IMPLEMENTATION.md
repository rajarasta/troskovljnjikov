# LLM Endpoint Discovery & Registry - Implementation Summary

## Overview
Complete implementation of LLM endpoint discovery, health checking, and registry management for llama.cpp/llama-server endpoints.

## What Was Implemented

### Backend

#### 1. **New Service: `backend/app/services/llm_discovery.py`**
- **Port Scanner**: Async scanning of common LLM ports (8000, 8008, 8040, 8080, 8095, 8096, 8110, 11434)
- **Health Check**: Probes endpoints via `/v1/models` or `/health` with configurable timeout
- **Endpoint Registry**: Persists to `backend/data/llm_endpoints.json`
- **Active Endpoint Management**: Tracks which endpoint is currently selected
- **Model Detection**: Extracts model IDs from discovered endpoints

**Key Functions:**
```python
async def probe_endpoint(url: str) -> EndpointInfo
async def scan_common_ports() -> list[EndpointInfo]
def add_endpoint(url: str) -> list[EndpointInfo]
def remove_endpoint(url: str) -> list[EndpointInfo]
def set_active_url(url: str) -> None
def get_active_url() -> str
def merge_discovered_endpoints(discovered: list[EndpointInfo]) -> None
```

#### 2. **Extended Router: `backend/app/routers/llm_settings.py`**
New REST API endpoints for endpoint management:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/llm-settings/endpoints` | List all registered endpoints |
| POST | `/api/llm-settings/endpoints` | Add endpoint manually `{url: str}` |
| DELETE | `/api/llm-settings/endpoints` | Remove endpoint `{url: str}` |
| POST | `/api/llm-settings/endpoints/scan` | Scan common ports, return discovered |
| POST | `/api/llm-settings/endpoints/health` | Health check specific URL `{url: str}` |
| PUT | `/api/llm-settings/endpoints/active` | Set active endpoint `{url: str}` |

Also updated:
- `GET /api/llm-settings/global/models` now uses active endpoint from discovery

#### 3. **Updated Service: `backend/app/services/llm_settings.py`**
- Dynamic `_provider` creation based on active endpoint URL
- Automatic cache invalidation when endpoint changes
- `get_model()` and `get_model_for_agent()` use dynamic provider
- New `_get_or_create_provider()` function

#### 4. **Updated Main: `backend/app/main.py`**
- Background startup task `_startup_discovery()` in lifespan
- Non-blocking async scan on app startup
- Auto-discovery logs results but doesn't block server initialization

### Frontend

#### 1. **Extended API Client: `frontend/src/lib/api/llmSettings.ts`**
New `EndpointInfo` type and functions:
```typescript
export interface EndpointInfo {
  url: string;
  status: "online" | "offline" | "unknown";
  models: string[];
  is_active: boolean;
  last_checked: string | null;
}

async function fetchEndpoints(): Promise<{ endpoints: EndpointInfo[] }>
async function scanEndpoints(): Promise<{ endpoints: EndpointInfo[] }>
async function probeEndpoint(url: string): Promise<{ endpoint: EndpointInfo }>
async function addEndpoint(url: string): Promise<{ endpoints: EndpointInfo[] }>
async function removeEndpoint(url: string): Promise<{ endpoints: EndpointInfo[] }>
async function setActiveEndpoint(url: string): Promise<{ active_url: string }>
```

#### 2. **Extended Store: `frontend/src/stores/llmSettingsStore.ts`**
New state and methods:
- `endpoints: EndpointInfo[]` - current endpoint list
- `endpointsLoading: boolean` - fetch loading state
- `scanLoading: boolean` - scan operation state
- `fetchEndpoints()`, `scanEndpoints()`, `addEndpoint()`, `removeEndpoint()`, `setActiveEndpoint()`
- Auto-refresh models after changing active endpoint

#### 3. **Extended UI: `frontend/src/components/layout/LlmControlBoard.tsx`**
New **"LLM Endpoints"** section above Global Model selector:

**Features:**
- Live endpoint list with status indicators (● = online, ○ = offline)
- Scan button with loading state
- Set active endpoint button (● shows active, ○ shows inactive)
- Remove endpoint button per endpoint
- Add custom endpoint form with URL input

**UI Layout:**
```
┌─ LLM Endpoints ─────────────────────── [Scan] ─┐
│ ● http://localhost:8095/v1    [●Set] [🗑]      │
│ ○ http://localhost:8080/v1    [ Set] [🗑]      │
│ ○ http://localhost:11434/v1   [ Set] [🗑]      │
│ + Add: [_____________________] [Add]            │
└────────────────────────────────────────────────┘
```

## Data Persistence

**File: `backend/data/llm_endpoints.json`**
```json
{
  "endpoints": [
    {
      "url": "http://localhost:8095/v1",
      "status": "online",
      "models": ["ministral-3b"],
      "is_active": true,
      "last_checked": "2025-02-18T10:30:45.123456Z"
    }
  ],
  "active_url": "http://localhost:8095/v1"
}
```

## Testing Checklist

### Backend

```bash
# 1. Start backend with auto-discovery
python -m uvicorn app.main:app --reload

# Check logs for: "Starting LLM endpoint discovery..." and results

# 2. List endpoints
curl http://localhost:8000/api/llm-settings/endpoints

# 3. Scan ports
curl -X POST http://localhost:8000/api/llm-settings/endpoints/scan

# 4. Check specific endpoint
curl -X POST http://localhost:8000/api/llm-settings/endpoints/health \
  -H "Content-Type: application/json" \
  -d '{"url": "http://localhost:8095/v1"}'

# 5. Add endpoint manually
curl -X POST http://localhost:8000/api/llm-settings/endpoints \
  -H "Content-Type: application/json" \
  -d '{"url": "http://localhost:8000/v1"}'

# 6. Set active endpoint
curl -X PUT http://localhost:8000/api/llm-settings/endpoints/active \
  -H "Content-Type: application/json" \
  -d '{"url": "http://localhost:8095/v1"}'

# 7. Verify models use active endpoint
curl http://localhost:8000/api/llm-settings/global/models
```

### Frontend

1. **View Endpoints Section**:
   - Open LlmControlBoard (sidebar)
   - New "LLM Endpoints" section visible above "Global Model"

2. **Auto-Discovery**:
   - Refresh page after backend starts
   - Check if any endpoints appear automatically

3. **Manual Scan**:
   - Click "Scan" button
   - Wait for endpoints to appear
   - Status should show "online"/"offline"

4. **Switch Active Endpoint**:
   - Click "Set" button on an endpoint
   - Verify models dropdown refreshes
   - Check that models from that endpoint appear

5. **Add Custom Endpoint**:
   - Type URL in "Add" field (e.g., `http://localhost:8000/v1`)
   - Click "Add"
   - Endpoint appears in list

6. **Remove Endpoint**:
   - Click trash icon on any endpoint
   - Endpoint disappears from list

## Key Design Decisions

1. **Non-Blocking Discovery**: Startup scan doesn't block server initialization; runs in background
2. **Graceful Degradation**: Missing endpoints fall back to environment config
3. **Dynamic Provider**: OpenAI provider rebuilt when active endpoint changes (avoids model cache issues)
4. **One Active Endpoint**: Only one endpoint can be active for local LLM at a time
5. **Concurrent Scanning**: Port scans use `asyncio.gather` for speed
6. **Normalization**: URLs auto-normalized to `http://host:port/v1` format
7. **Model Cache Invalidation**: Changing active endpoint clears cached model so it's rebuilt with new provider

## Common Port Mapping

- `8000`, `8008`: ollama, vLLM, other servers
- `8040`: mistral.rs
- `8080`: nginx (common reverse proxy)
- `8095`, `8096`: llama-server defaults
- `8110`: alternative llama-server port
- `11434`: Ollama API

## Future Enhancements

- [ ] Endpoint auto-retry on failure
- [ ] Batch import/export endpoint configs
- [ ] Endpoint latency measurement
- [ ] Model compatibility checking per endpoint
- [ ] Endpoint priority/ordering
- [ ] Multi-endpoint load balancing
