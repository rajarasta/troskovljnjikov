# Price Search Diagnosis: Root Cause Analysis

## Summary
**The price search feature returns 0 quotes because the local LLM (`ministral-3b`) doesn't properly support function/tool calling.**

Item descriptions ARE reaching the backend correctly. The problem is downstream in the search agent execution.

---

## Evidence

### ✅ What's Working
1. **Frontend → Backend description flow is GOOD**
   - ExcelView captures `cell.text` and creates synthetic items with `description: cell.text`
   - SelectionStore preserves items and their descriptions
   - Batch API payload includes descriptions
   - Backend's Lookup Agent successfully resolves items to their descriptions

   Example from console logs:
   ```
   [Lookup Agent] Resolved: excel-cell-65-1 -> Nabava materijala, dovoz i zidanje...
   ```

2. **Description validation works**
   - Generic descriptions like "m²" are correctly rejected with: "Description too generic for meaningful search"

### ❌ What's Broken
1. **Search agent returns 0 quotes for all searches**
2. **search_log contains hallucinated supplier data, not real tool outputs**

   Example of hallucinated output:
   ```
   search_log: ["Supplier A: Price $100, Confidence: 95%, Historical Price: $98",
                "Supplier B: Price $98, Confidence: 92%, Historical Price: $102"]
   ```

   This is completely fabricated - it's what the LLM THINKS the response should be.

3. **Actual tool calls are NOT happening**
   - Should see logs like: "Searching bauhaus.hr for: cement"
   - Should see: "Found X candidates on bauhaus.hr"
   - Should see: "Fetching: https://www.bauhaus.hr/product/..."
   - Should see: "Extracted X prices from ..."

   But instead, the agent generates fake data.

---

## Root Cause

**Model: `ministral-3b` (local LLM via llama-server on port 8095)**

This model doesn't properly support [OpenAI function calling spec](https://platform.openai.com/docs/guides/function-calling) when accessed via OpenAI-compatible API.

### How PydanticAI Tool Calling Works
1. Agent defines tools using `@agent.tool` decorators
2. On each run, agent requests to call tools
3. Framework intercepts tool calls and executes them
4. Results are fed back to agent for interpretation

### What's Happening with ministral-3b
- ❌ Agent doesn't recognize or request tools
- ❌ Agent generates response without tool calls
- ❌ Framework has no tool calls to execute
- ❌ LLM just hallucinnates what it thinks the answer should be

---

## Solution Options

### Option 1: ✅ Use Claude API (RECOMMENDED)
**Most reliable - guaranteed tool support**

```python
# backend/app/config.py
LLM_BASE_URL: str = "https://api.anthropic.com/v1"  # Or proxy
LLM_MODEL_NAME: str = "claude-opus-4-6"  # or claude-sonnet-4-5
```

Pros:
- Production-grade tool calling
- Excellent at following instructions
- No local GPU required
- Faster API responses

Cons:
- Requires API key (but Claude API has generous rate limits)
- Network dependency

### Option 2: Use Better Local Model (Mixtral-8x7b)
**More resource-intensive but fully local**

```bash
# Download Mixtral quantized model
wget https://huggingface.co/.../mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf
```

Pros:
- Fully local, no API calls
- Better tool calling support
- ~30GB model, but quantized versions available

Cons:
- Requires significant GPU VRAM
- Slower inference
- Complex to set up

### Option 3: Fallback Search Without Tools
**Lower-quality but doesn't require LLM tool support**

Manually implement domain search without relying on agent:
- Directly call `search_domain()` logic without tool wrapper
- Fetch from Google/Bing using site: queries
- Skip tool-based approach entirely

Pros:
- Works with current ministral-3b
- No API dependency

Cons:
- Less flexible
- Can't use agent reasoning
- Less reliable extraction

---

## Immediate Next Steps

1. **Confirm tool calls aren't happening:**
   ```bash
   # Run with DEBUG logging
   LOG_LEVEL=DEBUG ./run.sh
   # Look for: "🔍 [Tool] search_domain called"
   # If you don't see these, tools aren't being called
   ```

2. **Choose a solution path** (recommend Option 1: Claude API)

3. **Implement fix** and re-test

---

## Why Descriptions Looked "Missing" Earlier

In the earlier debugging, descriptions appeared to be lost because:
- Batch searches triggered without descriptions in the original code
- But we FIXED that - descriptions are now passed correctly
- The NEW problem is that even with correct descriptions, the search agent doesn't work

This is why proper debugging revealed the real issue! The descriptions were never the problem - it was always the LLM tool calling.
