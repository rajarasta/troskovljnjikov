"""Domain Registry - allowlist of approved supplier domains for web price search.

Each domain has configuration for fetch mode, VAT policy, search URL patterns,
and extraction hints. The registry acts as the safety boundary — the search
agent can only access URLs that pass validation here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse


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
# Approved domains
# ---------------------------------------------------------------------------

APPROVED_DOMAINS: dict[str, DomainConfig] = {
    "www.bauhaus.hr": DomainConfig(
        domain="www.bauhaus.hr",
        display_name="Bauhaus HR",
        allowed_paths=["/"],
        fetch_mode="static",
        vat_included=True,
        shipping_policy="per_order",
        search_url_template="https://www.bauhaus.hr/catalogsearch/result/?q={query}",
        currency="EUR",
    ),
    "gradja.hr": DomainConfig(
        domain="gradja.hr",
        display_name="Gradja.hr",
        allowed_paths=["/"],
        fetch_mode="static",
        vat_included=True,
        shipping_policy="per_order",
        search_url_template="https://gradja.hr/?s={query}&post_type=product",
        currency="EUR",
    ),
    "www.gradja.hr": DomainConfig(
        domain="www.gradja.hr",
        display_name="Gradja.hr",
        allowed_paths=["/"],
        fetch_mode="static",
        vat_included=True,
        shipping_policy="per_order",
        search_url_template="https://gradja.hr/?s={query}&post_type=product",
        currency="EUR",
    ),
    "eshop.wuerth.com.hr": DomainConfig(
        domain="eshop.wuerth.com.hr",
        display_name="Würth HR",
        allowed_paths=["/"],
        fetch_mode="render",  # Würth eshop is JS-heavy
        vat_included=True,
        shipping_policy="free_over_threshold",
        search_url_template="https://eshop.wuerth.com.hr/Search/Products?search={query}",
        currency="EUR",
    ),
    "era-commerce.hr": DomainConfig(
        domain="era-commerce.hr",
        display_name="ERA Commerce",
        allowed_paths=["/"],
        fetch_mode="static",
        vat_included=True,
        shipping_policy="unknown",
        search_url_template="https://era-commerce.hr/?s={query}&post_type=product",
        currency="EUR",
    ),
    "www.era-commerce.hr": DomainConfig(
        domain="www.era-commerce.hr",
        display_name="ERA Commerce",
        allowed_paths=["/"],
        fetch_mode="static",
        vat_included=True,
        shipping_policy="unknown",
        search_url_template="https://www.era-commerce.hr/?s={query}&post_type=product",
        currency="EUR",
    ),
}


def get_domain_config(url: str) -> DomainConfig | None:
    """Return the DomainConfig for a URL if it's on the allowlist, else None."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    config = APPROVED_DOMAINS.get(hostname)
    if config is None:
        return None
    # Check path prefix
    path = parsed.path or "/"
    if any(path.startswith(ap) for ap in config.allowed_paths):
        return config
    return None


def is_approved(url: str) -> bool:
    """Check if a URL is on the approved domain list."""
    return get_domain_config(url) is not None


def get_all_domains() -> list[DomainConfig]:
    """Return all unique approved domain configs (deduplicated by display_name)."""
    seen: set[str] = set()
    result: list[DomainConfig] = []
    for config in APPROVED_DOMAINS.values():
        if config.display_name not in seen:
            seen.add(config.display_name)
            result.append(config)
    return result


def get_search_url(domain: str, query: str) -> str | None:
    """Build a search URL for a domain using its template."""
    config = APPROVED_DOMAINS.get(domain)
    if config is None or config.search_url_template is None:
        return None
    return config.search_url_template.format(query=query)
