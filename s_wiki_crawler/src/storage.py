"""Storage layer — filesystem writes, sidecar metadata, and graph operations.

All content is stored on the filesystem as markdown files with .meta.json
sidecars. SurrealDB (via Storage MCP) stores only metadata and graph
relationships — file paths, content hashes, crawl timestamps, edges.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from src.config import CRAWL_CACHE_ROOT, MCP_STORAGE_URL
from src.crawler import mcp_call
from src.models import CrawlResult, PageMetadata

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# URL → slug / record ID helpers
# ---------------------------------------------------------------------------


def _url_to_slug(url: str) -> str:
    """Convert a URL to a filesystem-safe slug.

    Takes the URL path, strips wiki prefixes, and normalizes to a
    lowercase underscore slug suitable for filenames.

    Examples:
        https://wowpedia.fandom.com/wiki/Hogger → hogger
        https://wiki.gg/wiki/Elwynn_Forest → elwynn_forest
        https://example.com/page/Some%20Page → some_page
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    # Strip common wiki prefixes
    for prefix in ("wiki/", "w/", "page/"):
        if path.lower().startswith(prefix):
            path = path[len(prefix):]
            break

    # URL decode common patterns
    slug = path.replace("%20", "_").replace("+", "_")

    # Normalize separators to underscores
    slug = slug.replace("/", "_").replace("-", "_").replace(" ", "_")

    # Remove non-alphanumeric characters (except underscores)
    slug = re.sub(r"[^a-zA-Z0-9_]", "", slug)

    # Collapse multiple underscores
    slug = re.sub(r"_+", "_", slug).strip("_").lower()

    # Fallback for empty slugs
    if not slug:
        slug = hashlib.sha256(url.encode()).hexdigest()[:16]

    return slug


def _url_to_record_id(url: str) -> str:
    """Convert a URL to a stable SurrealDB record ID.

    Uses a SHA-256 hash prefix for uniqueness and stability — URLs can
    contain characters that are invalid in SurrealDB record IDs.
    """
    return hashlib.sha256(url.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Store page — filesystem + sidecar + graph
# ---------------------------------------------------------------------------


async def store_page(
    crawl_result: CrawlResult,
    zone_name: str,
    game: str,
    category: str,
) -> str | None:
    """Store crawled content on filesystem and update graph.

    1. Write markdown to {game}/{zone}/{category}/{slug}.md
    2. Write .meta.json sidecar alongside
    3. Create/update crawl_page record in graph
    4. Create has_page edge (crawl_zone → crawl_page)
    5. Create from_domain edge (crawl_page → crawl_domain)

    Returns the relative file path, or None if nothing to store.
    """
    if not crawl_result.content:
        return None

    # 1. Filesystem write
    page_slug = _url_to_slug(crawl_result.url)
    relative_path = f"{game}/{zone_name}/{category}/{page_slug}.md"
    full_path = Path(CRAWL_CACHE_ROOT) / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(crawl_result.content, encoding="utf-8")

    # 2. Sidecar metadata
    now = datetime.now(timezone.utc)
    metadata = PageMetadata(
        url=crawl_result.url,
        domain=crawl_result.domain,
        crawled_at=now,
        content_hash=crawl_result.content_hash,
        http_status=crawl_result.http_status,
        content_length=len(crawl_result.content.encode("utf-8")),
    )
    sidecar_path = full_path.with_suffix(".meta.json")
    sidecar_path.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")

    # 3. Graph: create/update crawl_page record
    page_id = _url_to_record_id(crawl_result.url)
    result = await mcp_call(MCP_STORAGE_URL, "create_record", {
        "table": "crawl_page",
        "record_id": page_id,
        "data": json.dumps({
            "url": crawl_result.url,
            "title": crawl_result.title,
            "page_type": category,
            "domain": crawl_result.domain,
            "file_path": relative_path,
            "content_hash": crawl_result.content_hash,
            "crawled_at": now.isoformat(),
            "content_length": metadata.content_length,
            "http_status": crawl_result.http_status,
        }),
    })
    if result is None:
        logger.warning("graph_write_failed", extra={
            "operation": "create_record", "table": "crawl_page", "url": crawl_result.url,
        })

    # 4. Graph: has_page edge (zone → page)
    result = await mcp_call(MCP_STORAGE_URL, "create_relation", {
        "relation_type": "has_page",
        "from_record": f"crawl_zone:{zone_name}",
        "to_record": f"crawl_page:{page_id}",
        "properties": json.dumps({
            "page_type": category,
            "discovery_method": "search",
        }),
    })
    if result is None:
        logger.warning("graph_write_failed", extra={
            "operation": "create_relation", "relation": "has_page", "url": crawl_result.url,
        })

    # 5. Graph: from_domain edge (page → domain)
    domain_id = crawl_result.domain.replace(".", "_")
    result = await mcp_call(MCP_STORAGE_URL, "create_relation", {
        "relation_type": "from_domain",
        "from_record": f"crawl_page:{page_id}",
        "to_record": f"crawl_domain:{domain_id}",
    })
    if result is None:
        logger.warning("graph_write_failed", extra={
            "operation": "create_relation", "relation": "from_domain", "url": crawl_result.url,
        })

    logger.info(
        "page_stored",
        extra={
            "url": crawl_result.url,
            "path": relative_path,
            "content_hash": crawl_result.content_hash,
        },
    )

    return relative_path


# ---------------------------------------------------------------------------
# Store page with change detection (for refresh cycles)
# ---------------------------------------------------------------------------


async def store_page_with_change_detection(
    crawl_result: CrawlResult,
    zone_name: str,
    game: str,
    category: str,
) -> tuple[str | None, bool]:
    """Store crawled content with change detection.

    Returns (file_path, changed). On refresh, compares content hash
    against existing sidecar. Only overwrites if content changed.
    """
    if not crawl_result.content:
        return None, False

    page_slug = _url_to_slug(crawl_result.url)
    relative_path = f"{game}/{zone_name}/{category}/{page_slug}.md"
    full_path = Path(CRAWL_CACHE_ROOT) / relative_path
    sidecar_path = full_path.with_suffix(".meta.json")

    changed = True
    if sidecar_path.exists():
        existing = PageMetadata.model_validate_json(sidecar_path.read_text(encoding="utf-8"))
        if existing.content_hash == crawl_result.content_hash:
            # Content unchanged — update only crawled_at timestamp
            existing.crawled_at = datetime.now(timezone.utc)
            sidecar_path.write_text(existing.model_dump_json(indent=2), encoding="utf-8")
            changed = False

    if changed:
        # Write new content + full sidecar update
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(crawl_result.content, encoding="utf-8")

        metadata = PageMetadata(
            url=crawl_result.url,
            domain=crawl_result.domain,
            crawled_at=datetime.now(timezone.utc),
            content_hash=crawl_result.content_hash,
            http_status=crawl_result.http_status,
            content_length=len(crawl_result.content.encode("utf-8")),
        )
        sidecar_path.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")

        logger.info(
            "content_changed",
            extra={
                "url": crawl_result.url,
                "new_hash": crawl_result.content_hash,
            },
        )

    # Update graph timestamp regardless
    page_id = _url_to_record_id(crawl_result.url)
    result = await mcp_call(MCP_STORAGE_URL, "update_record", {
        "table": "crawl_page",
        "record_id": page_id,
        "data": json.dumps({
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "content_hash": crawl_result.content_hash,
        }),
    })
    if result is None:
        logger.warning("graph_write_failed", extra={
            "operation": "update_record", "table": "crawl_page", "url": crawl_result.url,
        })

    return relative_path, changed
