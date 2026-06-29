# ==============================================================================
# (a) What this file is: CLI test suite.
# (b) What it does: Tests config-writing in isolation (no Docker or tool installs). Ingest and capture tested against running MENO.
# (c) How it fits into the MENO system: Validates correctness of all CLI commands.
# ==============================================================================

import os
import sys
import json
import tempfile
import shutil
import subprocess
import threading
import time
import pytest
import httpx
import uvicorn

from core.embeddings import embedding_service
from apps.api.main import app
from meno_cli.detect import write_vscode_config
from meno_cli.commands.ingest import ingest_path

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
    time.sleep(1.5)
    yield
    server.should_exit = True
    thread.join(timeout=2.0)

@pytest.mark.anyio
async def test_detect_writes_vscode_config_without_clobbering():
    """
    Create temp dir with .vscode/mcp.json containing one existing unrelated server entry.
    Run the detect_vscode() writer function. Assert both the original server AND the meno server are present.
    Verify valid JSON.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        orig_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            os.makedirs(".vscode", exist_ok=True)
            mcp_file = ".vscode/mcp.json"
            
            # Write unrelated server config
            existing_config = {
                "servers": {
                    "unrelated": {
                        "command": "node",
                        "args": ["unrelated.js"]
                    }
                }
            }
            with open(mcp_file, "w", encoding="utf-8") as f:
                json.dump(existing_config, f, indent=2)
                
            entry = {
                "command": "python",
                "args": ["-m", "apps.mcp"]
            }
            # Run writer
            write_vscode_config(entry)
            
            # Verify both are present
            with open(mcp_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            assert "servers" in data
            assert "unrelated" in data["servers"]
            assert "meno" in data["servers"]
            assert data["servers"]["unrelated"]["command"] == "node"
            assert data["servers"]["meno"]["command"] == "python"
        finally:
            os.chdir(orig_cwd)

@pytest.mark.anyio
async def test_ingest_extracts_from_sample_repo(run_api_server, cleanup):
    """
    Create fixture dir: README.md ("# MyProject: architecture overview") + docs/decisions/001.md
    ("We decided to use Redis for caching"). Run ingest against fixture dir.
    Assert >= 1 knowledge_object in DB (query via httpx POST /knowledge/search/structured).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create fixtures
        readme_path = os.path.join(tmpdir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write("# MyProject: architecture overview")
            
        docs_dir = os.path.join(tmpdir, "docs", "decisions")
        os.makedirs(docs_dir, exist_ok=True)
        decision_path = os.path.join(docs_dir, "001.md")
        with open(decision_path, "w", encoding="utf-8") as f:
            f.write("We decided to use Redis for caching")
            
        # Run ingest via helper function
        ingested = ingest_path(tmpdir, "http://localhost:8000", {})
        assert ingested >= 1
        
        # Verify in DB via HTTP search
        payload = {
            "tenant_id": "default",
            "user_id": "default_user",
            "knowledge_type": "decision",
            "limit": 10
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post("http://localhost:8000/knowledge/search/structured", json=payload)
            assert resp.status_code == 200
            objs = resp.json()
            assert len(objs) >= 1
            assert any("Redis" in item["content"] for item in objs)

@pytest.mark.anyio
async def test_capture_from_stdin(run_api_server, cleanup):
    """
    Simulate stdin with: "We decided to use tokio for the async runtime in Sol worker."
    Run capture command with that input. Assert a DECISION knowledge_object is stored in DB.
    """
    # Run capture subcommand using subprocess or CLI call
    # We can pass simulated stdin to the command: `meno capture`
    input_text = "We decided to use tokio for the async runtime in Sol worker."
    
    # Run venv/Scripts/meno capture
    cmd = [os.path.join("venv", "Scripts", "meno"), "capture"]
    try:
        proc = subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        raise e
    
    # Assert output shows captured
    assert "captured" in proc.stdout.lower() or "extracted" in proc.stdout.lower()
    
    # Verify in DB via HTTP search
    payload = {
        "tenant_id": "default",
        "user_id": "default_user",
        "knowledge_type": "decision",
        "limit": 10
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post("http://localhost:8000/knowledge/search/structured", json=payload)
        assert resp.status_code == 200
        objs = resp.json()
        assert len(objs) >= 1
        assert any("tokio" in item["content"] for item in objs)

@pytest.mark.anyio
async def test_hook_capture_handles_meno_down_gracefully():
    """
    Run hook-capture pointing at localhost:19999 (unreachable).
    Assert subprocess exit code is 0. Assert something was printed to stderr.
    """
    # Run venv/Scripts/meno hook-capture <some_hash> --remote http://localhost:19999
    cmd = [
        os.path.join("venv", "Scripts", "meno"),
        "hook-capture",
        "dummy_commit_hash",
        "--remote",
        "http://localhost:19999"
    ]
    
    # Mock Git repo calls if hook-capture runs git commands.
    # To run git log, we need a valid git repo.
    # We can run it in our current git repo, which is valid and contains git hashes!
    # Let's get a valid commit hash using `git rev-parse HEAD`
    hash_res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    valid_hash = hash_res.stdout.strip()
    
    cmd[2] = valid_hash
    
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    
    # Assert exit code is 0 (graceful recovery)
    assert proc.returncode == 0
    # Assert warning or error printed to stderr
    assert "warning" in proc.stderr.lower() or "error" in proc.stderr.lower() or "failed" in proc.stderr.lower()
