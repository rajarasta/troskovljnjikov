# Agentic Document Editor v1 — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a working Streamlit + PydanticAI multi-agent document analysis app backed by a local llama-server.

**Architecture:** Single-file Streamlit app (`main.py`) with two PydanticAI agents (orchestrator + confirmation specialist) connected to a local llama-server via OpenAI-compatible API. State managed via `st.session_state`. Launched with a single shell script.

**Tech Stack:** Python 3.11+, Streamlit, PydanticAI, Pydantic, pandas, openpyxl, openai, httpx, uv (package manager)

---

### Task 1: Project Setup — pyproject.toml

**Files:**
- Create: `pyproject.toml`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "company-agent-ui"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic-ai",
    "streamlit",
    "pandas",
    "openpyxl",
    "openai",
    "httpx",
]

[tool.uv]
package = true
```

**Step 2: Verify uv can resolve dependencies**

Run: `uv lock`
Expected: Creates `uv.lock` file without errors.

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add pyproject.toml with dependencies"
```

---

### Task 2: Main App — State Management & Schemas

**Files:**
- Create: `main.py` (first section only — state + schemas + model)

**Step 1: Write the state management and schema section of main.py**

```python
import streamlit as st
import asyncio
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

# --- 1. STATE MANAGEMENT ---
if 'ui_state' not in st.session_state:
    st.session_state.ui_state = {
        "summary": "No analysis performed yet.",
        "logs": [],
        "anchors": {"second": "?", "penultimate": "?"}
    }

def add_log(msg: str):
    st.session_state.ui_state["logs"].append(msg)

# --- 2. SCHEMAS & MODELS ---
class ConfirmationVerdict(BaseModel):
    approved: bool = Field(description="True if the logic is sound")
    reason: str = Field(description="Explanation of the verdict")

# Connect to local llama-server
model = OpenAIModel(model_name='llama3', base_url='http://localhost:8080/v1')
```

Note: The PydanticAI API may use `OpenAIChatModel` instead of `OpenAIModel` depending on the installed version. If `OpenAIModel` fails on import, change to:
```python
from pydantic_ai.models.openai import OpenAIChatModel
model = OpenAIChatModel('llama3', base_url='http://localhost:8080/v1')
```

**Step 2: Run a quick import check**

Run: `uv run python -c "from pydantic_ai import Agent, RunContext; from pydantic_ai.models.openai import OpenAIModel; print('OK')"`
Expected: Either prints `OK` or shows the correct import name. Fix the import if needed.

**Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add state management, schemas, and model config"
```

---

### Task 3: Main App — Agents & Tools

**Files:**
- Modify: `main.py` (append agents and tools after the schema section)

**Step 1: Add the agents section**

Append to `main.py` after the model definition:

```python
# --- 3. AGENTS ---
# Main Agent (The Orchestrator)
orchestrator = Agent(model, deps_type=str)

# Confirmation Agent (Transient Specialist)
confirm_agent = Agent(model, result_type=ConfirmationVerdict)
```

Note: If the API uses `output_type` instead of `result_type`, change to:
```python
confirm_agent = Agent(model, output_type=ConfirmationVerdict)
```

**Step 2: Add the tools section**

Append to `main.py` after agents:

```python
# --- 4. TOOLS ---
@orchestrator.tool
def get_anchor_letters(ctx: RunContext[str]) -> dict:
    """Extracts 2nd and 2nd-to-last letters."""
    text = ctx.deps
    res = {"second": text[1], "penultimate": text[-2]}
    st.session_state.ui_state["anchors"] = res
    return res

@orchestrator.tool
async def verify_logic(ctx: RunContext[str], proposal: str) -> str:
    """Summons a Confirmation Agent to double-check the Orchestrator's plan."""
    add_log(f"Summoning Confirmation Agent for: {proposal}")

    # This agent runs and then 'unspawns' when the function returns
    verdict = await confirm_agent.run(f"Verify this proposal: {proposal}")

    status = "APPROVED" if verdict.data.approved else "REJECTED"
    add_log(f"Verdict: {status} - {verdict.data.reason}")

    # Update global summary state
    st.session_state.ui_state["summary"] = f"Last Check: {status}. {verdict.data.reason}"
    return status
```

Note: If the API uses `verdict.output` instead of `verdict.data`, adjust accordingly.

**Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add orchestrator and confirmation agents with tools"
```

---

### Task 4: Main App — Streamlit UI

**Files:**
- Modify: `main.py` (append UI layout after the tools section)

**Step 1: Add the UI layout section**

Append to `main.py`:

```python
# --- 5. UI LAYOUT ---
st.set_page_config(page_title="Company Doc AI", layout="wide")
st.title("Agentic Document Editor")

col1, col2 = st.columns([2, 1])

with col1:
    uploaded_file = st.file_uploader("Upload Document", type=['txt', 'xlsx'])
    if uploaded_file:
        content = uploaded_file.getvalue().decode("utf-8")

        if st.button("Start Multi-Agent Analysis"):
            with st.spinner("Agents are thinking..."):
                add_log("Starting Orchestrator...")
                # Run the async logic
                asyncio.run(orchestrator.run(
                    "Identify the anchor letters and verify if they form a valid pattern.",
                    deps=content
                ))
            st.success("Analysis Complete")

    st.subheader("Document Summary")
    st.info(st.session_state.ui_state["summary"])

with col2:
    st.subheader("Agent Activity Log")
    for log in reversed(st.session_state.ui_state["logs"]):
        st.caption(log)

    st.subheader("Extracted Anchors")
    st.json(st.session_state.ui_state["anchors"])
```

**Step 2: Verify the app starts (without llama-server — just UI rendering)**

Run: `uv run streamlit run main.py --server.headless true &` then `sleep 3 && curl -s http://localhost:8501 | head -20`
Expected: HTML output from Streamlit (confirms app loads). Kill the process after.

**Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add Streamlit UI layout with file upload and agent display"
```

---

### Task 5: Launcher Script — run.sh

**Files:**
- Create: `run.sh`

**Step 1: Create run.sh**

```bash
#!/bin/bash
# Agentic Document Editor Launcher
# Starts llama-server in background, then launches Streamlit UI.
# Cleans up llama-server on exit.

set -e

# 1. Start the LLM Server in background
echo "Starting llama-server..."
./bin/llama-server -m ./models/llama3.gguf --parallel 4 --cont-batching --cache-reuse 512 &
SERVER_PID=$!

# Give the server a moment to start
sleep 3

# 2. Run the UI (uv will install everything on first run)
echo "Launching UI..."
uv run streamlit run main.py

# 3. Cleanup on exit
kill $SERVER_PID 2>/dev/null || true
echo "Shut down llama-server."
```

**Step 2: Make executable**

Run: `chmod +x run.sh`

**Step 3: Commit**

```bash
git add run.sh
git commit -m "feat: add one-click launcher script"
```

---

### Task 6: API Compatibility Verification

**Files:**
- Modify: `main.py` (fix any import/API mismatches found)

**Step 1: Install deps and check PydanticAI API**

Run: `uv run python -c "import pydantic_ai; print(pydantic_ai.__version__); from pydantic_ai import Agent; import inspect; print([m for m in dir(Agent) if not m.startswith('_')])"`
Expected: Version number and list of Agent methods/attributes. Look for `result_type` vs `output_type`, and check the result object attributes.

**Step 2: Check OpenAIModel import**

Run: `uv run python -c "from pydantic_ai.models.openai import OpenAIModel; print('OpenAIModel OK')" 2>&1 || uv run python -c "from pydantic_ai.models.openai import OpenAIChatModel; print('OpenAIChatModel OK')"`
Expected: One of them prints OK. Use whichever works.

**Step 3: Fix any mismatches in main.py**

If the API uses different names than what's in the code, update main.py accordingly:
- `OpenAIModel` → `OpenAIChatModel` (if needed)
- `result_type=` → `output_type=` (if needed)
- `verdict.data` → `verdict.output` (if needed)

**Step 4: Commit fixes**

```bash
git add main.py
git commit -m "fix: align with installed pydantic-ai API version"
```

---

### Task 7: End-to-End Smoke Test (with llama-server)

This task requires the user's llama-server to be running.

**Step 1: Confirm llama-server is reachable**

Run: `curl -s http://localhost:8080/v1/models | head -5`
Expected: JSON listing available models. If not running, start it manually.

**Step 2: Run the app**

Run: `uv run streamlit run main.py`
Expected: Streamlit opens in browser. Upload a .txt file, click "Start Multi-Agent Analysis", see logs and results populate.

**Step 3: Create a test file for smoke testing**

Create `test_input.txt` with content: `Hello World from the Agentic Editor`

Upload it via the UI and verify:
- Anchor letters extracted: second="e", penultimate="o"
- Confirmation agent runs and returns a verdict
- Summary and logs update

**Step 4: Commit test file**

```bash
git add test_input.txt
git commit -m "test: add smoke test input file"
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Project setup | `pyproject.toml`, `uv.lock` |
| 2 | State + schemas + model | `main.py` (create) |
| 3 | Agents + tools | `main.py` (append) |
| 4 | Streamlit UI | `main.py` (append) |
| 5 | Launcher script | `run.sh` |
| 6 | API compatibility check | `main.py` (fix if needed) |
| 7 | End-to-end smoke test | manual verification |
