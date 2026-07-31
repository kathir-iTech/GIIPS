"""
Redis-backed rate limiter for GIIPS endpoints.
Key pattern: rate_limit:{prefix}:{ip}:{endpoint}
TTL: configurable per caller, falls open if Redis is down.
"""

import logging
from typing import Optional

from fastapi import HTTPException, Request
from job_queue import get_pool

logger = logging.getLogger(__name__)

RATE_LIMIT_WINDOW = 60
AUTH_RATE_LIMIT_MAX = 5
COMPLAINT_RATE_LIMIT_MAX = 10


async def _check_rate_limit(request: Request, prefix: str, max_requests: int, window: int = RATE_LIMIT_WINDOW) -> None:
    """Core rate limiter. Falls open (allows request) if Redis is unavailable."""
    pool = get_pool()
    if pool is None:
        return

    ip = request.client.host if request.client else "unknown"
    key = f"rate_limit:{prefix}:{ip}:{request.url.path}"

    try:
        current = await pool.get(key)
        if current is None:
            await pool.set(key, "1", ex=window)
            return

        count = int(current)
        if count >= max_requests:
            logger.warning("Rate limit exceeded for %s on %s", ip, request.url.path)
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Please try again later."
            )

        await pool.incr(key)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Rate limiter error (falling open): %s", e)


async def check_auth_rate_limit(request: Request) -> None:
    """5 req/min per IP on auth endpoints (login, register)."""
    await _check_rate_limit(request, "auth", AUTH_RATE_LIMIT_MAX)


async def check_complaint_rate_limit(request: Request) -> None:
    """10 req/min per IP on complaint submission."""
    await _check_rate_limit(request, "complaint", COMPLAINT_RATE_LIMIT_MAX)


VERIFY_RATE_LIMIT_MAX = 3
TRACK_RATE_LIMIT_MAX = 15


async def check_verify_rate_limit(request: Request) -> None:
    """3 req/min per IP on resolution verification (anti-guessing)."""
    await _check_rate_limit(request, "verify", VERIFY_RATE_LIMIT_MAX)


async def check_track_rate_limit(request: Request) -> None:
    """15 req/min per IP on public complaint tracking (anti-scraping)."""
    await _check_rate_limit(request, "track", TRACK_RATE_LIMIT_MAX)


APPEAL_RATE_LIMIT_MAX = 3
REOPEN_RATE_LIMIT_MAX = 3
SEARCH_RATE_LIMIT_MAX = 30
COPILOT_RATE_LIMIT_MAX = 10
PUBLIC_STATS_RATE_LIMIT_MAX = 60
TRACK_PUBLIC_RATE_LIMIT_MAX = 60

RATE_LIMIT_WINDOW_HOUR = 3600


async def check_appeal_rate_limit(request: Request) -> None:
    """3 req/hour per IP on incident appeal."""
    await _check_rate_limit(request, "appeal", APPEAL_RATE_LIMIT_MAX, window=RATE_LIMIT_WINDOW_HOUR)


async def check_reopen_rate_limit(request: Request) -> None:
    """3 req/hour per IP on incident reopen."""
    await _check_rate_limit(request, "reopen", REOPEN_RATE_LIMIT_MAX, window=RATE_LIMIT_WINDOW_HOUR)


async def check_search_rate_limit(request: Request) -> None:
    """30 req/min per IP on search."""
    await _check_rate_limit(request, "search", SEARCH_RATE_LIMIT_MAX)


async def check_copilot_rate_limit(request: Request) -> None:
    """10 req/min per IP on copilot chat."""
    await _check_rate_limit(request, "copilot", COPILOT_RATE_LIMIT_MAX)


async def check_public_stats_rate_limit(request: Request) -> None:
    """60 req/min per IP on public stats."""
    await _check_rate_limit(request, "public_stats", PUBLIC_STATS_RATE_LIMIT_MAX)


async def check_track_public_rate_limit(request: Request) -> None:
    """60 req/min per IP on public tracking."""
    await _check_rate_limit(request, "track_public", TRACK_PUBLIC_RATE_LIMIT_MAX)


TREND_RATE_LIMIT_MAX = 30


async def check_trend_rate_limit(request: Request) -> None:
    """30 req/min per IP on public complaint trend."""
    await _check_rate_limit(request, "trend", TREND_RATE_LIMIT_MAX)
