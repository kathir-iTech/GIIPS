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
