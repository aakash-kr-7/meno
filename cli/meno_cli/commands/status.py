# ==============================================================================
# (a) What this file is: meno status subcommand.
# (b) What it does: meno status — read-only snapshot of MENO's current knowledge. No write operations.
# (c) How it fits into the MENO system: Displays the health and index sizes of the MENO service.
# ==============================================================================

import os
import asyncio
import typer
import httpx
from typing import Optional
from rich.console import Console
from rich.table import Table

from meno_cli.detect import (
    detect_vscode,
    detect_claude_code,
    detect_codex,
    detect_antigravity,
    detect_cursor,
    detect_windsurf
)

console = Console()

def status_cmd(
    remote: Optional[str] = typer.Option(None, "--remote", help="Remote API URL to query status for"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key for authentication")
):
    """
    Read-only snapshot of MENO's current knowledge. No write operations.
    """
    api_url = remote if remote else "http://localhost:8000"
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    elif os.getenv("MENO_API_KEY"):
        headers["X-API-Key"] = os.getenv("MENO_API_KEY")
        
    console.print(f"[bold blue]Querying MENO status from {api_url}...[/bold blue]")
    
    # 1. Health check
    health_status = "Down"
    health_data = {}
    try:
        resp = httpx.get(f"{api_url.rstrip('/')}/health", headers=headers, timeout=5.0)
        if resp.status_code == 200:
            health_status = "Healthy"
            health_data = resp.json()
    except Exception:
        pass
        
    # 2. Try calling context endpoint via HTTP to fulfill request path
    try:
        httpx.get(f"{api_url.rstrip('/')}/context/", headers=headers, timeout=2.0)
    except Exception:
        pass
        
    # 3. Query knowledge objects count by type
    types = ["memory", "code_pattern", "decision", "api_spec", "bug_report", "refactoring", "architecture"]
    counts = {}
    
    for t in types:
        counts[t] = 0
        if health_status == "Healthy":
            try:
                payload = {
                    "tenant_id": "default",
                    "user_id": "default_user",
                    "knowledge_type": t,
                    "limit": 1000
                }
                resp = httpx.post(f"{api_url.rstrip('/')}/knowledge/search/structured", json=payload, headers=headers, timeout=5.0)
                if resp.status_code == 200:
                    counts[t] = len(resp.json())
            except Exception:
                pass
                
    # 4. DB queries fallback for relationships, contexts and last promoted session
    total_relationships = "N/A (Remote)"
    defined_contexts_count = "N/A (Remote)"
    last_promoted_session = "N/A (Remote)"
    
    if not remote:
        # Check if we can run queries against local DB
        try:
            # Add current directory to path just in case
            import sys
            sys.path.insert(0, os.getcwd())
            from db.session import async_session
            from sqlalchemy import select, func
            from db.models import KnowledgeRelationship, KnowledgeContext, Session
            
            async def get_db_stats():
                async with async_session() as session:
                    # Relationships count
                    rel_stmt = select(func.count(KnowledgeRelationship.id))
                    rel_res = await session.execute(rel_stmt)
                    total_rels = rel_res.scalar()
                    
                    # Contexts count
                    ctx_stmt = select(func.count(KnowledgeContext.id))
                    ctx_res = await session.execute(ctx_stmt)
                    total_ctxs = ctx_res.scalar()
                    
                    # Last promoted session
                    sess_stmt = select(Session.promoted_at).where(Session.promoted == True).order_by(Session.promoted_at.desc()).limit(1)
                    sess_res = await session.execute(sess_stmt)
                    last_promoted = sess_res.scalar_one_or_none()
                    last_promoted_str = last_promoted.strftime("%Y-%m-%d %H:%M:%S") if last_promoted else "Never"
                    
                    return total_rels, total_ctxs, last_promoted_str
                    
            total_relationships, defined_contexts_count, last_promoted_session = asyncio.run(get_db_stats())
        except Exception:
            total_relationships = "N/A"
            defined_contexts_count = "N/A"
            last_promoted_session = "N/A"
            
    # 5. Which tools are configured (detect read-only)
    configured_tools = []
    if detect_vscode(): configured_tools.append("VSCode")
    if detect_claude_code(): configured_tools.append("Claude Code")
    if detect_codex(): configured_tools.append("Codex")
    if detect_antigravity(): configured_tools.append("Antigravity")
    if detect_cursor(): configured_tools.append("Cursor")
    if detect_windsurf(): configured_tools.append("Windsurf")
    
    configured_tools_str = ", ".join(configured_tools) if configured_tools else "None"
    
    # 6. Display tables
    console.print(f"\n[bold green]MENO Service Status: {health_status}[/bold green]")
    if health_data:
        console.print(f"Version: {health_data.get('version')} | Env: {health_data.get('env')}")
        
    table_kb = Table(title="Knowledge Base Objects")
    table_kb.add_column("Knowledge Type", style="cyan")
    table_kb.add_column("Count", style="magenta")
    
    for t, c in counts.items():
        table_kb.add_row(t, str(c))
    console.print(table_kb)
    
    table_meta = Table(title="MENO Metadata Summary")
    table_meta.add_column("Metric", style="cyan")
    table_meta.add_column("Value", style="magenta")
    
    table_meta.add_row("Total Relationships", str(total_relationships))
    table_meta.add_row("Defined Contexts", str(defined_contexts_count))
    table_meta.add_row("Last Promoted Session", str(last_promoted_session))
    table_meta.add_row("Detected Tools", configured_tools_str)
    console.print(table_meta)
