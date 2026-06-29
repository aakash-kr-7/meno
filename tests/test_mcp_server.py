# ==============================================================================
# Tests for MCP tool layer. Calls tool functions directly, not over transport. Requires Postgres + Redis.
# ==============================================================================
"""
Tests for MCP tool layer. Calls tool functions directly, not over transport. Requires Postgres + Redis.
"""

import pytest
from httpx import AsyncClient

from apps.mcp.server import (
    meno_store,
    meno_retrieve,
    meno_relate,
    meno_get_graph
)

@pytest.mark.anyio
async def test_meno_store_tool_returns_serializable_dict(cleanup) -> None:
    """Call meno_store tool directly. Assert result is a dict with string 'id' field."""
    result = await meno_store(
        tenant_id="test_tenant",
        user_id="test_user",
        type="decision",
        content="Testing tool store directly",
        title="Test Store Tool"
    )
    assert isinstance(result, dict)
    assert "id" in result
    assert isinstance(result["id"], str)

@pytest.mark.anyio
async def test_meno_retrieve_tool_returns_list(client: AsyncClient, cleanup) -> None:
    """Store one object via REST. Call retrieve tool. Assert non-empty list of dicts."""
    store_payload = {
        "tenant_id": "test_tenant",
        "user_id": "test_user",
        "type": "decision",
        "content": "Testing retrieve tool via REST",
        "title": "REST Store Title",
        "confidence": 0.9,
        "tags": ["test"],
        "metadata": {},
        "context_ids": []
    }
    response = await client.post("/knowledge/store", json=store_payload)
    assert response.status_code == 201
    stored_data = response.json()
    assert "id" in stored_data

    # Try retrieving via REST endpoint to verify
    retrieve_payload = {
        "tenant_id": "test_tenant",
        "user_id": "test_user",
        "query": "Testing retrieve tool",
        "top_k": 5
    }
    await client.post("/knowledge/retrieve", json=retrieve_payload)

    results = await meno_retrieve(
        tenant_id="test_tenant",
        user_id="test_user",
        query="Testing retrieve tool",
        top_k=5
    )
    assert isinstance(results, list)
    assert len(results) > 0
    assert any(r["id"] == stored_data["id"] for r in results)

@pytest.mark.anyio
async def test_meno_relate_and_graph_tools(cleanup) -> None:
    """Store two objects. Call relate tool. Call graph tool. Assert edge present in result dict."""
    obj1 = await meno_store(
        tenant_id="test_tenant",
        user_id="test_user",
        type="decision",
        content="First object for relationship",
        title="Obj 1"
    )
    obj2 = await meno_store(
        tenant_id="test_tenant",
        user_id="test_user",
        type="code_pattern",
        content="Second object for relationship",
        title="Obj 2"
    )

    rel_res = await meno_relate(
        tenant_id="test_tenant",
        source_id=obj1["id"],
        target_id=obj2["id"],
        relationship_type="implements",
        confidence=0.8,
        explanation="First relates to second"
    )
    assert isinstance(rel_res, dict)
    assert "id" in rel_res

    graph_res = await meno_get_graph(
        object_id=obj1["id"],
        max_depth=2
    )
    assert isinstance(graph_res, dict)
    assert "edges" in graph_res
    edges = graph_res["edges"]
    assert len(edges) > 0
    assert any(e["source"] == obj1["id"] and e["target"] == obj2["id"] for e in edges)

@pytest.mark.anyio
async def test_meno_tool_error_handling(cleanup) -> None:
    """Call retrieve tool with invalid knowledge_type value. Assert {"error": ...} dict returned — not an exception raised."""
    result = await meno_retrieve(
        tenant_id="test_tenant",
        user_id="test_user",
        query="Invalid knowledge type query",
        knowledge_type="invalid_type_here"
    )
    assert isinstance(result, dict)
    assert "error" in result
    assert result["tool"] == "meno_retrieve"
