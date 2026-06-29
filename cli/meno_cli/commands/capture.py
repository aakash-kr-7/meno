# ==============================================================================
# (a) What this file is: meno capture subcommand.
# (b) What it does: meno capture — manual handoff when switching AI tools. Paste or pipe conversation. MENO immediately extracts and stores knowledge so the next tool's retrieve call already has it.
# (c) How it fits into the MENO system: Performs on-the-fly manual ingest from pasted conversation logs.
# ==============================================================================

import os
import sys
import re
import typer
import httpx
from typing import Optional, List, Dict
from rich.console import Console
from rich.table import Table

console = Console()

def parse_conversation(text: str) -> List[Dict[str, str]]:
    """Parses role markers or falls back to treating the entire text as a user message."""
    pattern = re.compile(r'^(user|human|assistant|system):\s*(.*)$', re.IGNORECASE)
    lines = text.splitlines()
    
    has_markers = False
    for line in lines:
        if pattern.match(line.strip()):
            has_markers = True
            break
            
    if not has_markers:
        return [{"role": "user", "content": text.strip()}]
        
    messages = []
    current_role = None
    current_content = []
    
    for line in lines:
        stripped = line.strip()
        match = pattern.match(stripped)
        if match:
            if current_role and current_content:
                messages.append({
                    "role": current_role,
                    "content": "\n".join(current_content).strip()
                })
            raw_role = match.group(1).lower()
            if raw_role in ("user", "human"):
                current_role = "user"
            elif raw_role == "assistant":
                current_role = "assistant"
            else:
                current_role = "system"
            current_content = [match.group(2)]
        else:
            if current_role:
                current_content.append(line)
            else:
                current_role = "user"
                current_content = [line]
                
    if current_role and current_content:
        messages.append({
            "role": current_role,
            "content": "\n".join(current_content).strip()
        })
        
    return messages

def capture_cmd(
    remote: Optional[str] = typer.Option(None, "--remote", help="Remote API URL to use instead of default localhost"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key for authentication")
):
    """
    Manual handoff when switching AI tools. Paste or pipe conversation.
    MENO immediately extracts and stores knowledge so the next tool's retrieve call already has it.
    """
    # 1. Read stdin
    if not sys.stdin.isatty():
        # piped or redirected input
        text = sys.stdin.read()
    else:
        # interactive terminal mode
        console.print("[bold yellow]Pasting conversation. Press Ctrl-D (Unix) or Ctrl-Z + Enter (Windows) when done:[/bold yellow]")
        text = sys.stdin.read()
        
    text = text.strip()
    if not text:
        console.print("[yellow]Empty input, aborting capture.[/yellow]")
        raise typer.Exit(0)
        
    # 2. Parse messages
    messages = parse_conversation(text)
    if not messages:
        console.print("[yellow]No messages parsed, aborting capture.[/yellow]")
        raise typer.Exit(0)
        
    # 3. Setup client headers
    api_url = remote if remote else "http://localhost:8000"
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    elif os.getenv("MENO_API_KEY"):
        headers["X-API-Key"] = os.getenv("MENO_API_KEY")
        
    try:
        # Create session
        session_payload = {
            "tenant_id": "default",
            "user_id": "default_user",
            "metadata": {"source": "cli_capture"}
        }
        resp = httpx.post(f"{api_url.rstrip('/')}/sessions/", json=session_payload, headers=headers, timeout=10.0)
        resp.raise_for_status()
        session_id = resp.json()["id"]
        
        # Append messages
        for msg in messages:
            msg_payload = {
                "role": msg["role"],
                "content": msg["content"]
            }
            resp = httpx.post(f"{api_url.rstrip('/')}/sessions/{session_id}/messages", json=msg_payload, headers=headers, timeout=10.0)
            resp.raise_for_status()
            
        # Promote session
        resp = httpx.post(f"{api_url.rstrip('/')}/worker/promote/{session_id}", headers=headers, timeout=15.0)
        resp.raise_for_status()
        promo_data = resp.json()
        
        # Fetch extracted details
        resp = httpx.get(f"{api_url.rstrip('/')}/sessions/{session_id}/extracted", headers=headers, timeout=10.0)
        resp.raise_for_status()
        extracted_items = resp.json()
        
        if not extracted_items:
            console.print("[yellow]No knowledge objects were extracted from this conversation.[/yellow]")
        else:
            table = Table(title="Extracted Knowledge Objects")
            table.add_column("Type", style="cyan")
            table.add_column("Title", style="magenta")
            table.add_column("Confidence", style="green")
            
            for item in extracted_items:
                table.add_row(item.get("type", "unknown"), item.get("title", ""), f"{item.get('confidence', 0.5):.2f}")
                
            console.print(table)
            console.print(f"[green]Successfully captured and stored {len(extracted_items)} knowledge objects.[/green]")
            
    except Exception as e:
        console.print(f"[bold red]Error in extract+store pipeline: {e}[/bold red]")
        raise typer.Exit(1)
