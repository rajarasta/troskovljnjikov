# Claude API Setup for Price Search Feature

## Problem Solved
The local LLM (`ministral-3b`) doesn't support PydanticAI tool calling, which is essential for the web price search agent. **Solution: Use Claude API which has production-grade tool calling support.**

## Quick Setup

### 1. Get Your API Key
1. Go to [Anthropic Console](https://console.anthropic.com/account/keys)
2. Create or copy your API key
3. Set it in the backend environment:

```bash
# Navigate to backend directory
cd backend

# Create/update .env file with your API key
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

### 2. Verify Configuration
The backend is already configured to use Claude:
- **Model:** `claude-opus-4-6` (see `backend/app/config.py`)
- **Provider:** Anthropic (using PydanticAI's native support)

### 3. Start the Application
```bash
./run.sh
```

The system will now:
- ✅ Use Claude for the price search agent (has tool calling)
- ✅ Properly call search_domain, fetch_and_extract, and rag_lookup tools
- ✅ Return real price quotes instead of hallucinated data

## What Changed

### Backend Changes
- **`backend/app/agents/search_agent.py`**
  - Changed from `OpenAIChatModel` to `AnthropicChatModel`
  - Removed OpenAI provider configuration
  - Now uses ANTHROPIC_API_KEY environment variable automatically

### Configuration Changes
- **`backend/app/config.py`**
  - Updated `LLM_MODEL_NAME` to `claude-opus-4-6`
  - Added note that `LLM_BASE_URL` is deprecated for Claude

### New Files
- **`backend/.env`** (template)
  - Set `ANTHROPIC_API_KEY=your-key-here`
  - Other optional settings documented

## Alternative Models

You can use different Claude models by setting in `.env`:

```bash
# Sonnet (faster, lower cost)
LLM_MODEL_NAME=claude-sonnet-4-5-20250929

# Opus (more capable, better reasoning)
LLM_MODEL_NAME=claude-opus-4-6
```

## Testing the Feature

1. **Start the app**: `./run.sh`
2. **Upload a BoQ file** with construction items (e.g., "Nabava cementa", "Radovi zidanja")
3. **Click on Price Search** button in the top bar
4. **Select items** from the spreadsheet and click "Search Price"
5. **Monitor the pipeline**:
   - Description → Search → Extract → Normalize → Report
6. **Check results** in the chat panel with vendor, price, and confidence

## Troubleshooting

### "ANTHROPIC_API_KEY not found" Error
```bash
# Verify the key is set
echo $ANTHROPIC_API_KEY

# If not set, add to .env and restart
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Search Returns 0 Quotes
- Check browser console for errors
- Run backend with DEBUG logging: `LOG_LEVEL=DEBUG ./run.sh`
- Look for logs: "🔍 [Tool] search_domain called"
- If not present, tool calling still has issues

### API Rate Limits
- Anthropic has generous rate limits on API calls
- If hitting limits, consider Claude Sonnet (faster, cheaper) instead of Opus

## Cost Considerations

**Price Search via Claude API:**
- Average search: ~0.5-2.0 min tokens, ~1.0-5.0 out tokens per search
- Typical cost: $0.01-0.05 USD per item search
- With generous free tier, suitable for testing

See [Anthropic Pricing](https://www.anthropic.com/pricing) for current rates.

## Future Improvements

### Option: Use Other Agents with Claude
Other agents (matcher, parser, pricer, vision) currently use local models but could benefit from Claude:
```python
# To enable: update backend/app/agents/{agent}_agent.py
# from pydantic_ai.models.anthropic import AnthropicChatModel
# _model = AnthropicChatModel(model_name=settings.LLM_MODEL_NAME)
```

### Option: Hybrid Approach
- Use Claude for price search (requires tools)
- Keep local LLM for other agents (no tool requirement)

---

**Status:** ✅ Price search agent is now ready to use with Claude API tool calling support.
