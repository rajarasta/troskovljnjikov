"""Database models for crawled price data."""
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, Float, Integer, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.database import Base


class CrawledPrice(Base):
    """Stores individual price points crawled from supplier websites."""
    
    __tablename__ = "crawled_prices"
    
    id = Column(String, primary_key=True)
    
    # Product identification
    product_name = Column(String, nullable=False)
    description = Column(Text)
    brand = Column(String, default="")
    sku = Column(String, default="")
    ean = Column(String, default="")
    
    # Pricing
    unit_price = Column(Float, nullable=False)
    currency = Column(String, default="EUR")  # EUR, HRK, RSD, BAM
    vat_included = Column(Boolean, default=True)
    vat_rate = Column(Float, default=25.0)  # Croatian PDV is 25%
    unit = Column(String, default="kom")  # kom, m², m, kg, l, etc.
    pack_size = Column(Float)  # e.g., 25.0 for 25m roll
    pack_unit = Column(String)  # m, kom, kg, etc.
    
    # Source information
    vendor = Column(String, nullable=False)
    vendor_domain = Column(String, nullable=False)
    product_url = Column(String, nullable=False)
    image_url = Column(String)
    image_urls = Column(JSON, default=list)
    
    # Availability
    availability = Column(String, default="unknown")  # in_stock, out_of_stock, low_stock
    stock_quantity = Column(Integer)
    lead_time_days = Column(Integer)
    
    # Shipping
    shipping_cost = Column(Float)
    free_shipping_threshold = Column(Float)
    shipping_policy = Column(String, default="unknown")
    
    # Product details
    category = Column(String)  # e.g., "cement", "bricks", "insulation"
    specifications = Column(JSON, default=dict)
    
    # Quality indicators
    rating = Column(Float)  # 0-5
    review_count = Column(Integer)
    
    # Crawling metadata
    crawled_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    extraction_method = Column(String, default="unknown")  # jsonld, meta, css, llm
    
    # Full HTML snapshot for debugging (optional, can be large)
    html_snapshot = Column(Text)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_vendor_domain', 'vendor_domain'),
        Index('idx_product_name', 'product_name'),
        Index('idx_category', 'category'),
        Index('idx_crawled_at', 'crawled_at'),
        Index('idx_currency', 'currency'),
        Index('idx_unit', 'unit'),
    )


class CrawlJob(Base):
    """Tracks crawling jobs and their status."""
    
    __tablename__ = "crawl_jobs"
    
    id = Column(String, primary_key=True)
    
    # Job configuration
    vendor_domain = Column(String, nullable=False)
    search_query = Column(String, nullable=False)
    category = Column(String)  # Optional category filter
    
    # Job status
    status = Column(String, default="pending")  # pending, running, completed, failed
    progress = Column(Integer, default=0)  # 0-100 percentage
    total_urls = Column(Integer, default=0)
    crawled_urls = Column(Integer, default=0)
    extracted_prices = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Results summary
    summary = Column(JSON, default=dict)


class CrawlSchedule(Base):
    """Scheduled crawling jobs for automatic price updates."""
    
    __tablename__ = "crawl_schedules"
    
    id = Column(String, primary_key=True)
    
    # Schedule configuration
    vendor_domain = Column(String, nullable=False)
    category = Column(String)  # Optional: crawl specific categories
    search_queries = Column(JSON, default=list)  # List of search terms
    
    # Timing
    cron_expression = Column(String, default="0 2 * * *")  # Daily at 2 AM
    enabled = Column(Boolean, default=True)
    last_run = Column(DateTime)
    next_run = Column(DateTime)
    
    # Statistics
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)
    avg_prices_found = Column(Float, default=0.0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, default="system")
