# Integrating Skills into Your Search Agent

This document shows the exact changes needed to add document processing skills to your existing `search_agent.py`.

## Current State

Your `search_agent.py` currently has:
- Custom tools: `search_domain`, `fetch_and_extract`, `rag_lookup`
- Searches approved supplier domains for pricing

## Modified Version

Update your `backend/app/agents/search_agent.py` with these changes:

### 1. Add Imports

At the top of the file, add:

```python
from app.services.skill_manager import initialize_skills, setup_agent_skills
```

### 2. Initialize Skills

After creating the `search_agent`, add skill initialization:

```python
# At module level, after search_agent creation (around line 173)

# Initialize the skill system at module load time
initialize_skills()

# Setup skills for the search agent
setup_agent_skills(search_agent, "search_agent")
```

### 3. Update the System Prompt (Optional)

If you want the agent to know about the new document skills, update `SYSTEM_PROMPT`:

```python
SYSTEM_PROMPT = """\
You are a Croatian construction materials price search specialist. Your task is to \
find current prices for construction materials and services on approved supplier websites.

You have access to these tools:
- search_domain: Search a specific approved domain for products
- fetch_and_extract: Fetch a product page and extract price information
- rag_lookup: Look up historical prices from internal database
- extract_pdf_text: Extract text from PDF documents (for spec sheets, catalogs)
- extract_pdf_tables: Extract tables from PDF documents
- read_excel_sheet: Read Excel pricing data
- create_excel_file: Create Excel reports with quotes

Workflow:
1. Analyze the item description to understand what product/material to search for
2. Generate good search queries (Croatian construction terms)
3. Search each approved domain using search_domain
4. For promising candidates, use fetch_and_extract to get detailed pricing
5. If specification PDFs or Excel files are available, extract data using document tools
6. Compare results and reason about which quotes best match the target item

Important:
- Only search approved domains (bauhaus.hr, gradja.hr, wuerth, era-commerce.hr)
- Report confidence honestly — don't guess if you can't find a match
- Consider unit compatibility (m², kom, m, kg, etc.)
- Croatian terminology: cijena = price, komad = piece, količina = quantity
- PDV = VAT (25% in Croatia), most prices include PDV\
"""
```

### 4. Updated Requirements

Add to `requirements.txt`:

```
pdfplumber>=0.10.0
PyPDF2>=3.0.0
openpyxl>=3.10.0
pandas>=2.0.0
python-docx>=0.8.11
```

## Example: Using Skills in Searches

Now your search agent can do things like:

```python
# Agent can extract price lists from PDFs
"Search for ceramic tiles on Bauhaus. If they have a PDF price list,
extract the pricing table and compare with web prices."

# Agent can read and create Excel reports
"Search for concrete on all suppliers, compile a comparison
in an Excel file with columns: [Vendor, Product, Unit Price, Availability]"

# Combined document and web search
"Read the specification PDF for floor tiles, search for matching products
on approved suppliers, and create a report with the best 3 quotes."
```

## Minimal Integration (If You Just Want to Try It)

If you just want to test this without modifying the full agent:

```python
# In backend/app/agents/search_agent.py, after imports

from app.services.skill_manager import initialize_skills, setup_agent_skills

# ... existing code ...

# After search_agent creation:
initialize_skills()
setup_agent_skills(search_agent, "search_agent")
```

That's it! The agent now has document processing capabilities.

## Configuration for Your Use Case

Update `.env` to enable/disable skills as needed:

```env
# Enable document processing for search agent
ENABLE_PDF_SKILL=true
ENABLE_DOCX_SKILL=true
ENABLE_XLSX_SKILL=true

# Define skills for search agent
SEARCH_AGENT_SKILLS=["pdf_extract", "xlsx_handler", "docx_handler"]
```

## Usage Example

With skills integrated, you can now use your search agent like this:

```python
# backend/app/api/search_endpoint.py

from app.agents.search_agent import run_price_search

result = await run_price_search(
    description="Ceramic floor tiles 30x30cm - read spec sheet from PDF and search prices",
    unit="m²",
    quantity=50,
)

# result.quotes will include prices extracted from PDFs and web searches
# result.computed will have the total calculation
# result.reasoning will explain how documents were analyzed
```

## What Each Document Tool Does in Your Agent

| Tool | Use Case |
|------|----------|
| `extract_pdf_text` | Read product datasheets, specification sheets, catalogs |
| `extract_pdf_tables` | Extract pricing tables from supplier PDFs |
| `read_excel_sheet` | Read existing price lists in Excel format |
| `create_excel_file` | Generate a comparison spreadsheet with all found quotes |
| `read_docx_text` | Extract product descriptions from Word specs |

## Testing Your Integration

1. **Install packages:**
   ```bash
   pip install pdfplumber PyPDF2 openpyxl pandas python-docx
   ```

2. **Restart your app** - The agent will now have document processing tools

3. **Test with a request:**
   ```python
   result = await run_price_search(
       description="Check the PDF catalog for pricing",
       unit="kom",
   )
   ```

4. **Check the search log:**
   ```python
   for log_entry in result.search_log:
       print(log_entry)
   ```

## Rollback (If Needed)

If you want to remove skills, simply comment out or remove:

```python
# Comment out these two lines to disable skills
# initialize_skills()
# setup_agent_skills(search_agent, "search_agent")
```

The agent will continue to work with just the built-in tools.
