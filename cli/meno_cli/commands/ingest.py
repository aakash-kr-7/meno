# ==============================================================================
# (a) What this file is: meno ingest subcommand.
# (b) What it does: meno ingest <path> — seeds MENO with existing project knowledge. Selectivity over coverage.
# (c) How it fits into the MENO system: Imports project source files and documents into MENO knowledge store.
# ==============================================================================

import os
import fnmatch
import typer
import httpx
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.progress import Progress

console = Console()

def is_binary(file_path: str) -> bool:
    """Checks if a file is binary using extensions and null-byte scans."""
    _, ext = os.path.splitext(file_path)
    if ext.lower() in [
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".tar", ".gz",
        ".7z", ".exe", ".dll", ".so", ".dylib", ".pyc", ".db", ".sqlite",
        ".woff", ".ttf", ".eot", ".mp3", ".mp4", ".wav", ".avi", ".mov", ".bin"
    ]:
        return True
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(8000)
            if b"\x00" in chunk:
                return True
    except Exception:
        return True
    return False

def get_comments_length(content: str, ext: str) -> int:
    """Heuristic extraction of comments and docstrings length."""
    length = 0
    if ext == ".py":
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                length += len(stripped) - 1
        import re
        triple_double = re.findall(r'"""(.*?)"""', content, re.DOTALL)
        triple_single = re.findall(r"'''(.*?)'''", content, re.DOTALL)
        for doc in triple_double + triple_single:
            length += len(doc)
    elif ext in (".js", ".ts", ".go", ".rs"):
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("//"):
                length += len(stripped) - 2
        import re
        blocks = re.findall(r'/\*(.*?)\*/', content, re.DOTALL)
        for block in blocks:
            length += len(block)
    return length

def parse_gitignore(root_path: str) -> List[str]:
    """Reads and parses .gitignore from the root directory."""
    patterns = []
    gitignore_path = os.path.join(root_path, ".gitignore")
    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line)
        except Exception:
            pass
    return patterns

def matches_ignore(rel_path: str, gitignore_patterns: List[str]) -> bool:
    """Matches relative path against default and gitignore patterns."""
    # Normalize paths to use forward slashes for matching
    rel_path_norm = rel_path.replace(os.sep, "/")
    parts = rel_path_norm.split("/")
    
    # Default directories to skip
    default_skips = {".git", "node_modules", "vendor", "build", "dist", "__pycache__"}
    if any(part in default_skips for part in parts):
        return True
        
    for pattern in gitignore_patterns:
        # Normalize pattern
        pattern_norm = pattern.replace(os.sep, "/")
        if pattern_norm.endswith("/"):
            pattern_match = pattern_norm[:-1]
        else:
            pattern_match = pattern_norm
            
        # Match pattern as glob on path
        if fnmatch.fnmatch(rel_path_norm, pattern_match) or fnmatch.fnmatch(rel_path_norm, f"*/{pattern_match}"):
            return True
            
        for part in parts:
            if fnmatch.fnmatch(part, pattern_match):
                return True
                
    return False

def determine_knowledge_type(rel_path: str, content: str) -> Optional[str]:
    """Determines the MENO knowledge type for a file if it matches filters."""
    rel_path_norm = rel_path.replace(os.sep, "/")
    filename = os.path.basename(rel_path)
    _, ext = os.path.splitext(filename)
    
    # 1. DECISION: docs/decisions/ or adr/
    if "docs/decisions/" in rel_path_norm or "adr/" in rel_path_norm:
        return "decision"
        
    # 2. ARCHITECTURE: README.md, ARCHITECTURE.md, docs/*.md
    if filename in ("README.md", "ARCHITECTURE.md") or (rel_path_norm.startswith("docs/") and filename.endswith(".md")):
        return "architecture"
        
    # 3. CODE_PATTERN: .py/.rs/.go/.ts with docstrings/comments > 50 chars
    if ext in (".py", ".rs", ".go", ".ts"):
        comments_len = get_comments_length(content, ext)
        if comments_len > 50:
            return "code_pattern"
            
    return None

def ingest_path(root_path: str, api_url: str, headers: Dict[str, str]) -> int:
    """Walks the path, scans and ingests matching knowledge items."""
    root_path = os.path.abspath(root_path)
    gitignore_patterns = parse_gitignore(root_path)
    
    files_to_process = []
    
    if os.path.isfile(root_path):
        rel_path = os.path.basename(root_path)
        if not is_binary(root_path):
            files_to_process.append((root_path, rel_path))
    else:
        for dirpath, dirnames, filenames in os.walk(root_path):
            # Prune directory walk using default skips
            dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "vendor", "build", "dist", "__pycache__")]
            
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(full_path, root_path)
                
                # Check ignores
                if matches_ignore(rel_path, gitignore_patterns):
                    continue
                    
                if is_binary(full_path):
                    continue
                    
                files_to_process.append((full_path, rel_path))
                
    ingested_count = 0
    processed_files_count = 0
    
    if not files_to_process:
        console.print("[yellow]No suitable files found for ingestion.[/yellow]")
        return 0
        
    with Progress() as progress:
        task = progress.add_task("[cyan]Ingesting files...", total=len(files_to_process))
        
        for full_path, rel_path in files_to_process:
            progress.update(task, advance=1, description=f"[cyan]Ingesting {rel_path}...")
            processed_files_count += 1
            
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
                
            k_type = determine_knowledge_type(rel_path, content)
            if not k_type:
                continue
                
            # POST to /knowledge/store
            payload = {
                "tenant_id": "default",
                "user_id": "default_user",
                "type": k_type,
                "content": content,
                "title": os.path.basename(rel_path),
                "source_type": "file",
                "source_id": rel_path,
                "source_context": {"path": rel_path},
                "confidence": 0.8,
                "tags": [k_type],
                "metadata": {"path": rel_path}
            }
            
            try:
                resp = httpx.post(f"{api_url.rstrip('/')}/knowledge/store", json=payload, headers=headers, timeout=10.0)
                if resp.status_code == 201 or resp.status_code == 200:
                    ingested_count += 1
            except Exception as e:
                # Silently skip file if store fails to connect
                pass
                
    console.print(f"[green]Ingested {ingested_count} objects from {processed_files_count} files.[/green]")
    return ingested_count

def ingest_cmd(
    path: str = typer.Argument(".", help="Path to seed MENO with"),
    remote: Optional[str] = typer.Option(None, "--remote", help="Remote API URL to use instead of default localhost"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key for authentication")
):
    """
    Seeds MENO with existing project knowledge. Selectivity over coverage.
    """
    api_url = remote if remote else "http://localhost:8000"
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    elif os.getenv("MENO_API_KEY"):
        headers["X-API-Key"] = os.getenv("MENO_API_KEY")
        
    ingest_path(path, api_url, headers)
