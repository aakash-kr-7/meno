# ==============================================================================
# (a) What this file is: meno init subcommand.
# (b) What it does: meno init — bootstraps MENO in the current project. Brings up Docker, generates .env if missing, detects and configures all present AI tools.
# (c) How it fits into the MENO system: Serves as the bootstrapping command to get MENO running and integrated.
# ==============================================================================

import os
import time
import shutil
import subprocess
import typer
import httpx
from typing import Optional
from rich.console import Console
from rich.table import Table

from meno_cli.detect import (
    STDIO_ENTRY,
    get_remote_entry,
    run_all_detectors_and_write,
    detect_vscode,
    detect_claude_code,
    detect_codex,
    detect_antigravity,
    detect_cursor,
    detect_windsurf
)
from meno_cli.commands.ingest import ingest_path

console = Console()

def init_cmd(
    remote: Optional[str] = typer.Option(None, "--remote", help="Configure MENO as a remote HTTP streamable engine at this URL"),
    verbose: bool = typer.Option(False, "--verbose", help="Show all docker-compose/subprocess logs")
):
    """
    Bootstraps MENO in the current project.
    Brings up Docker, generates .env if missing, detects and configures all present AI tools.
    """
    entry = STDIO_ENTRY
    is_remote = remote is not None
    
    if is_remote:
        console.print(f"[bold blue]Setting up MENO in remote mode at {remote}...[/bold blue]")
        # Prompt for API key
        api_key = typer.prompt("Enter MENO API Key", hide_input=True)
        entry = get_remote_entry(remote, api_key)
    else:
        console.print("[bold blue]Setting up MENO locally...[/bold blue]")
        
        # 1. Check docker available
        if not shutil.which("docker"):
            console.print("[bold red]Error: 'docker' is not available. Please install Docker first.[/bold red]")
            raise typer.Exit(1)
            
        try:
            res = subprocess.run(["docker", "--version"], capture_output=True, text=True, check=True)
        except subprocess.SubprocessError:
            console.print("[bold red]Error: Docker is installed but not running or accessible.[/bold red]")
            raise typer.Exit(1)
            
        # 2. Generate .env from .env.example if absent
        if not os.path.exists(".env"):
            if os.path.exists(".env.example"):
                console.print("Generating .env from .env.example...")
                shutil.copy(".env.example", ".env")
            else:
                console.print("[yellow]Warning: .env and .env.example are both missing. Creating dummy .env...[/yellow]")
                with open(".env", "w") as f:
                    f.write("DATABASE_URL=postgresql+asyncpg://meno:meno@localhost:5432/meno\n")
                    
        # 3. docker compose up -d --build
        console.print("Starting docker containers (docker compose up -d --build)...")
        compose_cmd = ["docker", "compose", "up", "-d", "--build"]
        stdout_dest = None if verbose else subprocess.DEVNULL
        stderr_dest = None if verbose else subprocess.DEVNULL
        
        try:
            subprocess.run(compose_cmd, stdout=stdout_dest, stderr=stderr_dest, check=True)
        except subprocess.SubprocessError as e:
            console.print(f"[bold red]Error: Failed to start docker containers. {e}[/bold red]")
            raise typer.Exit(1)
            
        # 4. Poll health endpoint until 200 (max 60s)
        console.print("Waiting for MENO API to be healthy (polling /health)...")
        start_time = time.time()
        healthy = False
        while time.time() - start_time < 60:
            try:
                resp = httpx.get("http://localhost:8000/health", timeout=2.0)
                if resp.status_code == 200:
                    healthy = True
                    break
            except Exception:
                pass
            time.sleep(1.0)
            
        if not healthy:
            console.print("[bold red]Error: MENO API health check timed out after 60 seconds.[/bold red]")
            raise typer.Exit(1)
            
        console.print("[green]MENO API is healthy and running![/green]")

    # 5. Run detectors & write configs
    configured_tools = run_all_detectors_and_write(entry)
    
    # 6. Print rich table: Tool | Status (configured / not detected)
    all_tools = {
        "VSCode": detect_vscode(),
        "Claude Code": detect_claude_code(),
        "Codex": detect_codex(),
        "Antigravity": detect_antigravity(),
        "Cursor": detect_cursor(),
        "Windsurf": detect_windsurf()
    }
    
    table = Table(title="MENO Tool Configuration Status")
    table.add_column("Tool", style="cyan")
    table.add_column("Status", style="magenta")
    
    for tool_name, detected_val in all_tools.items():
        if tool_name in configured_tools:
            status_text = f"[green]configured[/green] ({configured_tools[tool_name]})" if "configured (" in configured_tools[tool_name] else "[green]configured[/green]"
        elif detected_val:
            status_text = "[yellow]detected but not configured[/yellow]"
        else:
            status_text = "[dim]not detected[/dim]"
        table.add_row(tool_name, status_text)
        
    console.print(table)
    
    # 7. typer.confirm to run ingest
    if typer.confirm("Would you like to seed MENO with the current project directory (run ingest)?"):
        # run ingest against '.'
        # if remote is specified, pass the URL and key
        api_url = remote if remote else "http://localhost:8000"
        headers = {"X-API-Key": api_key} if is_remote else {}
        ingest_path(".", api_url, headers)
