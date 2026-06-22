# Tests for the knowledge extraction pipeline. Rule-based (no LLM key needed). Requires Postgres + Redis.
"""
Tests for the knowledge extraction pipeline. Rule-based (no LLM key needed). Requires Postgres + Redis.
"""

import pytest
import redis.asyncio as redis
from httpx import AsyncClient
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.llm import extract_from_messages, infer_relationship, ExtractionResult
from core.types import KnowledgeType, RelationshipType
from db.models.session import Session, SessionMessage
from db.models.knowledge_object import KnowledgeObject
from memory.working.redis_store import create_session_cache, append_message_cache


@pytest.fixture(autouse=True)
async def cleanup_sessions(db_session: AsyncSession):
    # Before test runs: make sure everything is empty
    await db_session.execute(delete(SessionMessage))
    await db_session.execute(delete(Session))
    await db_session.commit()

    client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    await client.flushdb()

    yield

    # After test runs: cleanup again
    await db_session.execute(delete(SessionMessage))
    await db_session.execute(delete(Session))
    await db_session.commit()

    await client.flushdb()
    await client.aclose()


@pytest.mark.anyio
async def test_rule_based_extracts_decision():
    messages = [{"role": "user", "content": "We decided to use pgvector for semantic search instead of Elasticsearch"}]
    results = await extract_from_messages(messages)
    assert len(results) >= 1
    types = [res.type for res in results]
    assert KnowledgeType.DECISION.value in types


@pytest.mark.anyio
async def test_rule_based_extracts_memory():
    messages = [{"role": "user", "content": "My favorite language is Rust"}]
    results = await extract_from_messages(messages)
    assert len(results) >= 1
    types = [res.type for res in results]
    assert KnowledgeType.MEMORY.value in types


@pytest.mark.anyio
async def test_relationship_inferred():
    obj1 = ExtractionResult(
        type=KnowledgeType.DECISION.value,
        title="Choose pgvector",
        content="We decided to use pgvector",
        confidence=0.8,
        tags=["decision"]
    )
    obj2 = ExtractionResult(
        type=KnowledgeType.CODE_PATTERN.value,
        title="Db queries",
        content="Implement SQL query patterns",
        confidence=0.8,
        tags=["code_pattern"]
    )
    result = await infer_relationship(obj1, obj2)
    assert result is not None
    assert result["type"] == RelationshipType.IMPLEMENTS.value


@pytest.mark.anyio
async def test_promote_session_end_to_end(db_session: AsyncSession, client: AsyncClient):
    # 1. Create Session in Postgres
    session_row = Session(
        tenant_id="test-tenant",
        user_id="test-user",
        metadata_={}
    )
    db_session.add(session_row)
    await db_session.commit()
    await db_session.refresh(session_row)

    session_id = session_row.id

    # 2. Create Redis cache
    await create_session_cache(
        session_id=session_id,
        user_id="test-user",
        tenant_id="test-tenant"
    )

    # 3. Append 3 messages including a decision
    messages_to_append = [
        {"role": "user", "content": "Hello, let's start the project."},
        {"role": "assistant", "content": "Sure, what is the plan?"},
        {"role": "user", "content": "We decided to use pgvector for semantic search instead of Elasticsearch."}
    ]

    for msg in messages_to_append:
        await append_message_cache(session_id, msg["role"], msg["content"])
        db_msg = SessionMessage(
            session_id=session_id,
            role=msg["role"],
            content=msg["content"]
        )
        db_session.add(db_msg)
    
    await db_session.commit()

    # 4. Call promote endpoint
    response = await client.post(f"/worker/promote/{session_id}")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["promoted"] is True
    assert res_data["extracted_count"] >= 1
    assert len(res_data["object_ids"]) >= 1

    # 5. Assert promoted=True in Postgres
    await db_session.refresh(session_row)
    assert session_row.promoted is True
    assert session_row.promoted_at is not None

    # 6. Assert knowledge_objects exist in DB with source_type='session'
    stmt_ko = select(KnowledgeObject).where(
        KnowledgeObject.source_type == "session",
        KnowledgeObject.source_id == str(session_id)
    )
    res_ko = await db_session.execute(stmt_ko)
    objs = res_ko.scalars().all()
    assert len(objs) >= 1
    types = {obj.type for obj in objs}
    assert KnowledgeType.DECISION.value in types
