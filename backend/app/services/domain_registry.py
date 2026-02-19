"""Domain Registry - DB-backed allowlist of approved supplier domains for web price search.

Each domain has configuration for fetch mode, VAT policy, search URL patterns,
and extraction hints. The registry acts as the safety boundary — the search
agent can only access URLs that pass validation here.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from urllib.parse import urlparse

from app.database import SessionLocal
from app.models.domain import SearchDomain


@dataclass
class DomainConfig:
    """Configuration for an approved supplier domain."""

    domain: str
    display_name: str
    allowed_paths: list[str] = field(default_factory=lambda: ["/"])
    fetch_mode: str = "static"  # "static" | "render"
    vat_included: bool | None = True  # True / False / None (unknown)
    shipping_policy: str = "unknown"  # "free_over_threshold" | "per_order" | "unknown"
    search_url_template: str | None = None  # e.g. "https://domain/search?q={query}"
    currency: str = "EUR"
    locale: str = "hr"


# ---------------------------------------------------------------------------
# In-memory cache (refreshed on writes via invalidate_cache)
# ---------------------------------------------------------------------------

_cache_lock = threading.Lock()
_cached_domains: dict[str, DomainConfig] | None = None


def _to_config(row: SearchDomain) -> DomainConfig:
    return DomainConfig(
        domain=row.domain,
        display_name=row.display_name,
        allowed_paths=["/"],
        fetch_mode=row.fetch_mode or "static",
        vat_included=row.vat_included,
        shipping_policy=row.shipping_policy or "unknown",
        search_url_template=row.search_url_template,
        currency=row.currency or "EUR",
        locale=row.locale or "hr",
    )


def _load_domains() -> dict[str, DomainConfig]:
    """Load enabled domains from DB into a dict keyed by domain hostname."""
    db = SessionLocal()
    try:
        rows = db.query(SearchDomain).filter(SearchDomain.enabled == True).all()  # noqa: E712
        result: dict[str, DomainConfig] = {}
        for row in rows:
            config = _to_config(row)
            result[row.domain] = config
            # Also register www variant if not already present
            if row.domain.startswith("www."):
                bare = row.domain[4:]
                if bare not in result:
                    result[bare] = config
            else:
                www = f"www.{row.domain}"
                if www not in result:
                    result[www] = config
        return result
    finally:
        db.close()


def _get_cache() -> dict[str, DomainConfig]:
    global _cached_domains
    with _cache_lock:
        if _cached_domains is None:
            _cached_domains = _load_domains()
        return _cached_domains


def invalidate_cache() -> None:
    """Clear the in-memory cache. Called after domain CRUD operations."""
    global _cached_domains
    with _cache_lock:
        _cached_domains = None


# ---------------------------------------------------------------------------
# Public API (same signatures as before)
# ---------------------------------------------------------------------------

def get_domain_config(url: str) -> DomainConfig | None:
    """Return the DomainConfig for a URL if it's on the allowlist, else None."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    config = _get_cache().get(hostname)
    if config is None:
        return None
    path = parsed.path or "/"
    if any(path.startswith(ap) for ap in config.allowed_paths):
        return config
    return None


def is_approved(url: str) -> bool:
    """Check if a URL is on the approved domain list."""
    return get_domain_config(url) is not None


def get_all_domains() -> list[DomainConfig]:
    """Return all unique enabled domain configs (deduplicated by display_name)."""
    seen: set[str] = set()
    result: list[DomainConfig] = []
    for config in _get_cache().values():
        if config.display_name not in seen:
            seen.add(config.display_name)
            result.append(config)
    return result


def get_search_url(domain: str, query: str) -> str | None:
    """Build a search URL for a domain using its template."""
    config = _get_cache().get(domain)
    if config is None or config.search_url_template is None:
        return None
    return config.search_url_template.format(query=query)
