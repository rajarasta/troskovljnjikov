"""Catalog Service — deterministic article catalog lookup against SQLite.

Provides fuzzy keyword search and exact ID lookup for the Article table.
Used as tools for the article_context agent and by the orchestrator.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, or_

from app.database import SessionLocal
from app.models.pricing_pipeline import Article

logger = logging.getLogger(__name__)


def _article_to_dict(a: Article) -> dict[str, Any]:
    """Convert an Article ORM object to a plain dict."""
    return {
        "id": a.id,
        "name": a.name,
        "description": a.description or "",
        "unit": a.unit,
        "net_price": a.net_price,
        "currency": a.currency,
        "vat_rate": a.vat_rate,
        "supplier": a.supplier or "",
        "category": a.category or "",
        "sku": a.sku or "",
        "ean": a.ean or "",
        "pack_qty": a.pack_qty,
    }


def catalog_lookup(query: str, top_k: int = 10) -> list[dict[str, Any]]:
    """Multi-strategy search on the article catalog.

    Strategy 1: Exact ID/SKU match (highest priority)
    Strategy 2: All keywords match name/description/category/id/sku (AND)
    Strategy 3: Any keyword matches (OR) — broader fallback

    Returns list of article dicts, deduplicated, up to top_k.
    """
    if not query or not query.strip():
        return []

    query_clean = query.strip()
    keywords = query_clean.lower().split()[:5]

    db = SessionLocal()
    try:
        results: list[Article] = []
        seen_ids: set[str] = set()

        def _add(articles: list[Article]) -> None:
            for a in articles:
                if a.id not in seen_ids:
                    seen_ids.add(a.id)
                    results.append(a)

        # Strategy 1: Exact ID or SKU match
        exact = db.query(Article).filter(
            or_(
                Article.id == query_clean,
                Article.sku == query_clean,
            )
        ).all()
        _add(exact)

        # Strategy 2: All keywords AND match on name/description/category/id/sku
        if len(results) < top_k:
            q = db.query(Article)
            for kw in keywords:
                pattern = f"%{kw}%"
                q = q.filter(
                    or_(
                        func.lower(Article.name).like(pattern),
                        func.lower(Article.description).like(pattern),
                        func.lower(Article.category).like(pattern),
                        func.lower(Article.id).like(pattern),
                        func.lower(Article.sku).like(pattern),
                    )
                )
            _add(q.limit(top_k).all())

        # Strategy 3: OR match (broader) if too few results
        if len(results) < top_k and len(keywords) > 1:
            conditions = []
            for kw in keywords:
                pattern = f"%{kw}%"
                conditions.extend([
                    func.lower(Article.name).like(pattern),
                    func.lower(Article.id).like(pattern),
                    func.lower(Article.sku).like(pattern),
                ])
            broader = db.query(Article).filter(or_(*conditions)).limit(top_k * 2).all()
            _add(broader)

        return [_article_to_dict(a) for a in results[:top_k]]
    except Exception:
        logger.exception("catalog_lookup failed for query: %s", query)
        return []
    finally:
        db.close()


def catalog_get(article_id: str) -> dict[str, Any] | None:
    """Get a single article by ID."""
    db = SessionLocal()
    try:
        a = db.query(Article).filter(Article.id == article_id).first()
        return _article_to_dict(a) if a else None
    except Exception:
        logger.exception("catalog_get failed for id: %s", article_id)
        return None
    finally:
        db.close()


def catalog_count() -> int:
    """Return the total number of articles in the catalog."""
    db = SessionLocal()
    try:
        return db.query(Article).count()
    except Exception:
        return 0
    finally:
        db.close()
