"""Web Fetcher - layered HTTP fetching with static (httpx) and rendered (Playwright) modes.

Provides a simple caching layer (15-min TTL) keyed by URL.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from app.services.domain_registry import get_domain_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class FetchResult:
    """Result of fetching a web page."""
    url: str
    final_url: str
    html: str
    text: str
    status_code: int
    fetched_at: str
    from_cache: bool = False
    fetch_mode: str = "static"  # "static" | "render"


# ---------------------------------------------------------------------------
# In-memory LRU cache (URL -> FetchResult, 15 min TTL)
# Implements thread-safe LRU eviction to prevent unbounded memory growth
# ---------------------------------------------------------------------------

@dataclass
class _CacheEntry:
    """Cache entry with timestamp for TTL validation."""
    timestamp: float
    result: FetchResult


class _LRUCache:
    """Thread-safe LRU cache with TTL support."""

    def __init__(self, max_size: int = 100, ttl: float = 900):
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl
        self._lock = threading.RLock()

    def get(self, url: str) -> FetchResult | None:
        """Get cached result if valid (not expired)."""
        with self._lock:
            if url not in self._cache:
                return None

            entry = self._cache[url]
            # Check if expired
            if time.time() - entry.timestamp > self._ttl:
                del self._cache[url]
                return None

            # Move to end (mark as recently used)
            self._cache.move_to_end(url)

            return FetchResult(
                url=entry.result.url,
                final_url=entry.result.final_url,
                html=entry.result.html,
                text=entry.result.text,
                status_code=entry.result.status_code,
                fetched_at=entry.result.fetched_at,
                from_cache=True,
                fetch_mode=entry.result.fetch_mode,
            )

    def put(self, url: str, result: FetchResult) -> None:
        """Put result in cache, evicting oldest if over limit."""
        with self._lock:
            # Remove if already exists (will re-add at end)
            if url in self._cache:
                del self._cache[url]

            # Add new entry
            self._cache[url] = _CacheEntry(timestamp=time.time(), result=result)

            # Evict oldest item if over size limit
            if len(self._cache) > self._max_size:
                oldest_url, _ = self._cache.popitem(last=False)
                logger.debug(f"Evicted cache entry for {oldest_url} (size limit reached)")

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)


_cache = _LRUCache(max_size=100, ttl=900)  # 100 URLs, 15 min TTL


def _cache_get(url: str) -> FetchResult | None:
    """Get cached result if available and not expired."""
    return _cache.get(url)


def _cache_put(url: str, result: FetchResult) -> None:
    """Put result in cache."""
    _cache.put(url, result)


# ---------------------------------------------------------------------------
# Static fetch (httpx)
# ---------------------------------------------------------------------------

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


async def fetch_static(url: str, timeout: float = 15.0) -> FetchResult:
    """Fetch a page using httpx (no JS rendering)."""
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=timeout,
        headers={"User-Agent": _USER_AGENT},
    ) as client:
        resp = await client.get(url)
        html = resp.text
        soup = BeautifulSoup(html, "lxml")
        # Remove script/style noise
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return FetchResult(
            url=url,
            final_url=str(resp.url),
            html=html,
            text=text,
            status_code=resp.status_code,
            fetched_at=datetime.utcnow().isoformat(),
            fetch_mode="static",
        )


# ---------------------------------------------------------------------------
# Rendered fetch (Playwright) - optional
# ---------------------------------------------------------------------------

async def fetch_rendered(url: str, timeout: float = 30.0) -> FetchResult:
    """Fetch a page using Playwright headless browser (JS rendering)."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("Playwright not installed, falling back to static fetch")
        return await fetch_static(url, timeout)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=_USER_AGENT)
        try:
            await page.goto(url, wait_until="networkidle", timeout=int(timeout * 1000))
            html = await page.content()
            final_url = page.url
        finally:
            await browser.close()

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return FetchResult(
        url=url,
        final_url=final_url,
        html=html,
        text=text,
        status_code=200,
        fetched_at=datetime.utcnow().isoformat(),
        fetch_mode="render",
    )


# ---------------------------------------------------------------------------
# Auto-mode fetch (tries static, falls back to render if needed)
# ---------------------------------------------------------------------------

def _looks_like_js_only(html: str) -> bool:
    """Heuristic: page has very little text content, likely needs JS rendering."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(strip=True)
    return len(text) < 200


async def fetch_page(url: str, mode: str = "auto") -> FetchResult:
    """Fetch a page with caching and automatic mode selection.

    Args:
        url: The URL to fetch.
        mode: "static", "render", or "auto" (tries static first, falls back to render).

    Returns:
        FetchResult with HTML, extracted text, and metadata.
    """
    # Check cache first
    cached = _cache_get(url)
    if cached is not None:
        return cached

    # Determine fetch mode
    if mode == "auto":
        config = get_domain_config(url)
        if config and config.fetch_mode == "render":
            mode = "render"
        else:
            mode = "static"

    if mode == "render":
        result = await fetch_rendered(url)
    else:
        result = await fetch_static(url)
        # If static fetch returned JS-only content, try render
        if _looks_like_js_only(result.html):
            logger.info("Static fetch returned JS-only content for %s, trying render", url)
            try:
                result = await fetch_rendered(url)
            except Exception:
                logger.warning("Render fallback failed for %s, using static result", url)

    _cache_put(url, result)
    return result
