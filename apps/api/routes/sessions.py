# REST router for Tier 0 working memory. Dual-write: Redis (fast) + Postgres (persistent). Both always in sync.
"""
REST router for Tier 0 working memory. Dual-write: Redis (fast) + Postgres (persistent). Both always in sync.
"""

import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from apps.api.dependencies import get_db
from apps.api.schemas import (
    SessionCreateRequest,
    SessionResponse,
    MessageAppendRequest,
    SessionMessagesResponse,
    StoreResponse
)
from db.models.session import Session, SessionMessage
from db.models.knowledge_object import KnowledgeObject
from memory.working.redis_store import (
    create_session_cache,
    append_message_cache,
    get_session_cache,
    expire_session_cache
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_new_session(
    request: SessionCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    # Prepare metadata with optional context_id
    meta = dict(request.metadata or {})
    if request.context_id:
        meta["context_id"] = str(request.context_id)

    # Save to PostgreSQL
    session_row = Session(
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        metadata_=meta
    )
    db.add(session_row)
    await db.commit()
    await db.refresh(session_row)

    # Initialize Redis Cache
    await create_session_cache(
        session_id=session_row.id,
        user_id=session_row.user_id,
        tenant_id=session_row.tenant_id
    )

    return SessionResponse(
        id=session_row.id,
        tenant_id=session_row.tenant_id,
        user_id=session_row.user_id,
        context_id=request.context_id,
        metadata=session_row.metadata_,
        created_at=session_row.created_at,
        updated_at=session_row.last_activity
    )


@router.post("/{session_id}/messages", response_model=SessionMessagesResponse)
async def append_message_to_session(
    session_id: uuid.UUID,
    request: MessageAppendRequest,
    db: AsyncSession = Depends(get_db)
):
    # Ensure session exists in Postgres
    session_stmt = select(Session).where(Session.id == session_id)
    session_res = await db.execute(session_stmt)
    session_row = session_res.scalar_one_or_none()
    if not session_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Append to Redis Cache
    try:
        updated_cache = await append_message_cache(session_id, request.role, request.content)
    except ValueError:
        # Rebuild cache from PostgreSQL if it was evicted
        msg_stmt = select(SessionMessage).where(SessionMessage.session_id == session_id).order_by(SessionMessage.created_at.asc())
        msg_res = await db.execute(msg_stmt)
        db_messages = msg_res.scalars().all()

        formatted_messages = []
        for msg in db_messages:
            formatted_messages.append({
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat()
            })

        await create_session_cache(
            session_id=session_id,
            user_id=session_row.user_id,
            tenant_id=session_row.tenant_id
        )
        for msg in formatted_messages:
            await append_message_cache(session_id, msg["role"], msg["content"])

        updated_cache = await append_message_cache(session_id, request.role, request.content)

    # Write SessionMessage row in PostgreSQL
    db_msg = SessionMessage(
        session_id=session_id,
        role=request.role,
        content=request.content,
        metadata_=request.metadata or {}
    )
    db.add(db_msg)

    # Update session activity
    session_row.last_activity = datetime.utcnow()
    await db.commit()

    return SessionMessagesResponse(
        session_id=session_id,
        messages=updated_cache["messages"]
    )


@router.get("/{session_id}", response_model=SessionMessagesResponse)
async def get_session_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    # Try Redis cache first
    cache = await get_session_cache(session_id)
    if cache:
        return SessionMessagesResponse(
            session_id=session_id,
            messages=cache["messages"]
        )

    # Fallback to PostgreSQL
    session_stmt = select(Session).where(Session.id == session_id)
    session_res = await db.execute(session_stmt)
    session_row = session_res.scalar_one_or_none()
    if not session_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    msg_stmt = select(SessionMessage).where(SessionMessage.session_id == session_id).order_by(SessionMessage.created_at.asc())
    msg_res = await db.execute(msg_stmt)
    db_messages = msg_res.scalars().all()

    formatted_messages = []
    for msg in db_messages:
        formatted_messages.append({
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.created_at.isoformat()
        })

    # Re-cache in Redis
    await create_session_cache(
        session_id=session_id,
        user_id=session_row.user_id,
        tenant_id=session_row.tenant_id
    )
    for msg in formatted_messages:
        await append_message_cache(session_id, msg["role"], msg["content"])

    return SessionMessagesResponse(
        session_id=session_id,
        messages=formatted_messages
    )


@router.delete("/{session_id}")
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    # Expire Redis cache
    await expire_session_cache(session_id)

    # Mark / delete Postgres
    stmt = delete(Session).where(Session.id == session_id)
    await db.execute(stmt)
    await db.commit()

    return {"deleted": True}


@router.get("/{session_id}/extracted", response_model=List[StoreResponse])
async def get_session_extracted_knowledge(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(KnowledgeObject).where(
        KnowledgeObject.source_type == "session",
        KnowledgeObject.source_id == str(session_id)
    )
    res = await db.execute(stmt)
    objs = res.scalars().all()
    return objs
