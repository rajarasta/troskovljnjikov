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
