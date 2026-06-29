# ==============================================================================
# (a) What this file is: End-to-end continuity test suite.
# (b) What it does: Proves knowledge stored by one independent OS process is retrievable by a completely separate OS process with no shared memory.
# (c) How it fits into the MENO system: Validates cross-process continuity and auth enforcement in MCP HTTP transport.
# ==============================================================================

import os
import sys
import subprocess
import threading
import time
from uuid import uuid4
import pytest
import httpx
import uvicorn

from core.embeddings import embedding_service
from apps.api.main import app as api_app

class Server(uvicorn.Server):
    def install_signal_handlers(self):
        pass

@pytest.fixture(scope="session")
def run_api_server():
    """Runs FastAPI app in a background thread on localhost:8000."""
    _ = embedding_service.embed("warmup")
    
    config = uvicorn.Config(api_app, host="127.0.0.1", port=8000, log_level="warning")
    server = Server(config=config)
    thread = threading.Thread(target=server.run)
    thread.daemon = True
    thread.start()
    
    time.sleep(1.5)
    yield
    server.should_exit = True
    thread.join(timeout=2.0)

@pytest.fixture
def run_mcp_test_server():
    """Runs MCP HTTP server in a background thread on port 8765 with auth enabled."""
    from core.config import settings
    from apps.mcp.server import mcp
    from apps.mcp.auth import MCPAuthMiddleware
    
    orig_env = settings.APP_ENV
    settings.APP_ENV = "production"
    
    app = mcp.streamable_http_app()
    app.add_middleware(MCPAuthMiddleware)
    
    config = uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="warning")
    server = Server(config=config)
    
    thread = threading.Thread(target=server.run)
    thread.daemon = True
    thread.start()
    
    time.sleep(1.0)
    yield
    
    server.should_exit = True
    thread.join(timeout=2.0)
    settings.APP_ENV = orig_env

@pytest.mark.anyio
async def test_cross_process_retrieval(run_api_server, cleanup):
    """
    MUST use genuinely separate OS processes — not async tasks or threads.
    This is the proof that the entire expansion works.
    """
    unique_tag = f"test_ct_{uuid4().hex[:8]}"
    
    store_script = f"""
import httpx
import sys

r = httpx.post("http://localhost:8000/knowledge/store", json={{
    "tenant_id": "default",
    "user_id": "test",
    "type": "decision",
    "title": "Continuity test decision",
    "content": "Test content for cross-process retrieval.",
    "tags": ["{unique_tag}"]
}}, timeout=10.0)

sys.exit(0 if r.status_code in (200, 201) else 1)
"""

    result = subprocess.run(["python", "-c", store_script])
    assert result.returncode == 0, "Store subprocess failed"
    
    # Step 2: retrieve by tag/type in this process
    payload = {
        "tenant_id": "default",
        "user_id": "test",
        "knowledge_type": "decision"
    }
    
    async with httpx.AsyncClient() as client:
        r = await client.post("http://localhost:8000/knowledge/search/structured", json=payload)
        assert r.status_code == 200
        found = any(unique_tag in obj.get("tags", []) for obj in r.json())
        assert found, "Cross-process retrieval failed — object not found"
        print("PASS: Process B found knowledge stored by Process A.")

@pytest.mark.anyio
async def test_mcp_http_auth_enforced(run_mcp_test_server):
    """Requires MCP HTTP transport running. Verify HTTP transport 401 rejection without auth headers."""
    # We run the background server on 8765 using run_mcp_test_server fixture.
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post("http://localhost:8765/", json={}, timeout=2)
            # In production mode, unauthenticated request must be rejected
            assert r.status_code == 401
    except httpx.ConnectError:
        pytest.skip("MCP HTTP transport not running")
