"""
Arq job queue helpers: Redis pool init, enqueue complaint job, query status.
"""

import os
import json
import logging
from typing import Optional, Dict, Any

from arq.connections import RedisSettings, create_pool, ArqRedis

logger = logging.getLogger(__name__)

_pool: Optional[ArqRedis] = None


def _redis_settings():
    host = os.environ.get("REDIS_HOST", "127.0.0.1")
    port = int(os.environ.get("REDIS_PORT", "6379"))
    db = int(os.environ.get("REDIS_DB", "0"))
    return RedisSettings(host=host, port=port, database=db)


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
