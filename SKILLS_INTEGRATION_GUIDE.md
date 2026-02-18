# Skills Integration Guide

This guide shows how to add and use Claude API skills in your agents.

## What You Now Have

1. **Skill Registry** (`skill_registry.py`) - Central management for all skills
2. **Skill Manager** (`skill_manager.py`) - Initialization and attachment logic
3. **Skill Implementations**:
   - `pdf_skill.py` - Extract text, tables, and metadata from PDFs
   - `xlsx_skill.py` - Create and analyze Excel spreadsheets
   - `docx_skill.py` - Create and analyze Word documents

## Quick Start: Adding Skills to Your Search Agent

### Step 1: Initialize Skills in Your Agent

```python
from pydantic_ai import Agent
from app.services.skill_manager import initialize_skills, setup_agent_skills
from app.config import settings

# Initialize the skill system (do this once at startup)
initialize_skills()

# Create your agent
search_agent = Agent(
    model,
    output_type=SearchResult,
    deps_type=SearchDeps,
    system_prompt=SYSTEM_PROMPT,
    retries=2,
    model_settings={"temperature": 0.1},
)

# Setup skills for your agent
if settings.SEARCH_AGENT_SKILLS:
    setup_agent_skills(search_agent, "search_agent")
```

### Step 2: Configure Skills in `.env`

```bash
# Enable/disable individual skills
ENABLE_PDF_SKILL=true
ENABLE_DOCX_SKILL=true
ENABLE_XLSX_SKILL=true
ENABLE_PPTX_SKILL=false

# Define which skills your search agent should use
SEARCH_AGENT_SKILLS=["pdf_extract", "xlsx_handler", "docx_handler"]
```

## Available Skills

### PDF Extraction (`pdf_extract`)

Tools added to agents:
- `extract_pdf_text(file_path, page_range=None)` - Extract text from PDF
- `extract_pdf_tables(file_path)` - Extract tables from PDF
- `get_pdf_metadata(file_path)` - Get PDF metadata

**Requirements:** `pdfplumber`, `PyPDF2`

```python
# Agent can now call these tools
result = await agent.run(
    "Extract all text from document.pdf",
    deps=deps,
)
```

### Excel Processing (`xlsx_handler`)

Tools added to agents:
- `read_excel_sheet(file_path, sheet_name="Sheet1")` - Read Excel data
- `list_excel_sheets(file_path)` - List all sheets
- `create_excel_file(file_path, sheets, headers=None)` - Create new Excel file

**Requirements:** `openpyxl`, `pandas`

```python
# Agent can read and create spreadsheets
result = await agent.run(
    "Create an Excel file with pricing data",
    deps=deps,
)
```

### Word Document Processing (`docx_handler`)

Tools added to agents:
- `read_docx_text(file_path)` - Extract text from Word
- `create_docx_file(file_path, content)` - Create new Word document
- `extract_docx_metadata(file_path)` - Get document metadata

**Requirements:** `python-docx`

```python
# Agent can read and create Word documents
result = await agent.run(
    "Read the specification document and create a summary report",
    deps=deps,
)
```

## Adding Your Own Skills

### 1. Create a New Skill Module

Create `backend/app/services/skills/my_skill.py`:

```python
import logging

logger = logging.getLogger(__name__)

def my_skill_function(param1: str, param2: int) -> dict:
    """
    Your skill implementation.

    Args:
        param1: Description
        param2: Description

    Returns:
        Dictionary with results
    """
    try:
        # Your implementation
        return {"success": True, "result": "..."}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"success": False, "error": str(e)}


SKILL_INFO = {
    "name": "my_skill",
    "description": "What this skill does",
    "functions": [
        {
            "name": "my_skill_function",
            "description": "Description of the function",
            "parameters": {
                "param1": "Parameter description",
                "param2": "Parameter description",
            },
        }
    ],
}
```

### 2. Register Your Skill

Update `skill_manager.py`:

```python
def setup_agent_skills(agent: Any, agent_name: str) -> None:
    # ... existing code ...

    # My Skill
    if "my_skill" in enabled_skills:
        try:
            @agent.tool
            async def my_skill_function(ctx, param1: str, param2: int) -> dict:
                """Description of what the tool does."""
                from app.services.skills.my_skill import my_skill_function
                return my_skill_function(param1, param2)

            skill_tools_attached += 1
            logger.info("Attached My Skill tools")
        except Exception as e:
            logger.error(f"Failed to attach My Skill: {e}")
```

### 3. Enable It in Config

Add to `config.py`:

```python
ENABLE_MY_SKILL: bool = True
SEARCH_AGENT_SKILLS: list[str] = ["pdf_extract", "xlsx_handler", "docx_handler", "my_skill"]
```

## Configuration-Driven Skill Management

### Global Skill Configuration

The skill system is fully configuration-driven:

```python
from app.services.skill_registry import get_skill_registry

registry = get_skill_registry()

# List all registered skills
all_skills = registry.list_skills()

# Get skills enabled for an agent
agent_skills = registry.get_enabled_skills("search_agent")

# Check if a skill is enabled
is_enabled = registry.is_skill_enabled("pdf_extract")

# Register a skill for an agent
registry.register_agent_skills("search_agent", ["pdf_extract", "xlsx_handler"])
```

## Example: Multi-Document Processing Agent

```python
from pydantic_ai import Agent
from pydantic import BaseModel
from app.services.skill_manager import initialize_skills, setup_agent_skills

initialize_skills()

class DocumentAnalysis(BaseModel):
    file_type: str
    summary: str
    key_data: dict

document_agent = Agent(
    model,
    output_type=DocumentAnalysis,
    system_prompt="You are a document analysis expert. Extract key information and provide summaries.",
)

setup_agent_skills(document_agent, "document_agent")

# Now the agent can read PDFs, Excel files, and Word documents
result = await document_agent.run(
    "Analyze the PDF and Excel files in the workspace directory",
    deps=deps,
)
```

## Installing Required Packages

Add to your `requirements.txt`:

```
pdfplumber>=0.10.0
PyPDF2>=3.0.0
openpyxl>=3.10.0
pandas>=2.0.0
python-docx>=0.8.11
python-pptx>=0.6.21
```

Then install:

```bash
pip install -r requirements.txt
```

## Troubleshooting

### "Module not found" errors

Make sure you've installed the required packages:

```bash
pip install pdfplumber PyPDF2 openpyxl pandas python-docx
```

### Skills not appearing in agent

1. Call `initialize_skills()` at startup
2. Call `setup_agent_skills(agent, "agent_name")` after creating the agent
3. Check that `SEARCH_AGENT_SKILLS` in config includes the skill name

### Performance with large files

For large PDF or Excel files, consider:
- Setting `page_range` in `extract_pdf_text()` to limit processing
- Reading specific sheets with `sheet_name` parameter in `read_excel_sheet()`
- Processing files in chunks

## Next Steps

1. Update `backend/app/agents/search_agent.py` to call `setup_agent_skills()`
2. Install the required packages
3. Test with sample PDF, Excel, and Word files
4. Add more skills as needed for your use case
