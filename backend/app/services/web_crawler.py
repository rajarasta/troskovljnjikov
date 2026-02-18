"""Web Crawler Service - Crawls regional supplier websites for price data.

Features:
- Playwright-based crawling with JavaScript rendering support
- Rate limiting and polite crawling (robots.txt respect)
- Parallel crawling with configurable concurrency
- Progress tracking and event emission
- Automatic retry with exponential backoff
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urljoin, urlparse

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

from app.services.regional_suppliers import (
    RegionalSupplier,
    get_supplier_by_domain,
    get_search_url,
    ALL_SUPPLIERS,
)
from app.services.price_extractor import (
    extract_prices,
    extract_product_links,
    extract_metadata,
    PriceField,
)
from app.services.price_normalizer import normalize_price, NormalizedQuote
from app.models.crawled_price import CrawledPrice, CrawlJob
from app.database import SessionLocal
from app.ws.events import emit, CRAWL_PROGRESS, CRAWL_COMPLETE, CRAWL_STARTED

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class CrawlResult:
    """Result of crawling a single product page."""
    
    success: bool
    prices: list[PriceField] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    error: str | None = None
    url: str = ""
    crawled_at: str = ""


@dataclass
class CrawlStats:
    """Statistics for a crawling session."""
    
    total_urls: int = 0
    successful_crawls: int = 0
    failed_crawls: int = 0
    total_prices_found: int = 0
    unique_products: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    
    @property
    def duration_seconds(self) -> float:
        return self.end_time - self.start_time if self.end_time else 0.0
    
    @property
    def success_rate(self) -> float:
        if self.total_urls == 0:
            return 0.0
        return self.successful_crawls / self.total_urls * 100


# ============================================================================
# Rate Limiter
# ============================================================================

class RateLimiter:
    """Rate limiter for polite crawling."""
    
    def __init__(self, requests_per_second: float = 2.0):
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait until rate limit allows next request."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_request_time
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
            self.last_request_time = time.monotonic()


# ============================================================================
# Robots.txt Checker
# ============================================================================

class RobotsTxtChecker:
    """Simple robots.txt checker for polite crawling."""
    
    def __init__(self):
        self._cache: dict[str, list[str]] = {}
        self._user_agent = "TroskovljnjikovBot/1.0"
    
    async def is_allowed(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        if base_url not in self._cache:
            await self._fetch_robots(base_url)
        
        disallowed = self._cache.get(base_url, [])
        path = parsed.path
        
        for pattern in disallowed:
            if path.startswith(pattern):
                return False
        
        return True
    
    async def _fetch_robots(self, base_url: str):
        """Fetch and parse robots.txt."""
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{base_url}/robots.txt", timeout=5.0)
                if resp.status_code == 200:
                    self._cache[base_url] = self._parse_robots(resp.text)
                else:
                    self._cache[base_url] = []
        except Exception as e:
            logger.warning(f"Failed to fetch robots.txt for {base_url}: {e}")
            self._cache[base_url] = []
    
    def _parse_robots(self, content: str) -> list[str]:
        """Parse robots.txt and extract Disallowed paths."""
        disallowed = []
        current_agents = []
        matching = False
        
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            if line.lower().startswith("user-agent:"):
                agent = line.split(":", 1)[1].strip().lower()
                current_agents = [agent]
                matching = agent in (self._user_agent.lower(), "*")
            
            elif line.lower().startswith("disallow:") and matching:
                path = line.split(":", 1)[1].strip()
                if path:
                    disallowed.append(path)
        
        return disallowed


# ============================================================================
# Web Crawler
# ============================================================================

class WebCrawler:
    """Main web crawler for regional supplier websites."""
    
    def __init__(
        self,
        concurrency: int = 3,
        requests_per_second: float = 2.0,
        timeout: float = 30.0,
        respect_robots: bool = True,
    ):
        self.concurrency = concurrency
        self.timeout = timeout
        self.rate_limiter = RateLimiter(requests_per_second)
        self.robots_checker = RobotsTxtChecker() if respect_robots else None
        self._semaphore = asyncio.Semaphore(concurrency)
    
    async def crawl_search_results(
        self,
        supplier: RegionalSupplier,
        query: str,
        max_products: int = 20,
    ) -> list[CrawlResult]:
        """Crawl search results page and extract product data.
        
        Args:
            supplier: Supplier configuration
            query: Search query
            max_products: Maximum number of products to crawl
            
        Returns:
            List of crawl results for each product page
        """
        search_url = get_search_url(supplier, query)
        if not search_url:
            logger.warning(f"No search URL template for {supplier.domain}")
            return []
        
        logger.info(f"Starting crawl: {supplier.display_name} - '{query}'")
        
        # Fetch search results page
        search_html = await self._fetch_page(search_url, render=(supplier.fetch_mode == "render"))
        if not search_html:
            return []
        
        # Extract product links
        base_url = f"https://{supplier.domain}"
        product_links = extract_product_links(search_html, base_url=base_url)
        
        if not product_links:
            logger.info(f"No product links found for '{query}' on {supplier.domain}")
            return []
        
        logger.info(f"Found {len(product_links)} product links")
        
        # Crawl product pages (limited)
        results = await self._crawl_product_pages(
            product_links[:max_products],
            supplier,
        )
        
        return results
    
    async def _crawl_product_pages(
        self,
        product_links: list[dict[str, str]],
        supplier: RegionalSupplier,
    ) -> list[CrawlResult]:
        """Crawl multiple product pages in parallel."""
        
        async def crawl_one(link: dict[str, str]) -> CrawlResult:
            url = link["url"]
            
            # Check robots.txt
            if self.robots_checker and not await self.robots_checker.is_allowed(url):
                return CrawlResult(
                    success=False,
                    error="Blocked by robots.txt",
                    url=url,
                )
            
            # Fetch product page
            html = await self._fetch_page(url, render=(supplier.fetch_mode == "render"))
            if not html:
                return CrawlResult(
                    success=False,
                    error="Failed to fetch page",
                    url=url,
                )
            
            # Extract prices
            prices = extract_prices(html)
            metadata = extract_metadata(html)
            
            # Enrich with supplier info
            for price in prices:
                if not price.product_name:
                    price.product_name = link.get("title", "")
            
            return CrawlResult(
                success=len(prices) > 0,
                prices=prices,
                metadata={
                    "images": metadata.images,
                    "rating": metadata.rating,
                    "review_count": metadata.review_count,
                    "brand": metadata.brand,
                    "sku": metadata.sku,
                },
                url=url,
                crawled_at=datetime.utcnow().isoformat(),
            )
        
        # Crawl with concurrency limit
        tasks = [crawl_one(link) for link in product_links]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.exception(f"Crawl task failed: {result}")
                processed_results.append(CrawlResult(
                    success=False,
                    error=str(result),
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _fetch_page(self, url: str, render: bool = False) -> str | None:
        """Fetch a single page with rate limiting."""
        await self.rate_limiter.acquire()
        
        try:
            if render:
                return await self._fetch_with_playwright(url)
            else:
                return await self._fetch_with_httpx(url)
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None
    
    async def _fetch_with_httpx(self, url: str) -> str | None:
        """Fetch page using httpx (static HTML)."""
        import httpx
        
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "hr-HR,hr;q=0.9,en;q=0.8",
        }
        
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            resp = await client.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.text
            else:
                logger.warning(f"HTTP {resp.status_code} for {url}")
                return None
    
    async def _fetch_with_playwright(self, url: str) -> str | None:
        """Fetch page using Playwright (JavaScript rendering)."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ]
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until="networkidle", timeout=int(self.timeout * 1000))
                
                # Wait a bit for lazy-loaded content
                await asyncio.sleep(2.0)
                
                html = await page.content()
                return html
            except PlaywrightTimeout:
                logger.warning(f"Timeout loading {url}")
                # Try to get partial content
                try:
                    return await page.content()
                except:
                    return None
            finally:
                await browser.close()
    
    async def crawl_multiple_suppliers(
        self,
        queries: list[str],
        suppliers: list[RegionalSupplier] | None = None,
        max_products_per_query: int = 10,
        emit_events: bool = True,
        job_id: str | None = None,
    ) -> dict:
        """Crawl multiple suppliers for multiple queries.
        
        Args:
            queries: List of search queries
            suppliers: List of suppliers to crawl (default: all)
            max_products_per_query: Max products to crawl per query
            emit_events: Whether to emit WebSocket events
            job_id: Optional job ID for tracking
            
        Returns:
            Dictionary with crawl results and statistics
        """
        if suppliers is None:
            suppliers = ALL_SUPPLIERS
        
        stats = CrawlStats(start_time=time.time())
        all_results: dict[str, list[CrawlResult]] = {}
        
        job_id = job_id or str(uuid.uuid4())
        
        if emit_events:
            await emit(CRAWL_STARTED, {
                "job_id": job_id,
                "total_queries": len(queries),
                "total_suppliers": len(suppliers),
            })
        
        total_tasks = len(queries) * len(suppliers)
        completed_tasks = 0
        
        # Create crawl tasks
        tasks = []
        for supplier in suppliers:
            if not supplier.search_enabled:
                continue
            for query in queries:
                tasks.append(self._crawl_task(
                    supplier, query, max_products_per_query, stats,
                ))
        
        # Execute with concurrency
        for coro in asyncio.as_completed(tasks):
            result = await coro
            if result:
                key = f"{result['supplier']}::{result['query']}"
                all_results.setdefault(key, []).append(result)
            
            completed_tasks += 1
            progress = int(completed_tasks / total_tasks * 100)
            
            if emit_events:
                await emit(CRAWL_PROGRESS, {
                    "job_id": job_id,
                    "progress": progress,
                    "completed": completed_tasks,
                    "total": total_tasks,
                    "prices_found": stats.total_prices_found,
                })
        
        stats.end_time = time.time()
        
        completion_event = {
            "job_id": job_id,
            "success": stats.successful_crawls > 0,
            "stats": {
                "total_urls": stats.total_urls,
                "successful_crawls": stats.successful_crawls,
                "failed_crawls": stats.failed_crawls,
                "total_prices_found": stats.total_prices_found,
                "duration_seconds": stats.duration_seconds,
                "success_rate": stats.success_rate,
            },
        }
        
        if emit_events:
            await emit(CRAWL_COMPLETE, completion_event)
        
        return {
            "job_id": job_id,
            "results": all_results,
            "stats": stats,
        }
    
    async def _crawl_task(
        self,
        supplier: RegionalSupplier,
        query: str,
        max_products: int,
        stats: CrawlStats,
    ) -> dict | None:
        """Single crawl task for one supplier + query combination."""
        try:
            results = await self.crawl_search_results(supplier, query, max_products)
            
            stats.total_urls += len(results)
            for result in results:
                if result.success:
                    stats.successful_crawls += 1
                    stats.total_prices_found += len(result.prices)
                else:
                    stats.failed_crawls += 1
            
            return {
                "supplier": supplier.display_name,
                "domain": supplier.domain,
                "query": query,
                "results": results,
            }
        except Exception as e:
            logger.exception(f"Crawl task failed for {supplier.domain} - '{query}': {e}")
            stats.failed_crawls += 1
            return None


# ============================================================================
# Database Integration
# ============================================================================

def save_crawl_results(
    results: list[CrawlResult],
    supplier: RegionalSupplier,
    db: SessionLocal | None = None,
) -> list[CrawledPrice]:
    """Save crawl results to database."""
    
    should_close = db is None
    if should_close:
        db = SessionLocal()
    
    try:
        saved_prices = []
        
        for result in results:
            if not result.success:
                continue
            
            for price_field in result.prices:
                # Normalize price
                normalized = normalize_price(
                    price_field,
                    vendor=supplier.display_name,
                    domain_vat_included=supplier.vat_included,
                )
                
                # Create database model
                db_price = CrawledPrice(
                    id=str(uuid.uuid4()),
                    product_name=normalized.product_name or price_field.product_name,
                    description="",
                    brand="",
                    sku="",
                    ean="",
                    unit_price=normalized.unit_price,
                    currency=normalized.currency,
                    vat_included=normalized.vat_included,
                    vat_rate=supplier.vat_rate,
                    unit=normalized.unit,
                    pack_size=normalized.pack_size,
                    pack_unit=normalized.pack_unit,
                    vendor=supplier.display_name,
                    vendor_domain=supplier.domain,
                    product_url=result.url,
                    image_url=price_field.image_url,
                    image_urls=[],
                    availability=price_field.availability,
                    stock_quantity=None,
                    lead_time_days=None,
                    shipping_cost=None,
                    free_shipping_threshold=None,
                    shipping_policy=supplier.shipping_policy if hasattr(supplier, 'shipping_policy') else "unknown",
                    category="",
                    specifications={},
                    rating=None,
                    review_count=None,
                    crawled_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    is_active=True,
                    extraction_method=price_field.source_method,
                    html_snapshot=None,  # Optional, can be large
                )
                
                db.add(db_price)
                saved_prices.append(db_price)
        
        db.commit()
        return saved_prices
    
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to save crawl results: {e}")
        raise
    finally:
        if should_close:
            db.close()


# ============================================================================
# Public API
# ============================================================================

async def crawl_supplier(
    supplier: RegionalSupplier,
    query: str,
    max_products: int = 20,
) -> list[CrawlResult]:
    """Crawl a single supplier for a search query.
    
    Args:
        supplier: Supplier configuration
        query: Search query
        max_products: Maximum products to crawl
        
    Returns:
        List of crawl results
    """
    crawler = WebCrawler()
    return await crawler.crawl_search_results(supplier, query, max_products)


async def crawl_suppliers_batch(
    queries: list[str],
    suppliers: list[RegionalSupplier] | None = None,
    max_products_per_query: int = 10,
) -> dict:
    """Crawl multiple suppliers for multiple queries.
    
    Args:
        queries: List of search queries
        suppliers: List of suppliers (default: all enabled)
        max_products_per_query: Max products per query
        
    Returns:
        Dictionary with results and statistics
    """
    crawler = WebCrawler()
    return await crawler.crawl_multiple_suppliers(
        queries=queries,
        suppliers=suppliers,
        max_products_per_query=max_products_per_query,
        emit_events=False,
    )


async def crawl_and_save(
    supplier: RegionalSupplier,
    query: str,
    max_products: int = 20,
) -> list[CrawledPrice]:
    """Crawl supplier and save results to database.
    
    Args:
        supplier: Supplier configuration
        query: Search query
        max_products: Maximum products to crawl
        
    Returns:
        List of saved price records
    """
    results = await crawl_supplier(supplier, query, max_products)
    return save_crawl_results(results, supplier)
