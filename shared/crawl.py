"""Shared crawl infrastructure — block detection and per-domain rate limiting.

Used by both the World Lore Researcher (mcp_client.py) and the Wiki Crawler
service (crawler.py). Extracted to shared/ so both consumers use identical
detection logic and throttle implementation.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Block detection — multi-signal CAPTCHA / rate-limit page detection
# ---------------------------------------------------------------------------

# Stage 1: Definitive phrases — never appear in legitimate game wiki content.
# A single match = blocked, no ambiguity.
_DEFINITIVE_BLOCKS: list[tuple[str, str]] = [
    ("verify you are human", "Cloudflare CAPTCHA"),
    ("please complete the security check", "security check gate"),
    ("checking your browser before accessing", "Cloudflare browser check"),
    ("cf-turnstile", "Cloudflare Turnstile widget"),
    ("enable javascript and cookies to continue", "JS/cookie gate"),
    ("automated access to this resource", "bot detection"),
    ("unusual traffic from your computer", "Google bot detection"),
]

# Stage 2: Soft signals — weighted. Multiple must fire to trigger (>= 0.6).
# Any single phrase could appear in legitimate content; it's the combination
# that indicates a block page.
_SOFT_SIGNALS: list[tuple[str, float, str]] = [
    ("just a moment", 0.35, "Cloudflare wait page"),
    ("cloudflare", 0.20, "Cloudflare reference"),
    ("ray id", 0.30, "Cloudflare Ray ID"),
    ("access denied", 0.35, "access denied"),
    ("403 forbidden", 0.40, "HTTP 403"),
    ("too many requests", 0.45, "rate limit response"),
    ("rate limit", 0.35, "rate limit mention"),
    ("captcha", 0.35, "CAPTCHA reference"),
    ("try again later", 0.25, "retry suggestion"),
    ("bot detection", 0.35, "bot detection"),
    ("please turn javascript on", 0.30, "JS required gate"),
    ("browser verification", 0.35, "browser verification"),
]

# Stage 3: Structural markers expected in real wiki/game content.
_WIKI_HEADER_RE = re.compile(r"^#{1,3}\s", re.MULTILINE)


@dataclass
class CrawlVerdict:
    """Result of content block detection."""

    is_blocked: bool
    reason: str


def detect_blocked_content(content: str) -> CrawlVerdict:
    """Multi-signal detection of CAPTCHA, rate-limit, and block pages.

    Stage 1: Definitive phrases that never appear in legitimate wiki content.
    Stage 2: Weighted soft signals — multiple must fire to cross threshold.
    Stage 3: Structural analysis — real wiki pages have headers and links;
             block pages lack these markers.
    """
    lower = content.lower()

    # Stage 1 — definitive matches
    for phrase, reason in _DEFINITIVE_BLOCKS:
        if phrase in lower:
            return CrawlVerdict(is_blocked=True, reason=reason)

    # Stage 2 — accumulate soft signals
    score = 0.0
    reasons: list[str] = []

    for phrase, weight, reason in _SOFT_SIGNALS:
        if phrase in lower:
            score += weight
            reasons.append(reason)

    # Stage 3 — structural analysis
    word_count = len(content.split())
    has_headers = bool(_WIKI_HEADER_RE.search(content))
    has_links = "](" in content

    if word_count < 100:
        score += 0.30
        reasons.append(f"very short ({word_count} words)")

    if word_count < 300 and not has_headers and not has_links:
        score += 0.25
        reasons.append("no wiki structure")

    if score >= 0.6:
        return CrawlVerdict(is_blocked=True, reason="; ".join(reasons))

    return CrawlVerdict(is_blocked=False, reason="")


# ---------------------------------------------------------------------------
# Per-domain rate limiter with exponential backoff
# ---------------------------------------------------------------------------


class DomainThrottle:
    """Per-domain rate limiter with exponential backoff and circuit breaker.

    - Enforces a minimum interval between requests to the same domain
      (derived from requests_per_minute).
    - Uses per-domain locks so different domains proceed in parallel
      while same-domain requests serialize.
    - Tracks exponential backoff per domain when block pages are detected.
    - Circuit breaker: after CIRCUIT_BREAKER_THRESHOLD consecutive blocks,
      the domain is tripped and requests are refused immediately (no wait).
    """

    CIRCUIT_BREAKER_THRESHOLD = 3

    def __init__(self, requests_per_minute: int) -> None:
        self._min_interval = 60.0 / requests_per_minute
        self._last_request: dict[str, float] = {}
        self._backoff: dict[str, float] = {}
        self._consecutive_blocks: dict[str, int] = {}
        self._domain_locks: dict[str, asyncio.Lock] = {}
        self._meta_lock: asyncio.Lock | None = None

    async def _get_domain_lock(self, domain: str) -> asyncio.Lock:
        """Lazily create per-domain locks (avoids module-level event loop)."""
        if self._meta_lock is None:
            self._meta_lock = asyncio.Lock()
        async with self._meta_lock:
            if domain not in self._domain_locks:
                self._domain_locks[domain] = asyncio.Lock()
            return self._domain_locks[domain]

    def is_tripped(self, domain: str) -> bool:
        """True if the circuit breaker has tripped for this domain."""
        return self._consecutive_blocks.get(domain, 0) >= self.CIRCUIT_BREAKER_THRESHOLD

    async def wait(self, domain: str) -> None:
        """Wait until it's safe to request this domain."""
        lock = await self._get_domain_lock(domain)
        async with lock:
            now = time.monotonic()
            min_wait = max(self._min_interval, self._backoff.get(domain, 0.0))
            last = self._last_request.get(domain, 0.0)
            elapsed = now - last

            if elapsed < min_wait:
                delay = min_wait - elapsed
                logger.info("Throttling %s: waiting %.1fs", domain, delay)
                await asyncio.sleep(delay)

            self._last_request[domain] = time.monotonic()

    def report_blocked(self, domain: str) -> None:
        """Double the backoff and increment the circuit breaker counter."""
        current = self._backoff.get(domain, 2.0)
        new_backoff = min(current * 2, 30.0)
        self._backoff[domain] = new_backoff

        count = self._consecutive_blocks.get(domain, 0) + 1
        self._consecutive_blocks[domain] = count

        if count >= self.CIRCUIT_BREAKER_THRESHOLD:
            logger.warning(
                "Circuit breaker TRIPPED for %s after %d consecutive blocks", domain, count,
            )
        else:
            logger.warning("Block detected on %s — backoff now %.1fs (%d/%d)",
                           domain, new_backoff, count, self.CIRCUIT_BREAKER_THRESHOLD)

    def report_success(self, domain: str) -> None:
        """Clear backoff and reset the circuit breaker for a domain."""
        if domain in self._backoff:
            logger.info("Clearing backoff for %s", domain)
            del self._backoff[domain]
        if domain in self._consecutive_blocks:
            del self._consecutive_blocks[domain]
