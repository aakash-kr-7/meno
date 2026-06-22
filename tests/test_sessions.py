# Integration tests for Tier 0 working memory. Tests dual-write and retrieval.
"""
Integration tests for Tier 0 working memory. Tests dual-write and retrieval.
"""

import pytest
import uuid
import redis.asyncio as redis
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from core.config import settings
from db.models.session import Session, SessionMessage


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
async def test_create_session(client: AsyncClient) -> None:
    payload = {
        "tenant_id": "tenant1",
        "user_id": "user1",
        "metadata": {"source": "test"}
    }
    response = await client.post("/sessions/", json=payload)
    assert response.status_code in (200, 201)
    data = response.json()
    assert "id" in data
    assert data["tenant_id"] == "tenant1"
    assert data["user_id"] == "user1"
    assert data["metadata"]["source"] == "test"


@pytest.mark.anyio
async def test_append_and_retrieve(client: AsyncClient) -> None:
    payload = {
        "tenant_id": "tenant1",
        "user_id": "user1"
    }
    create_res = await client.post("/sessions/", json=payload)
    assert create_res.status_code in (200, 201)
    session_id = create_res.json()["id"]

    msg1 = {"role": "user", "content": "First test message"}
    res1 = await client.post(f"/sessions/{session_id}/messages", json=msg1)
    assert res1.status_code == 200

    msg2 = {"role": "assistant", "content": "Second test message"}
    res2 = await client.post(f"/sessions/{session_id}/messages", json=msg2)
    assert res2.status_code == 200

    get_res = await client.get(f"/sessions/{session_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["session_id"] == session_id
    messages = data["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "First test message"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Second test message"


@pytest.mark.anyio
async def test_dual_write(client: AsyncClient, db_session: AsyncSession) -> None:
    payload = {
        "tenant_id": "tenant1",
        "user_id": "user1"
    }
    create_res = await client.post("/sessions/", json=payload)
    assert create_res.status_code in (200, 201)
    session_id = create_res.json()["id"]

    msg = {"role": "user", "content": "Hello, is this persisted?"}
    res = await client.post(f"/sessions/{session_id}/messages", json=msg)
    assert res.status_code == 200

    stmt = select(SessionMessage).where(SessionMessage.session_id == uuid.UUID(session_id))
    db_res = await db_session.execute(stmt)
    db_messages = db_res.scalars().all()

    assert len(db_messages) == 1
    assert db_messages[0].role == "user"
    assert db_messages[0].content == "Hello, is this persisted?"


@pytest.mark.anyio
async def test_expire(client: AsyncClient) -> None:
    payload = {
        "tenant_id": "tenant1",
        "user_id": "user1"
    }
    create_res = await client.post("/sessions/", json=payload)
    assert create_res.status_code in (200, 201)
    session_id = create_res.json()["id"]

    del_res = await client.delete(f"/sessions/{session_id}")
    assert del_res.status_code == 200
    assert del_res.json() == {"deleted": True}

    get_res = await client.get(f"/sessions/{session_id}")
    assert get_res.status_code == 404


@pytest.mark.anyio
async def test_extracted_empty(client: AsyncClient) -> None:
    payload = {
        "tenant_id": "tenant1",
        "user_id": "user1"
    }
    create_res = await client.post("/sessions/", json=payload)
    assert create_res.status_code in (200, 201)
    session_id = create_res.json()["id"]

    ext_res = await client.get(f"/sessions/{session_id}/extracted")
    assert ext_res.status_code == 200
    assert ext_res.json() == []
