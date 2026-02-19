"""Articles CRUD Router — manage the persistent article catalog."""
from __future__ import annotations

import csv
import io
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pricing_pipeline import Article

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class ArticleCreate(BaseModel):
    id: str | None = None
    name: str
    description: str = ""
    unit: str = "kom"
    net_price: float | None = None
    currency: str = "EUR"
    vat_rate: float = 0.25
    supplier: str = ""
    category: str = ""
    sku: str = ""
    ean: str = ""
    pack_qty: float | None = None


class ArticleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    unit: str | None = None
    net_price: float | None = None
    currency: str | None = None
    vat_rate: float | None = None
    supplier: str | None = None
    category: str | None = None
    sku: str | None = None
    ean: str | None = None
    pack_qty: float | None = None


class ArticleResponse(BaseModel):
    id: str
    name: str
    description: str
    unit: str
    net_price: float | None
    currency: str
    vat_rate: float
    supplier: str
    category: str
    sku: str
    ean: str
    pack_qty: float | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/articles", response_model=list[ArticleResponse])
async def list_articles(
    q: str = "",
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List articles, optionally filtered by name/description search."""
    query = db.query(Article)
    if q:
        pattern = f"%{q}%"
        from sqlalchemy import func, or_

        query = query.filter(
            or_(
                func.lower(Article.name).like(pattern.lower()),
                func.lower(Article.description).like(pattern.lower()),
            )
        )
    return query.offset(offset).limit(limit).all()


@router.get("/articles/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: str, db: Session = Depends(get_db)):
    """Get a single article by ID."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.post("/articles", response_model=ArticleResponse, status_code=201)
async def create_article(body: ArticleCreate, db: Session = Depends(get_db)):
    """Create a new article."""
    article_id = body.id or str(uuid.uuid4())

    existing = db.query(Article).filter(Article.id == article_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Article ID already exists")

    article = Article(
        id=article_id,
        name=body.name,
        description=body.description,
        unit=body.unit,
        net_price=body.net_price,
        currency=body.currency,
        vat_rate=body.vat_rate,
        supplier=body.supplier,
        category=body.category,
        sku=body.sku,
        ean=body.ean,
        pack_qty=body.pack_qty,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


@router.put("/articles/{article_id}", response_model=ArticleResponse)
async def update_article(
    article_id: str, body: ArticleUpdate, db: Session = Depends(get_db)
):
    """Update an existing article."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(article, key, value)

    db.commit()
    db.refresh(article)
    return article


@router.delete("/articles/{article_id}")
async def delete_article(article_id: str, db: Session = Depends(get_db)):
    """Delete an article."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    db.delete(article)
    db.commit()
    return {"detail": "Article deleted"}


@router.post("/articles/import-csv")
async def import_articles_csv(
    file: UploadFile = File(...), db: Session = Depends(get_db)
):
    """Bulk import articles from a CSV file.

    Expected CSV columns (header row required):
    id, name, description, unit, net_price, currency, vat_rate,
    supplier, category, sku, ean, pack_qty

    At minimum: name is required. Missing id will be auto-generated.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files accepted")

    content = await file.read()
    text = content.decode("utf-8-sig")  # handle BOM
    reader = csv.DictReader(io.StringIO(text))

    imported = 0
    skipped = 0

    for row in reader:
        name = (row.get("name") or row.get("naziv") or "").strip()
        if not name:
            skipped += 1
            continue

        article_id = (
            row.get("id") or row.get("sifra") or row.get("code") or str(uuid.uuid4())
        )

        # Skip if already exists
        existing = db.query(Article).filter(Article.id == article_id).first()
        if existing:
            skipped += 1
            continue

        net_price = _parse_float(row.get("net_price") or row.get("cijena"))

        article = Article(
            id=article_id,
            name=name,
            description=(row.get("description") or row.get("opis") or "").strip(),
            unit=(row.get("unit") or row.get("jm") or "kom").strip(),
            net_price=net_price,
            currency=(row.get("currency") or "EUR").strip(),
            vat_rate=_parse_float(row.get("vat_rate")) or 0.25,
            supplier=(row.get("supplier") or row.get("dobavljac") or "").strip(),
            category=(row.get("category") or row.get("kategorija") or "").strip(),
            sku=(row.get("sku") or row.get("sifra_artikla") or "").strip(),
            ean=(row.get("ean") or "").strip(),
            pack_qty=_parse_float(row.get("pack_qty") or row.get("pakiranje")),
        )
        db.add(article)
        imported += 1

    db.commit()

    return {
        "imported": imported,
        "skipped": skipped,
        "total_in_catalog": db.query(Article).count(),
    }


@router.post("/articles/import-xlsx")
async def import_articles_xlsx(
    file: UploadFile = File(...), db: Session = Depends(get_db)
):
    """Bulk import articles from a Pantheon ExportIdent XLSX file.

    Recognises Pantheon column headers like:
    - Šifra (acIdent) → id/sku
    - Naziv (acName) → name
    - Primarni dobavljač (acSupplier) → supplier
    - Glavna mjerna jedinica (acUM) → unit
    - Dobavljačeva cijena (anPriceSupp) → net_price (preferred)
    - Prodajna cijena (anRTPrice) → fallback net_price
    - Valuta (acCurrency) → currency
    - Primarna klasifikacija (acClassif) → category
    - Dobavljačeva šifra (acCode) → sku
    """
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only XLSX files accepted")

    import openpyxl

    content = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not rows:
        raise HTTPException(status_code=400, detail="Empty spreadsheet")

    # Map header names to column indices
    raw_headers = [str(h or "").strip().lower() for h in rows[0]]
    col_map = _build_pantheon_col_map(raw_headers)

    if "name" not in col_map:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot find name column. Headers: {rows[0][:10]}",
        )

    imported = 0
    skipped = 0

    for row in rows[1:]:
        name = _cell_str(row, col_map.get("name"))
        if not name:
            skipped += 1
            continue

        article_id = _cell_str(row, col_map.get("id")) or str(uuid.uuid4())
        article_id = article_id.strip()

        existing = db.query(Article).filter(Article.id == article_id).first()
        if existing:
            skipped += 1
            continue

        # Prefer supplier price over retail price (retail often 0 in Pantheon)
        net_price = (
            _cell_float(row, col_map.get("supplier_price"))
            or _cell_float(row, col_map.get("net_price"))
            or _cell_float(row, col_map.get("ws_price"))
        )

        article = Article(
            id=article_id,
            name=name,
            description="",
            unit=_cell_str(row, col_map.get("unit")) or "kom",
            net_price=net_price,
            currency=_cell_str(row, col_map.get("currency")) or "EUR",
            vat_rate=0.25,
            supplier=_cell_str(row, col_map.get("supplier")) or "",
            category=_cell_str(row, col_map.get("category")) or "",
            sku=_cell_str(row, col_map.get("sku")) or "",
            ean="",
            pack_qty=None,
        )
        db.add(article)
        imported += 1

    db.commit()

    return {
        "imported": imported,
        "skipped": skipped,
        "total_in_catalog": db.query(Article).count(),
    }


def _parse_float(value: str | None) -> float | None:
    """Parse a float from a string, handling Croatian decimals."""
    if not value:
        return None
    value = value.strip().replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Pantheon XLSX helpers
# ---------------------------------------------------------------------------

# Map of known Pantheon header substrings → canonical field names
_PANTHEON_HEADER_MAP: list[tuple[str, str]] = [
    ("šifra", "id"),
    ("acident", "id"),
    ("naziv", "name"),
    ("acname", "name"),
    ("dobavljač (acsupplier)", "supplier"),
    ("primarni dobavljač", "supplier"),
    ("acsupplier", "supplier"),
    ("dobavljačeva šifra", "sku"),
    ("accode", "sku"),
    ("mjerna jedinica", "unit"),
    ("acum", "unit"),
    ("dobavljačeva cijena", "supplier_price"),
    ("anpricesupp", "supplier_price"),
    ("prodajna cijena", "net_price"),
    ("anrtprice", "net_price"),
    ("veleprod.cijena1", "ws_price"),
    ("anwsprice)", "ws_price"),
    ("valuta (accurrency)", "currency"),
    ("accurrency)", "currency"),
    ("klasifikacija", "category"),
    ("acclassif)", "category"),
]


def _build_pantheon_col_map(headers: list[str]) -> dict[str, int]:
    """Match Pantheon header names to canonical field names, return {field: col_idx}."""
    col_map: dict[str, int] = {}
    for idx, header in enumerate(headers):
        if not header:
            continue
        h = header.lower().strip()
        for pattern, field in _PANTHEON_HEADER_MAP:
            if pattern in h and field not in col_map:
                col_map[field] = idx
                break
    return col_map


def _cell_str(row: tuple, idx: int | None) -> str:
    """Safely extract a string from a row tuple."""
    if idx is None or idx >= len(row) or row[idx] is None:
        return ""
    return str(row[idx]).strip()


def _cell_float(row: tuple, idx: int | None) -> float | None:
    """Safely extract a float from a row tuple."""
    if idx is None or idx >= len(row) or row[idx] is None:
        return None
    val = row[idx]
    if isinstance(val, (int, float)):
        return float(val) if val != 0 else None
    try:
        return float(str(val).strip().replace(",", ".")) or None
    except (ValueError, TypeError):
        return None
