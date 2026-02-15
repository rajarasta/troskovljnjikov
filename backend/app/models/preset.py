from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.sqlite import JSON

from app.database import Base


class Preset(Base):
    __tablename__ = "presets"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    groups = Column(JSON, nullable=False)  # e.g. ["core", "mat_rad"]
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
