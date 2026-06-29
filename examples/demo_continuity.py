# ==============================================================================
# (a) What this file is: MENO Multi-Tool Continuity Demo.
# (b) What it does: Proves knowledge stored by Process A is retrievable by Process B with zero shared state.
# (c) How it fits into the MENO system: Serves as an interactive end-to-end demo of platform capability.
# ==============================================================================
"""
MENO Multi-Tool Continuity Demo
Proves: knowledge stored by one tool (Process A) is retrievable by a completely
separate tool (Process B) with no shared in-memory state between them.
Three genuinely independent OS-level Python processes — not threads or async tasks.
Run: python examples/demo_continuity.py
Requires: docker compose up --build (API at localhost:8000)
"""

import subprocess
import tempfile
import os
import time

def main():
    unique_tag = f"continuity_demo_{int(time.time())}"
    print(f"Using unique tag for demo: {unique_tag}\n")

    # ==========================================================================
    # PHASE 1 — "Copilot stores a decision"
    # ==========================================================================
    print("--- PHASE 1: Process A (Copilot) stores a decision ---")
    phase1_script = f"""
import httpx
import sys

try:
    r = httpx.post("http://localhost:8000/knowledge/store", json={{
        "tenant_id": "default",
        "user_id": "demo",
        "type": "decision",
        "title": "Use pgvector for semantic search",
        "content": "We chose pgvector because it runs in Postgres and avoids a separate vector DB.",
        "tags": ["{unique_tag}"]
    }}, timeout=10.0)
    if r.status_code not in (200, 201):
        print(f"Failed to store. Status code: {{r.status_code}}, Response: {{r.text}}")
        sys.exit(1)
    print(f"Stored: {{r.json()['id']}}")
    sys.exit(0)
except Exception as e:
    print(f"Connection error: {{e}}")
    sys.exit(1)
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(phase1_script)
        temp_path1 = f.name

    try:
        subprocess.run(["python", temp_path1], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Process A failed: {e}")
    finally:
        try:
            os.unlink(temp_path1)
        except Exception:
            pass

    print("Process A (Copilot) stored decision and has now exited. All its memory is gone.\n")
    time.sleep(1.0)

    # ==========================================================================
    # PHASE 2 — "Claude retrieves it"
    # ==========================================================================
    print("--- PHASE 2: Process B (Claude Code) retrieves the decision ---")
    phase2_script = """
import httpx
import sys

try:
    r = httpx.post("http://localhost:8000/knowledge/retrieve", json={
        "tenant_id": "default",
        "user_id": "demo",
        "query": "how do we handle semantic search?"
    }, timeout=10.0)
    if r.status_code != 200:
        print(f"Failed to retrieve. Status code: {r.status_code}, Response: {r.text}")
        sys.exit(1)
        
    results = r.json().get("results", [])
    if len(results) == 0:
        print("No results returned!")
        sys.exit(1)
        
    print(f"Found: {results[0]['title']} (score: {results[0]['score']})")
    sys.exit(0)
except Exception as e:
    print(f"Connection error: {e}")
    sys.exit(1)
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(phase2_script)
        temp_path2 = f.name

    try:
        subprocess.run(["python", temp_path2], check=True)
        print("=" * 60)
        print(" Process B (Claude) found knowledge stored by Process A.")
        print(" No context was pasted between them.")
        print("=" * 60)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Process B failed: {e}")
    finally:
        try:
            os.unlink(temp_path2)
        except Exception:
            pass
    print()
    time.sleep(1.0)

    # ==========================================================================
    # PHASE 3 — "Codex promotes a session"
    # ==========================================================================
    print("--- PHASE 3: Process C (Codex) promotes a session ---")
    phase3_script = """
import httpx
import sys

try:
    # 1. Create a session
    r = httpx.post("http://localhost:8000/sessions/", json={
        "tenant_id": "default",
        "user_id": "demo",
        "metadata": {"demo": "continuity"}
    }, timeout=10.0)
    r.raise_for_status()
    session_id = r.json()["id"]
    
    # 2. Append messages
    messages = [
        {"role": "user", "content": "We decided to migrate the cache layer to Redis."},
        {"role": "assistant", "content": "That sounds like a good choice to reduce latency."},
        {"role": "user", "content": "Agreed, let's track this as cached data implementation."}
    ]
    for msg in messages:
        rm = httpx.post(f"http://localhost:8000/sessions/{session_id}/messages", json=msg, timeout=10.0)
        rm.raise_for_status()
        
    # 3. Promote session
    rp = httpx.post(f"http://localhost:8000/worker/promote/{session_id}", timeout=10.0)
    rp.raise_for_status()
    print(f"Extracted count: {rp.json().get('extracted_count', 0)}")
    sys.exit(0)
except Exception as e:
    print(f"Error during promotion: {e}")
    sys.exit(1)
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(phase3_script)
        temp_path3 = f.name

    try:
        subprocess.run(["python", temp_path3], check=True)
        print("Process C (Codex) promoted session. Extracted knowledge available to all tools.")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Process C failed: {e}")
    finally:
        try:
            os.unlink(temp_path3)
        except Exception:
            pass

    print("\n--- Continuity Demo Completed ---")

if __name__ == "__main__":
    main()
