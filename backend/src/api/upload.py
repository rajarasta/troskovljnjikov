from fastapi import APIRouter, UploadFile, File

from ..models.boq import ParsedBoQ
from ..parser.excel_parser import parse_excel

router = APIRouter()

# In-memory session storage for current upload
_current_boq: ParsedBoQ | None = None


def get_current_boq() -> ParsedBoQ | None:
    return _current_boq


@router.post("/upload", response_model=ParsedBoQ)
async def upload_excel(file: UploadFile = File(...)):
    global _current_boq
    content = await file.read()
    _current_boq = parse_excel(content, file.filename or "unknown.xlsx")
    return _current_boq
