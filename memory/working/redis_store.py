# Redis working memory Tier 0. 24-hour TTL. Messages also written to Postgres for persistence and promotion. Redis = read cache; Postgres = source of truth.
"""
Redis working memory Tier 0. 24-hour TTL. Messages also written to Postgres for persistence and promotion. Redis = read cache; Postgres = source of truth.
"""

import json
import asyncio
from datetime import datetime
from typing import Optional, Any
import redis.asyncio as redis

from core.config import settings

_redis_client: Optional[redis.Redis] = None
_loop: Optional[asyncio.AbstractEventLoop] = None


def get_redis_client() -> redis.Redis:
    global _redis_client, _loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        return redis.from_url(settings.REDIS_URL, decode_responses=True)

    if _redis_client is None or _loop is not current_loop:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        _loop = current_loop
    return _redis_client


async def create_session_cache(session_id: Any, user_id: str, tenant_id: str) -> dict:
    session_key = f"session:{session_id}"
    session_data = {
        "session_id": str(session_id),
        "user_id": str(user_id),
        "tenant_id": str(tenant_id),
        "messages": [],
        "created_at": datetime.utcnow().isoformat()
    }
    ttl = getattr(settings, "session_ttl_seconds", getattr(settings, "SESSION_TTL_SECONDS", 86400))
    client = get_redis_client()
    await client.set(session_key, json.dumps(session_data), ex=ttl)
    return session_data


async def append_message_cache(session_id: Any, role: str, content: str) -> dict:
    session_key = f"session:{session_id}"
    client = get_redis_client()
    data_str = await client.get(session_key)
    if not data_str:
        raise ValueError(f"Session {session_id} not found in cache")

    data = json.loads(data_str)
    new_msg = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat()
    }
    data["messages"].append(new_msg)

    # Get remaining TTL to preserve it
    ttl = await client.ttl(session_key)
    if ttl <= 0:
        ttl = getattr(settings, "session_ttl_seconds", getattr(settings, "SESSION_TTL_SECONDS", 86400))

    await client.set(session_key, json.dumps(data), ex=ttl)
    return data


async def get_session_cache(session_id: Any) -> Optional[dict]:
    session_key = f"session:{session_id}"
    client = get_redis_client()
    data_str = await client.get(session_key)
    if not data_str:
        return None
    return json.loads(data_str)


async def expire_session_cache(session_id: Any) -> bool:
    session_key = f"session:{session_id}"
    client = get_redis_client()
    deleted = await client.delete(session_key)
    return deleted > 0


async def get_session_length(session_id: Any) -> int:
    data = await get_session_cache(session_id)
    if not data:
        return 0
    return len(data.get("messages", []))


async def should_promote(session_id: Any) -> bool:
    length = await get_session_length(session_id)
    threshold = getattr(settings, "promotion_threshold", getattr(settings, "PROMOTION_THRESHOLD", 20))
    return length >= threshold
