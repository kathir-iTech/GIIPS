"""
Redis-backed rate limiter for auth endpoints.
Key pattern: rate_limit:auth:{ip}:{endpoint}
TTL: 60 seconds, max 5 attempts per window.
"""

import os
import json
import logging
from typing import Optional

from fastapi import HTTPException, Request
from job_queue import get_pool

logger = logging.getLogger(__name__)

RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 5


async def check_auth_rate_limit(request: Request) -> None:
    """FastAPI dependency: raises 429 if client exceeds rate limit on auth endpoints."""
    pool = get_pool()
    if pool is None:
        return

    ip = request.client.host if request.client else "unknown"
    endpoint = request.url.path
    key = f"rate_limit:auth:{ip}:{endpoint}"

    try:
        current = await pool.get(key)
        if current is None:
            await pool.set(key, "1", ex=RATE_LIMIT_WINDOW)
            return

        count = int(current)
        if count >= RATE_LIMIT_MAX:
            logger.warning("Rate limit exceeded for %s on %s", ip, endpoint)
            raise HTTPException(
                status_code=429,
                detail="Too many attempts. Please try again later."
            )

        await pool.incr(key)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Rate limiter error (falling open): %s", e)
