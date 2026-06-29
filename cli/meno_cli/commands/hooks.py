# ==============================================================================
# (a) What this file is: meno hooks subcommand.
# (b) What it does: meno hooks install — git post-commit hook for tool-agnostic knowledge capture. Runs hook-capture hidden command to extract and store git commit details offline.
# (c) How it fits into the MENO system: Automates background knowledge capture on every git commit.
# ==============================================================================

import os
import sys
import subprocess
import asyncio
import typer
import httpx
from typing import Optional
from rich.console import Console

console = Console()
hooks_app = typer.Typer(help="Manage MENO Git hooks.")

@hooks_app.command(name="install")
def hooks_install():
    """
    Installs the git post-commit hook for tool-agnostic knowledge capture.
    """
    if not os.path.exists(".git"):
        console.print("[bold red]Error: Not a git repository (no .git folder found).[/bold red]")
        raise typer.Exit(1)
        
    hooks_dir = ".git/hooks"
    os.makedirs(hooks_dir, exist_ok=True)
    
    hook_path = os.path.join(hooks_dir, "post-commit")
    
    # Write shell script hook (POSIX standard, works in Git Bash/Windows as well)
    hook_content = (
        "#!/bin/sh\n"
        "meno hook-capture $(git rev-parse HEAD) 2>/dev/null || true\n"
    )
    
    try:
        with open(hook_path, "w", newline="\n", encoding="utf-8") as f:
            f.write(hook_content)
        # Make executable
        os.chmod(hook_path, 0o755)
        console.print("Git hook installed.")
    except Exception as e:
        console.print(f"[bold red]Failed to write git hook: {e}[/bold red]")
        raise typer.Exit(1)

def hook_capture_cmd(
    commit_hash: str,
    remote: Optional[str] = typer.Option(None, "--remote", help="Remote API URL to use instead of default localhost")
):
    """
    Hidden subcommand called by the git post-commit hook.
    Extracts commit details, performs rule-based extraction, and stores the knowledge objects.
    """
    # CRITICAL: wrap everything in try-except to never exit non-zero (which would abort/pollute git commit)
    try:
        # Resolve Python path to load core packages
        sys.path.insert(0, os.getcwd())
        from core.llm import _rule_based_extract
        
        # 1. Get commit message
        msg_res = subprocess.run(
            ["git", "log", "-1", "--format=%B", commit_hash],
            capture_output=True,
            text=True,
            check=True
        )
        commit_msg = msg_res.stdout.strip()
        
        # 2. Get changed files summary
        diff_res = subprocess.run(
            ["git", "diff", f"{commit_hash}~1", commit_hash, "--stat"],
            capture_output=True,
            text=True,
            check=True
        )
        changed_files = diff_res.stdout.strip()
        
        # 3. Create synthetic message
        synthetic_message = (
            f"Git Commit Details:\n"
            f"Message: {commit_msg}\n\n"
            f"Changes:\n{changed_files}"
        )
        
        # 4. Extract knowledge
        # _rule_based_extract is async and expects list[dict]
        messages = [{"role": "user", "content": synthetic_message}]
        extracted = asyncio.run(_rule_based_extract(messages))
        
        if not extracted:
            sys.exit(0)
            
        # 5. POST to /knowledge/store
        api_url = remote if remote else "http://localhost:8000"
        api_key = os.getenv("MENO_API_KEY")
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key
            
        for obj in extracted:
            payload = {
                "tenant_id": "default",
                "user_id": "default_user",
                "type": obj.type,
                "content": obj.content,
                "title": obj.title,
                "source_type": "git_commit",
                "source_id": commit_hash,
                "source_context": {
                    "commit": commit_hash,
                    "message": commit_msg,
                    "changes": changed_files
                },
                "confidence": obj.confidence,
                "tags": obj.tags
            }
            try:
                # Use a small timeout so we do not block git committing too long
                resp = httpx.post(f"{api_url.rstrip('/')}/knowledge/store", json=payload, headers=headers, timeout=5.0)
                resp.raise_for_status()
            except Exception as e:
                sys.stderr.write(f"MENO hook-capture warning: failed to store knowledge: {e}\n")
                
    except Exception as e:
        # Write to stderr, but exit with 0 to make sure git commit NEVER fails
        sys.stderr.write(f"MENO hook-capture warning: {e}\n")
        sys.exit(0)
        
    sys.exit(0)
