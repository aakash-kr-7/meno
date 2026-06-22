# Integration tests for knowledge store and retrieval. Requires Postgres + pgvector.
"""
Integration tests for knowledge store and retrieval. Requires Postgres + pgvector.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.types import KnowledgeType, RelationshipType
from knowledge.context import define_context


@pytest.mark.anyio
async def test_store_returns_correct_type(client: AsyncClient) -> None:
    payload = {
        "tenant_id": "tenant1",
        "user_id": "user1",
        "type": "decision",
        "content": "Use Redis for session caching to improve response times.",
        "title": "Session Caching Decision"
    }
    response = await client.post("/knowledge/store", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "decision"
    assert data["content"] == payload["content"]


@pytest.mark.anyio
async def test_retrieve_finds_stored(client: AsyncClient) -> None:
    # Store a specific CODE_PATTERN object
    store_payload = {
        "tenant_id": "tenant1",
        "user_id": "user1",
        "type": "code_pattern",
        "content": "Implement python decorator caching pattern to cache return values.",
        "title": "Python Caching Decorator"
    }
    store_res = await client.post("/knowledge/store", json=store_payload)
    assert store_res.status_code == 201

    # Retrieve with semantic query
    retrieve_payload = {
        "tenant_id": "tenant1",
        "user_id": "user1",
        "query": "how to cache decorator in python",
        "top_k": 3
    }
    retrieve_res = await client.post("/knowledge/retrieve", json=retrieve_payload)
    assert retrieve_res.status_code == 200
    results = retrieve_res.json()["results"]
    assert len(results) > 0
    assert "decorator" in results[0]["content"].lower()


@pytest.mark.anyio
async def test_retrieve_with_type_filter(client: AsyncClient) -> None:
    # Store MEMORY
    await client.post("/knowledge/store", json={
        "tenant_id": "tenant1",
        "user_id": "user1",
        "type": "memory",
        "content": "User prefers light mode."
    })
    # Store DECISION
    await client.post("/knowledge/store", json={
        "tenant_id": "tenant1",
        "user_id": "user1",
        "type": "decision",
        "content": "Use Redis for caching."
    })

    # Retrieve with type=decision
    retrieve_payload = {
        "tenant_id": "tenant1",
        "user_id": "user1",
        "query": "caching setup preference",
        "knowledge_type": "decision"
    }
    retrieve_res = await client.post("/knowledge/retrieve", json=retrieve_payload)
    assert retrieve_res.status_code == 200
    results = retrieve_res.json()["results"]
    assert len(results) > 0
    for r in results:
        assert r["type"] == "decision"


@pytest.mark.anyio
async def test_relationship_roundtrip(client: AsyncClient) -> None:
    # Store 2 objects
    obj_a_res = await client.post("/knowledge/store", json={
        "tenant_id": "tenant1",
        "user_id": "user1",
        "type": "architecture",
        "content": "API Gateway acts as the single entry point."
    })
    obj_b_res = await client.post("/knowledge/store", json={
        "tenant_id": "tenant1",
        "user_id": "user1",
        "type": "architecture",
        "content": "Authentication service validates tokens."
    })

    id_a = obj_a_res.json()["id"]
    id_b = obj_b_res.json()["id"]

    # POST /relate
    relate_payload = {
        "tenant_id": "tenant1",
        "source_id": id_a,
        "target_id": id_b,
        "relationship_type": "depends_on",
        "confidence": 0.9,
        "explanation": "Gateway depends on Auth service to validate tokens."
    }
    relate_res = await client.post("/knowledge/relate", json=relate_payload)
    assert relate_res.status_code == 201

    # GET /graph
    graph_res = await client.get(f"/knowledge/graph/{id_a}")
    assert graph_res.status_code == 200
    graph_data = graph_res.json()

    # Assert edge exists in graph
    edges = graph_data["edges"]
    assert len(edges) > 0
    edge = edges[0]
    assert edge["source"] == id_a
    assert edge["target"] == id_b
    assert edge["type"] == "depends_on"


@pytest.mark.anyio
async def test_context_scoping(client: AsyncClient, db_session: AsyncSession) -> None:
    # Define context A and B
    ctx_a = await define_context(db_session, tenant_id="tenant1", context_type="project", context_id_str="project-a")
    ctx_b = await define_context(db_session, tenant_id="tenant1", context_type="project", context_id_str="project-b")

    # Store object in context A
    store_payload = {
        "tenant_id": "tenant1",
        "user_id": "user1",
        "type": "code_pattern",
        "content": "Special secret encryption routine for project A.",
        "context_ids": [str(ctx_a.id)]
    }
    store_res = await client.post("/knowledge/store", json=store_payload)
    assert store_res.status_code == 201

    # Retrieve with context B
    retrieve_payload = {
        "tenant_id": "tenant1",
        "user_id": "user1",
        "query": "secret encryption routine",
        "context_id": str(ctx_b.id)
    }
    retrieve_res = await client.post("/knowledge/retrieve", json=retrieve_payload)
    assert retrieve_res.status_code == 200
    results = retrieve_res.json()["results"]

    # Assert empty
    assert len(results) == 0
