"""Search domain management endpoints — CRUD for supplier websites."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.domain import SearchDomain
from app.schemas.domain import DomainCreate, DomainUpdate, DomainSchema
from app.services.domain_registry import invalidate_cache

router = APIRouter()


@router.get("/domains", response_model=list[DomainSchema])
def list_domains(db: Session = Depends(get_db)):
    return db.query(SearchDomain).order_by(SearchDomain.is_default.desc(), SearchDomain.display_name).all()


@router.post("/domains", response_model=DomainSchema, status_code=201)
def create_domain(body: DomainCreate, db: Session = Depends(get_db)):
    # Normalize domain: strip protocol and trailing slash
    domain = body.domain.strip().rstrip("/")
    if "://" in domain:
        domain = domain.split("://", 1)[1]

    existing = db.query(SearchDomain).filter(SearchDomain.domain == domain).first()
    if existing:
        raise HTTPException(409, f"Domain '{domain}' already exists")

    record = SearchDomain(
        id=str(uuid.uuid4()),
        domain=domain,
        display_name=body.display_name,
        search_url_template=body.search_url_template,
        fetch_mode=body.fetch_mode,
        vat_included=body.vat_included,
        shipping_policy=body.shipping_policy,
        currency=body.currency,
        locale=body.locale,
        enabled=body.enabled,
        is_default=False,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    invalidate_cache()
    return record


@router.put("/domains/{domain_id}", response_model=DomainSchema)
def update_domain(domain_id: str, body: DomainUpdate, db: Session = Depends(get_db)):
    record = db.query(SearchDomain).filter(SearchDomain.id == domain_id).first()
    if not record:
        raise HTTPException(404, "Domain not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    invalidate_cache()
    return record


@router.delete("/domains/{domain_id}", status_code=204)
def delete_domain(domain_id: str, db: Session = Depends(get_db)):
    record = db.query(SearchDomain).filter(SearchDomain.id == domain_id).first()
    if not record:
        raise HTTPException(404, "Domain not found")
    if record.is_default:
        raise HTTPException(403, "Cannot delete default domains. Disable them instead.")
    db.delete(record)
    db.commit()
    invalidate_cache()
