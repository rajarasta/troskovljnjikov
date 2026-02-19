import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite needs this
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    import app.models.preset  # noqa: F401  — register Preset table
    import app.models.pricing_pipeline  # noqa: F401  — register Article + PricingRun tables
    import app.models.domain  # noqa: F401  — register SearchDomain table
    Base.metadata.create_all(bind=engine)


def seed_default_presets():
    """Insert default presets if they don't exist."""
    from app.models.preset import Preset

    db = SessionLocal()
    try:
        existing = db.query(Preset).filter(Preset.is_default == True).count()  # noqa: E712
        if existing > 0:
            return
        data_path = Path(__file__).parent / "data" / "default_presets.json"
        presets = json.loads(data_path.read_text())
        for p in presets:
            db.add(Preset(**p))
        db.commit()
    finally:
        db.close()


def seed_default_domains():
    """Insert default search domains if none exist."""
    import uuid
    from app.models.domain import SearchDomain

    _DEFAULTS = [
        {
            "domain": "www.bauhaus.hr",
            "display_name": "Bauhaus HR",
            "search_url_template": "https://www.bauhaus.hr/catalogsearch/result/?q={query}",
            "fetch_mode": "static",
            "vat_included": True,
            "shipping_policy": "per_order",
            "currency": "EUR",
            "locale": "hr",
        },
        {
            "domain": "gradja.hr",
            "display_name": "Gradja.hr",
            "search_url_template": "https://gradja.hr/?s={query}&post_type=product",
            "fetch_mode": "static",
            "vat_included": True,
            "shipping_policy": "per_order",
            "currency": "EUR",
            "locale": "hr",
        },
        {
            "domain": "eshop.wuerth.com.hr",
            "display_name": "Würth HR",
            "search_url_template": "https://eshop.wuerth.com.hr/Search/Products?search={query}",
            "fetch_mode": "render",
            "vat_included": True,
            "shipping_policy": "free_over_threshold",
            "currency": "EUR",
            "locale": "hr",
        },
        {
            "domain": "era-commerce.hr",
            "display_name": "ERA Commerce",
            "search_url_template": "https://era-commerce.hr/?s={query}&post_type=product",
            "fetch_mode": "static",
            "vat_included": True,
            "shipping_policy": "unknown",
            "currency": "EUR",
            "locale": "hr",
        },
    ]

    db = SessionLocal()
    try:
        existing = db.query(SearchDomain).count()
        if existing > 0:
            return
        for d in _DEFAULTS:
            db.add(SearchDomain(id=str(uuid.uuid4()), is_default=True, enabled=True, **d))
        db.commit()
    finally:
        db.close()
