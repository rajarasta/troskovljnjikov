from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime

from app.database import Base


class SearchDomain(Base):
    __tablename__ = "search_domains"

    id = Column(String, primary_key=True)
    domain = Column(String, nullable=False, unique=True)
    display_name = Column(String, nullable=False)
    search_url_template = Column(String, nullable=True)
    fetch_mode = Column(String, default="static")  # "static" | "render"
    vat_included = Column(Boolean, default=True)
    shipping_policy = Column(String, default="unknown")
    currency = Column(String, default="EUR")
    locale = Column(String, default="hr")
    enabled = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
