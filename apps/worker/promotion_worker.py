# Session promotion worker. Runs extraction pipeline. Marks session promoted. Promotion = structured extraction + relationship inference, not summarization. Triggered via REST endpoint or threshold check.
"""
Session promotion worker. Runs extraction pipeline. Marks session promoted. Promotion = structured extraction + relationship inference, not summarization. Triggered via REST endpoint or threshold check.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.session import Session, SessionMessage
from memory.working.redis_store import get_session_cache, should_promote
from knowledge.extraction import extract_and_store_from_session


async def promote_session(session_id: str, db: AsyncSession) -> Optional[dict]:
    """
    Promote a session: extracts knowledge objects, infers relationships,
    scans for project contexts, links them, and marks the session as promoted.
    """
    try:
        session_uuid = uuid.UUID(session_id) if isinstance(session_id, str) else session_id
    except ValueError:
        return None

    # 1. Get Session from Postgres. Return None if not found or already promoted.
    stmt = select(Session).where(Session.id == session_uuid)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session or session.promoted:
        return None

    # 2. Get messages: try get_session_cache(session_id) first, fallback to Postgres session_messages.
    messages = []
    cache = await get_session_cache(session_uuid)
    if cache and cache.get("messages"):
        messages = cache["messages"]
    else:
        # Fallback to Postgres session_messages
        msg_stmt = select(SessionMessage).where(SessionMessage.session_id == session_uuid).order_by(SessionMessage.created_at.asc())
        msg_res = await db.execute(msg_stmt)
        db_messages = msg_res.scalars().all()
        messages = [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat()
            }
            for msg in db_messages
        ]

    # 3. If no messages: return {"promoted": False, "reason": "no messages"}
    if not messages:
        return {"promoted": False, "reason": "no messages"}

    # 4. Call extract_and_store_from_session(db, session_id, user_id, tenant_id, messages)
    stored_objs = await extract_and_store_from_session(
        db=db,
        session_id=session_uuid,
        user_id=session.user_id,
        tenant_id=session.tenant_id,
        messages=messages
    )

    # 5. Set session.promoted=True, session.promoted_at=now(). Commit.
    session.promoted = True
    session.promoted_at = datetime.utcnow()
    await db.commit()

    # 6. Return {promoted:True, session_id:str, extracted_count:int, object_ids:[str...]}
    return {
        "promoted": True,
        "session_id": str(session_uuid),
        "extracted_count": len(stored_objs),
        "object_ids": [str(obj.id) for obj in stored_objs]
    }


async def check_and_promote_eligible(db: AsyncSession) -> List[dict]:
    """
    Query sessions WHERE promoted=False ORDER BY created_at DESC LIMIT 100.
    For each: call should_promote(session_id) via Redis.
    If True: call promote_session(). Return list of results.
    """
    stmt = select(Session).where(Session.promoted == False).order_by(Session.created_at.desc()).limit(100)
    res = await db.execute(stmt)
    sessions = res.scalars().all()

    results = []
    for s in sessions:
        if await should_promote(s.id):
            promo_res = await promote_session(s.id, db)
            if promo_res:
                results.append(promo_res)

    return results
