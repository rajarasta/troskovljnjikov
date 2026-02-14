from fastapi import APIRouter, UploadFile, File, Query

from ..models.historic import HistoricMatch
from ..db.historic_repo import search_historic, import_boq_to_historic
from ..parser.excel_parser import parse_excel

router = APIRouter()


@router.get("/historic/search", response_model=list[HistoricMatch])
async def search_historic_units(q: str = Query(..., min_length=2), limit: int = 10):
    return await search_historic(q, limit)


@router.post("/historic/import")
async def import_historic(file: UploadFile = File(...)):
    content = await file.read()
    boq = parse_excel(content, file.filename or "unknown.xlsx")
    count = await import_boq_to_historic(boq, file.filename or "unknown.xlsx")
    return {"imported_count": count, "unit_count": len(boq.units)}
