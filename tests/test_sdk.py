"""
Integration tests for MENO SDK. Requires API at localhost:8000.
"""

import threading
import time
import uuid
import pytest
import uvicorn

# Preload embedding service to avoid HTTP client timeouts during model load
from core.embeddings import embedding_service
from apps.api.main import app
from meno import Meno, KnowledgeType, RelationshipType


class Server(uvicorn.Server):
    def install_signal_handlers(self):
        pass


@pytest.fixture(scope="session")
def run_api_server():
    """Runs FastAPI app in a background thread on localhost:8000."""
    # Force load embedding model in main thread
    _ = embedding_service.embed("warmup")
    
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
    server = Server(config=config)
    thread = threading.Thread(target=server.run)
    thread.daemon = True
    thread.start()
    
    # Give the server a moment to start
    time.sleep(1.0)
    yield
    server.should_exit = True
    thread.join(timeout=2.0)


@pytest.mark.anyio
async def test_sdk_store_and_retrieve(run_api_server, cleanup) -> None:
    sdk = Meno(base_url="http://localhost:8000")
    
    # Store CODE_PATTERN
    store_res = sdk.store(
        user_id="test_user_1",
        content="Implement python decorator caching pattern to cache return values.",
        type=KnowledgeType.CODE_PATTERN,
        title="Python Caching Decorator"
    )
    assert store_res.id is not None
    assert store_res.type == "code_pattern"
    assert store_res.content == "Implement python decorator caching pattern to cache return values."
    
    # Retrieve with semantic query
    results = sdk.retrieve(
        user_id="test_user_1",
        query="how to cache decorator in python",
        top_k=3
    )
    assert len(results) > 0
    assert results[0].type == "code_pattern"
    assert "decorator" in results[0].content.lower()


@pytest.mark.anyio
async def test_sdk_relate_and_graph(run_api_server, cleanup) -> None:
    sdk = Meno(base_url="http://localhost:8000")
    
    # Store 2 objects
    obj_a = sdk.store(
        user_id="test_user_2",
        content="Component A implements authentication backend.",
        type=KnowledgeType.CODE_PATTERN
    )
    obj_b = sdk.store(
        user_id="test_user_2",
        content="Component B handles user login requests.",
        type=KnowledgeType.CODE_PATTERN
    )
    
    # Relate them IMPLEMENTS
    rel_res = sdk.relate(
        source_id=obj_a.id,
        target_id=obj_b.id,
        relationship_type=RelationshipType.IMPLEMENTS,
        confidence=0.8,
        explanation="Component A implements backend login logic for Component B"
    )
    assert rel_res.id is not None
    assert rel_res.relationship_type == "implements"
    
    # Get graph
    graph = sdk.get_graph(object_id=obj_a.id, max_depth=2)
    assert graph.root == obj_a.id
    assert len(graph.edges) > 0
    edge = graph.edges[0]
    assert edge["source"] == obj_a.id
    assert edge["target"] == obj_b.id
    assert edge["type"] == "implements"


@pytest.mark.anyio
async def test_sdk_define_context_and_scope(run_api_server, cleanup) -> None:
    sdk = Meno(base_url="http://localhost:8000")
    
    # Define context
    context_id = "project-xyz"
    ctx_res = sdk.define_context(
        context_type="project",
        context_id=context_id,
        metadata={"name": "Project XYZ"}
    )
    assert ctx_res.id is not None
    assert ctx_res.context_id == context_id
    
    # Store in it
    obj_res = sdk.store(
        user_id="test_user_3",
        content="Sensitive code pattern specifically for project-xyz.",
        type=KnowledgeType.CODE_PATTERN,
        context_ids=[ctx_res.id]
    )
    assert obj_res.id is not None
    
    # Retrieve scoped (should be found)
    results_found = sdk.retrieve(
        user_id="test_user_3",
        query="sensitive code pattern",
        context_id=ctx_res.id
    )
    assert len(results_found) > 0
    assert results_found[0].id == obj_res.id
    
    # Retrieve wrong context (should be empty)
    wrong_ctx_res = sdk.define_context(
        context_type="project",
        context_id="project-other"
    )
    
    results_empty = sdk.retrieve(
        user_id="test_user_3",
        query="sensitive code pattern",
        context_id=wrong_ctx_res.id
    )
    assert len(results_empty) == 0


@pytest.mark.anyio
async def test_sdk_session_and_promote(run_api_server, cleanup) -> None:
    sdk = Meno(base_url="http://localhost:8000")
    
    # Create session
    session_info = await sdk.acreate_session(user_id="test_user_4")
    assert session_info.id is not None
    
    # Append 3 messages (one decision-flavored)
    await sdk.aappend_message(session_id=session_info.id, role="user", content="Hello, let's start the design discussion.")
    await sdk.aappend_message(session_id=session_info.id, role="assistant", content="Sure, what is the plan?")
    # Decision-flavored message
    await sdk.aappend_message(
        session_id=session_info.id, 
        role="user", 
        content="We decided to use Redis for session caching because it has low latency."
    )
    
    # Get session messages to verify they are recorded
    sess_data = await sdk.aget_session(session_id=session_info.id)
    assert len(sess_data.get("messages", [])) == 3
    
    # Promote session
    promo_res = await sdk.apromote_session(session_id=session_info.id)
    assert promo_res.get("promoted") is True
    
    # Get extracted (should be non-empty)
    extracted = await sdk.aget_extracted_from_session(session_id=session_info.id)
    assert len(extracted) > 0
    assert any(item.type == "decision" for item in extracted)
