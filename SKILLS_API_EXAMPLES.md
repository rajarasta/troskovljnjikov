# Skills API Examples

Practical examples of how to use the new skills through your API endpoints.

## Using the Document Processor Agent

### Example 1: Process a Single PDF

```bash
curl -X POST http://localhost:8000/api/documents/process \
  -H "Content-Type: application/json" \
  -d '{
    "file_paths": ["./uploads/supplier_catalog.pdf"],
    "analysis_prompt": "Extract all product prices and specifications"
  }'
```

Response:
```json
{
  "documents_processed": 1,
  "extractions": [
    {
      "file_path": "./uploads/supplier_catalog.pdf",
      "file_type": "pdf",
      "summary": "Product catalog with 25 items and pricing",
      "key_findings": {
        "total_products": 25,
        "price_range": "$10 - $500",
        "categories": ["Tiles", "Paint", "Hardware"]
      },
      "metadata": {
        "pages": 15,
        "author": "Supplier Name"
      }
    }
  ],
  "combined_analysis": "The catalog contains...",
  "reasoning": "Used PDF extraction to..."
}
```

### Example 2: Compare Multiple File Types

```bash
curl -X POST http://localhost:8000/api/documents/process \
  -H "Content-Type: application/json" \
  -d '{
    "file_paths": [
      "./uploads/spec_sheet.pdf",
      "./uploads/pricing_data.xlsx",
      "./uploads/requirements.docx"
    ],
    "analysis_prompt": "Compare the specifications with requirements and pricing"
  }'
```

Response will include extractions from all three file types.

## Using Skills with Search Agent

### Example 3: Search with PDF Price Lists

```bash
curl -X POST http://localhost:8000/api/search/price \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Ceramic floor tiles 30x30cm - check supplier PDF for reference prices",
    "unit": "m²",
    "quantity": 50,
    "pdf_path": "./uploads/reference_pricing.pdf"
  }'
```

The search agent will:
1. Extract pricing from the PDF
2. Search online suppliers
3. Compare all prices
4. Return best matches

### Example 4: Generate Comparison Report

```bash
curl -X POST http://localhost:8000/api/search/price \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Search for ceramic tiles on all suppliers",
    "unit": "m²",
    "quantity": 50,
    "generate_report": true,
    "report_format": "xlsx"
  }'
```

Response:
```json
{
  "quotes": [...],
  "best_quote": {...},
  "report_file": "./reports/price_comparison_2024_02_17.xlsx",
  "report_url": "/api/files/reports/price_comparison_2024_02_17.xlsx"
}
```

## API Endpoint Examples

### New Endpoints to Add

#### 1. Process Documents Endpoint

**File:** `backend/app/api/documents.py`

```python
from fastapi import APIRouter, UploadFile, File
from app.agents.document_processor_agent import process_documents
from pydantic import BaseModel

router = APIRouter(prefix="/api/documents", tags=["documents"])

class ProcessDocumentsRequest(BaseModel):
    file_paths: list[str]
    analysis_prompt: str = ""

@router.post("/process")
async def process_docs(request: ProcessDocumentsRequest):
    """Process documents using the document processor agent."""
    result = await process_documents(
        file_paths=request.file_paths,
        analysis_prompt=request.analysis_prompt,
    )
    return result

@router.post("/upload-and-process")
async def upload_and_process(files: list[UploadFile] = File(...)):
    """Upload files and process them."""
    file_paths = []
    for file in files:
        # Save uploaded file
        path = f"./uploads/{file.filename}"
        with open(path, "wb") as f:
            f.write(await file.read())
        file_paths.append(path)

    result = await process_documents(file_paths=file_paths)
    return result
```

#### 2. Search with Document Support

**Update:** `backend/app/api/search.py`

```python
from fastapi import APIRouter
from app.agents.search_agent import run_price_search
from pydantic import BaseModel

router = APIRouter(prefix="/api/search", tags=["search"])

class PriceSearchRequest(BaseModel):
    description: str
    unit: str = "kom"
    quantity: float | None = None
    reference_documents: list[str] = []  # PDF, Excel files
    generate_report: bool = False
    report_format: str = "xlsx"  # or "docx"

@router.post("/price")
async def search_price(request: PriceSearchRequest):
    """Search prices with optional document support."""
    # If reference documents provided, agent can extract data from them
    enhanced_description = request.description

    if request.reference_documents:
        enhanced_description += f"\n\nReference documents available: {', '.join(request.reference_documents)}"

    result = await run_price_search(
        description=enhanced_description,
        unit=request.unit,
        quantity=request.quantity,
    )

    # Generate report if requested
    if request.generate_report:
        from app.services.skills.xlsx_skill import create_excel_file

        sheets = {
            "Quotes": [
                ["Vendor", "Product", "Unit Price", "Currency", "Confidence"],
                *[[
                    q.vendor, q.product_name, str(q.unit_price),
                    q.currency, str(q.confidence)
                ] for q in result.quotes]
            ]
        }

        report_path = f"./reports/search_result_{int(time.time())}.{request.report_format}"
        create_excel_file(report_path, sheets)

        result.report_file = report_path

    return result
```

## React/Frontend Examples

### Example: Upload and Process

```jsx
async function processDocuments() {
  const formData = new FormData();
  const files = document.getElementById('fileInput').files;

  for (let file of files) {
    formData.append('files', file);
  }

  const response = await fetch('/api/documents/upload-and-process', {
    method: 'POST',
    body: formData,
  });

  const result = await response.json();
  console.log('Processing result:', result);

  // Display extractions
  result.extractions.forEach(extraction => {
    console.log(`${extraction.file_type}: ${extraction.summary}`);
    console.log(`Key findings:`, extraction.key_findings);
  });
}
```

### Example: Search with Document Reference

```jsx
async function searchWithDocuments() {
  const response = await fetch('/api/search/price', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      description: "Search for ceramic tiles - compare with attached spec",
      unit: "m²",
      quantity: 50,
      reference_documents: ["./uploads/spec_sheet.pdf"],
      generate_report: true,
      report_format: "xlsx"
    })
  });

  const result = await response.json();

  // Download report if generated
  if (result.report_file) {
    const link = document.createElement('a');
    link.href = result.report_url;
    link.download = result.report_file.split('/').pop();
    link.click();
  }

  return result;
}
```

## Command-Line Examples

### Process PDF and Extract Data

```bash
python -c "
import asyncio
from app.agents.document_processor_agent import process_documents

async def main():
    result = await process_documents(
        file_paths=['./data/supplier_catalog.pdf'],
        analysis_prompt='Extract all product prices'
    )
    print(f'Processed: {result.documents_processed} documents')
    for extraction in result.extractions:
        print(f'  - {extraction.file_type}: {extraction.summary}')

asyncio.run(main())
"
```

### Search with Generated Report

```bash
python -c "
import asyncio
import json
from app.agents.search_agent import run_price_search

async def main():
    result = await run_price_search(
        description='Ceramic tiles 30x30cm',
        unit='m²',
        quantity=50,
    )

    # Print results
    print(f'Found {len(result.quotes)} quotes')
    if result.best_quote:
        print(f'Best: {result.best_quote.vendor} @ {result.best_quote.unit_price} {result.best_quote.currency}')

    # Save as JSON
    with open('price_search_result.json', 'w') as f:
        json.dump(result.model_dump(), f, indent=2)

asyncio.run(main())
"
```

## Workflow Examples

### Workflow 1: Supplier Onboarding

```
1. Upload supplier PDF catalog → extract products
2. Extract prices and specs → store in database
3. Create comparison Excel → against existing suppliers
4. Generate report → PDF summary
```

### Workflow 2: Quote Comparison

```
1. Receive PDF spec from client
2. Extract requirements
3. Search suppliers (already integrated)
4. Compare against PDF spec
5. Create Excel comparison
6. Generate Word report with recommendations
```

### Workflow 3: Price Tracking

```
1. Read last month's Excel pricing data
2. Search current supplier prices
3. Create new Excel with comparison
4. Calculate price changes
5. Alert if prices changed >5%
```

## Error Handling Examples

```python
from app.agents.document_processor_agent import process_documents

async def safe_process_documents(file_paths):
    try:
        result = await process_documents(file_paths)
        return {
            "success": True,
            "data": result.model_dump()
        }
    except FileNotFoundError as e:
        return {
            "success": False,
            "error": f"File not found: {e}",
            "code": "FILE_NOT_FOUND"
        }
    except Exception as e:
        logger.error(f"Document processing error: {e}")
        return {
            "success": False,
            "error": "Failed to process documents",
            "code": "PROCESSING_ERROR"
        }
```

## Performance Considerations

### Large PDF Processing

```python
# For large PDFs, limit page range
result = extract_pdf_text(
    file_path="large_document.pdf",
    page_range=(0, 10)  # Only read first 10 pages
)
```

### Excel Sheet Selection

```python
# For large Excel files, read specific sheets
data = read_excel_sheet(
    file_path="large_spreadsheet.xlsx",
    sheet_name="Pricing"  # Only read this sheet
)
```

## Integration with Existing Workflow

Your current flow:
```
User Input → Search Agent → Extract Prices → Return Results
```

New flow:
```
User Input + Documents → Search Agent + Skills → Extract from Docs + Web → Compare → Return Results + Report
```

The skills add capability without breaking existing functionality.

---

Ready to integrate into your API! Start with the endpoint examples above.
