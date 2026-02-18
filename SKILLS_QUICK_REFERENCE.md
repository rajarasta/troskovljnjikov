# Skills Quick Reference

## What Was Created

| File | Purpose |
|------|---------|
| `backend/app/services/skill_registry.py` | Central skill registry and management |
| `backend/app/services/skill_manager.py` | Skill initialization and attachment |
| `backend/app/services/skills/pdf_skill.py` | PDF extraction tools |
| `backend/app/services/skills/xlsx_skill.py` | Excel processing tools |
| `backend/app/services/skills/docx_skill.py` | Word document tools |
| `backend/app/agents/document_processor_agent.py` | Example agent using skills |
| `SKILLS_INTEGRATION_GUIDE.md` | Full integration documentation |

## Installation

1. **Install required packages:**

```bash
pip install pdfplumber PyPDF2 openpyxl pandas python-docx
```

2. **Update your `.env`:**

```env
ENABLE_PDF_SKILL=true
ENABLE_DOCX_SKILL=true
ENABLE_XLSX_SKILL=true
SEARCH_AGENT_SKILLS=["pdf_extract", "xlsx_handler", "docx_handler"]
```

## Using Skills in Your Agents

### Option 1: Add Skills to Existing Agent

```python
from app.services.skill_manager import initialize_skills, setup_agent_skills

# At app startup
initialize_skills()

# After creating your agent
setup_agent_skills(your_agent, "search_agent")
```

### Option 2: Use the Example Document Processor Agent

```python
from backend.app.agents.document_processor_agent import process_documents

result = await process_documents(
    file_paths=["document.pdf", "data.xlsx"],
    analysis_prompt="Extract all pricing information"
)
```

## Available Tools by Skill

### PDF Skill (`pdf_extract`)
- `extract_pdf_text(file_path, page_range=None)` → Extract text
- `extract_pdf_tables(file_path)` → Extract tables
- `get_pdf_metadata(file_path)` → Get metadata

### Excel Skill (`xlsx_handler`)
- `read_excel_sheet(file_path, sheet_name="Sheet1")` → Read data
- `list_excel_sheets(file_path)` → List sheets
- `create_excel_file(file_path, sheets, headers=None)` → Create file

### Word Skill (`docx_handler`)
- `read_docx_text(file_path)` → Extract text
- `create_docx_file(file_path, content)` → Create file
- `extract_docx_metadata(file_path)` → Get metadata

## Configuration

### Config Settings (in `config.py`)

```python
# Enable/disable skills
ENABLE_PDF_SKILL: bool = True
ENABLE_DOCX_SKILL: bool = True
ENABLE_XLSX_SKILL: bool = True
ENABLE_PPTX_SKILL: bool = False

# Define skills per agent
SEARCH_AGENT_SKILLS: list[str] = ["pdf_extract", "xlsx_handler", "docx_handler"]
```

### Adding Skills to Your Agent

1. Add skill name to `SEARCH_AGENT_SKILLS` in config
2. Call `initialize_skills()` at startup
3. Call `setup_agent_skills(agent, "search_agent")`

## Common Patterns

### Reading Multiple Files

```python
# Agent will use the tools to read different file types
result = await agent.run(
    "Read all files and summarize the pricing information",
    deps=deps,  # deps.file_paths contains the file list
)
```

### Creating Reports

```python
# Agent can create new Excel or Word files
result = await agent.run(
    "Analyze the data and create a summary report in Word format",
    deps=deps,
)
```

### Data Extraction and Analysis

```python
# Combine reading, analysis, and report generation
result = await agent.run(
    "Extract data from the PDF, read the Excel spreadsheet, "
    "compare the values, and create a report with discrepancies",
    deps=deps,
)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Module not found" | Install packages: `pip install pdfplumber PyPDF2 openpyxl pandas python-docx` |
| Skills not working | Call `initialize_skills()` before creating agents |
| Skill tool not attached | Check that skill name is in `SEARCH_AGENT_SKILLS` |
| Large file processing slow | Use `page_range` or `sheet_name` parameters to limit scope |

## Next Steps

1. ✅ Create test agent with sample documents
2. ✅ Update search agent to include document skills
3. ✅ Add more skills as needed (PowerPoint, JSON, CSV, etc.)
4. ✅ Integrate with your API endpoints

## Architecture Diagram

```
┌─────────────────────────────────────┐
│     Your PydanticAI Agents          │
│  (search_agent, etc.)               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│    Skill Manager                    │
│  (setup_agent_skills)               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│    Skill Registry                   │
│  (get_skill_registry)               │
└──────────────┬──────────────────────┘
               │
       ┌───────┼───────┬──────────┐
       ▼       ▼       ▼          ▼
    PDF    Excel   Word      Custom
   Tools   Tools   Tools      Tools
```

## For More Details

See `SKILLS_INTEGRATION_GUIDE.md` for:
- Detailed examples
- Creating custom skills
- Configuration-driven management
- Advanced usage patterns
