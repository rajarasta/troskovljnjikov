import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship

from app.database import Base


class ItemStatusEnum(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REFUSED = "refused"
    NEGOTIATED = "negotiated"
    EXPIRED = "expired"


class BoQFile(Base):
    __tablename__ = "boq_files"

    id = Column(String, primary_key=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, default="xlsx")
    stored_path = Column(String, nullable=True)  # path to original xlsx on disk
    file_date = Column(DateTime, nullable=True)
    sheet_count = Column(Integer, default=0)
    item_count = Column(Integer, default=0)
    project_name = Column(String, nullable=True)
    column_mapping = Column(JSON, nullable=True)
    missing_data = Column(JSON, nullable=True)
    raw_preview = Column(JSON, nullable=True)  # first N raw rows per sheet
    indexed_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("BoQItem", back_populates="file", cascade="all, delete-orphan")
    units = relationship("BoQUnit", back_populates="file", cascade="all, delete-orphan")


class BoQItem(Base):
    __tablename__ = "boq_items"

    id = Column(String, primary_key=True)
    file_id = Column(String, ForeignKey("boq_files.id"), nullable=False)
    sheet_name = Column(String, nullable=True)
    row = Column(Integer, nullable=False)
    item_number = Column(String, nullable=True)
    description = Column(Text, nullable=False)
    full_description = Column(Text, nullable=True)
    parent_item_number = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    quantity = Column(Float, default=0)
    unit_price = Column(Float, default=0)
    total = Column(Float, default=0)
    unit_id = Column(String, ForeignKey("boq_units.id"), nullable=True)
    project_name = Column(String, nullable=True)
    date = Column(String, nullable=True)

    file = relationship("BoQFile", back_populates="items")
    unit_ref = relationship("BoQUnit", foreign_keys=[unit_id])
    status_record = relationship("ItemStatus", back_populates="item", uselist=False)


class BoQUnit(Base):
    __tablename__ = "boq_units"

    id = Column(String, primary_key=True)
    file_id = Column(String, ForeignKey("boq_files.id"), nullable=False)
    sheet_name = Column(String, nullable=False)
    parent_item_number = Column(String, nullable=False)
    parent_title = Column(String, nullable=True)
    parent_description = Column(Text, nullable=True)
    start_row = Column(Integer, nullable=False)
    end_row = Column(Integer, nullable=False)
    item_ids = Column(JSON, nullable=False)
    subtotal = Column(Float, nullable=True)
    item_count = Column(Integer, default=0)

    file = relationship("BoQFile", back_populates="units")


class ItemStatus(Base):
    __tablename__ = "item_statuses"

    item_id = Column(String, ForeignKey("boq_items.id"), primary_key=True)
    status = Column(SQLEnum(ItemStatusEnum), default=ItemStatusEnum.PENDING)
    notes = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    item = relationship("BoQItem", back_populates="status_record")


class Workbook(Base):
    __tablename__ = "workbooks"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    file_path = Column(String, nullable=True)
    file_type = Column(String, default="xlsx")
    original_data = Column(JSON, nullable=False)
    working_data = Column(JSON, nullable=False)
    changes = Column(JSON, default=dict)
    column_mapping = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
