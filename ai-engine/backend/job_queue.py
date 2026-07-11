"""
Redis pool helpers and complaint status query (shared by routes.py and pipeline.py).
The enqueue_complaint_job() function here is used for the arq worker model — currently
deprecated in favour of pipeline.py's inline asyncio.create_task() approach.

init_redis_pool / close_redis_pool / get_pool / get_complaint_status are still actively used.
"""

import os
import json
import logging
from typing import Optional, Dict, Any

from arq.connections import RedisSettings, create_pool, ArqRedis

logger = logging.getLogger(__name__)

_pool: Optional[ArqRedis] = None


def _redis_settings():
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        from urllib.parse import urlparse
        parsed = urlparse(redis_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 6379
        db = 0
        if parsed.path and parsed.path.strip("/"):
            try:
                db = int(parsed.path.strip("/"))
            except ValueError:
                db = 0
        password = parsed.password or os.environ.get("REDIS_PASSWORD")
        ssl = parsed.scheme in ("rediss",)
        return RedisSettings(
            host=host, port=port, database=db,
            password=password, ssl=ssl,
        )
    host = os.environ.get("REDIS_HOST", "127.0.0.1")
    port = int(os.environ.get("REDIS_PORT", "6379"))
    db = int(os.environ.get("REDIS_DB", "0"))
    password = os.environ.get("REDIS_PASSWORD")
    ssl = os.environ.get("REDIS_TLS", "").lower() in ("1", "true", "yes")
    return RedisSettings(host=host, port=port, database=db, password=password, ssl=ssl)


async def init_redis_pool():
    global _pool
    try:
        _pool = await create_pool(_redis_settings())
        logger.info("[JOB_QUEUE] Redis pool created")
    except Exception as e:
        logger.warning("[JOB_QUEUE] Failed to create Redis pool: %s", e)
        _pool = None


async def close_redis_pool():
    global _pool
    if _pool is not None:
        try:
            _pool.close()
            await _pool.wait_closed()
        except Exception:
            pass
        _pool = None
        logger.info("[JOB_QUEUE] Redis pool closed")


def get_pool() -> Optional[ArqRedis]:
    """Expose the global Redis pool for use by other modules (rate limiter, etc.)."""
    return _pool


async def enqueue_complaint_job(complaint_id: str, user_id: Optional[str] = None) -> bool:
    if _pool is None:
        logger.warning("[JOB_QUEUE] Redis pool not available, cannot enqueue job")
        return False
    try:
        job = await _pool.enqueue_job("process_complaint", complaint_id, user_id)
        logger.info("[JOB_QUEUE] Enqueued job %s for complaint %s", job.job_id, complaint_id)
        return True
    except Exception as e:
        logger.error("[JOB_QUEUE] Failed to enqueue job: %s", e)
        return False


async def get_complaint_status(complaint_id: str) -> Optional[Dict[str, Any]]:
    if _pool is None:
        return None
    try:
        raw = await _pool.get(f"complaint:status:{complaint_id}")
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        return None
