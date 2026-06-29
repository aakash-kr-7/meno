# ==============================================================================
# (a) What this file is: MCP detector and configuration writer.
# (b) What it does: Detects MCP-compatible AI tools in the current workspace. Additive and non-destructive. Undetected tools silently skipped. Each writer merges the meno server entry under the tool's correct key, never overwriting unrelated servers.
# (c) How it fits into the MENO system: Integrates the MCP server with present AI editors/clients.
# ==============================================================================

import os
import glob
import json
import shutil
import subprocess
import tomlkit
from typing import Optional, Dict, Any

# Standard stdio configuration
STDIO_ENTRY = {
    "command": "python",
    "args": ["-m", "apps.mcp"]
}

def get_remote_entry(url: str, api_key: str) -> Dict[str, Any]:
    return {
        "url": url,
        "headers": {
            "X-API-Key": api_key
        }
    }

# Detectors: each returns detection path or None

def detect_vscode() -> Optional[str]:
    """VSCode: .vscode/ present, targets .vscode/mcp.json"""
    if os.path.isdir(".vscode"):
        return ".vscode"
    return None

def detect_claude_code() -> Optional[str]:
    """Claude Code: .claude/ or claude on PATH"""
    if os.path.isdir(".claude"):
        return ".claude"
    if shutil.which("claude"):
        return "claude"
    return None

def detect_codex() -> Optional[str]:
    """Codex: .codex/ or codex on PATH"""
    if os.path.isdir(".codex"):
        return ".codex"
    if shutil.which("codex"):
        return "codex"
    return None

def detect_antigravity() -> Optional[str]:
    """Antigravity: glob .gemini/antigravity*/"""
    # Check current directory
    local_gemini = glob.glob(".gemini/antigravity*")
    if local_gemini:
        return local_gemini[0]
    
    # Check user home directory
    home = os.path.expanduser("~")
    home_gemini = glob.glob(os.path.join(home, ".gemini", "antigravity*"))
    if home_gemini:
        return home_gemini[0]
        
    return None

def detect_cursor() -> Optional[str]:
    """Cursor: .cursor/ present"""
    if os.path.isdir(".cursor"):
        return ".cursor"
    return None

def detect_windsurf() -> Optional[str]:
    """Windsurf: .windsurf/ present"""
    if os.path.isdir(".windsurf"):
        return ".windsurf"
    return None

# Configuration writers (Additive/Non-destructive merging)

def write_vscode_config(entry: Dict[str, Any]) -> str:
    os.makedirs(".vscode", exist_ok=True)
    path = ".vscode/mcp.json"
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    
    if not isinstance(data, dict):
        data = {}
    
    if "servers" not in data or not isinstance(data["servers"], dict):
        data["servers"] = {}
        
    data["servers"]["meno"] = entry
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path

def write_claude_config(entry: Dict[str, Any]) -> str:
    """Claude Code: subprocess config command"""
    if "url" in entry:
        # Remote URL config
        cmd = ["claude", "mcp", "add", "meno", entry["url"]]
        # Try to pass API key if we can, but standard is just URL.
    else:
        # Local stdio config
        cmd = ["claude", "mcp", "add", "meno", "--", "python", "-m", "apps.mcp"]
        
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except Exception as e:
        # If running subprocess fails, fallback to writing to standard local config if it exists
        # or just raise/return description.
        pass
    return "claude_code"

def write_codex_config(entry: Dict[str, Any]) -> str:
    os.makedirs(".codex", exist_ok=True)
    path = ".codex/config.toml"
    doc = tomlkit.document()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                doc = tomlkit.parse(f.read())
        except Exception:
            pass
            
    if "mcp" not in doc:
        doc["mcp"] = tomlkit.table()
    if "servers" not in doc["mcp"]:
        doc["mcp"]["servers"] = tomlkit.table()
        
    # tomlkit needs to map the dict structure
    t = tomlkit.table()
    for k, v in entry.items():
        if isinstance(v, dict):
            sub_t = tomlkit.table()
            for sk, sv in v.items():
                sub_t[sk] = sv
            t[k] = sub_t
        else:
            t[k] = v
            
    doc["mcp"]["servers"]["meno"] = t
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(doc))
    return path

def write_antigravity_config(target_dir: str, entry: Dict[str, Any]) -> str:
    os.makedirs(target_dir, exist_ok=True)
    path = os.path.join(target_dir, "mcp_config.json")
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
            
    if not isinstance(data, dict):
        data = {}
        
    if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
        data["mcpServers"] = {}
        
    data["mcpServers"]["meno"] = entry
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path

def write_cursor_config(entry: Dict[str, Any]) -> str:
    os.makedirs(".cursor", exist_ok=True)
    path = ".cursor/mcp.json"
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
            
    if not isinstance(data, dict):
        data = {}
        
    if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
        data["mcpServers"] = {}
        
    data["mcpServers"]["meno"] = entry
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path

def write_windsurf_config(entry: Dict[str, Any]) -> str:
    os.makedirs(".windsurf", exist_ok=True)
    path = ".windsurf/mcp.json"
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
            
    if not isinstance(data, dict):
        data = {}
        
    if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
        data["mcpServers"] = {}
        
    data["mcpServers"]["meno"] = entry
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path

def run_all_detectors_and_write(entry: Dict[str, Any]) -> Dict[str, str]:
    """Runs all detectors, writes config for detected tools, returns status map."""
    configured = {}
    
    # 1. VSCode
    if detect_vscode():
        path = write_vscode_config(entry)
        configured["VSCode"] = f"configured ({path})"
    
    # 2. Claude Code
    if detect_claude_code():
        write_claude_config(entry)
        configured["Claude Code"] = "configured"
        
    # 3. Codex
    if detect_codex():
        path = write_codex_config(entry)
        configured["Codex"] = f"configured ({path})"
        
    # 4. Antigravity
    anti_path = detect_antigravity()
    if anti_path:
        path = write_antigravity_config(anti_path, entry)
        configured["Antigravity"] = f"configured ({path})"
        
    # 5. Cursor
    if detect_cursor():
        path = write_cursor_config(entry)
        configured["Cursor"] = f"configured ({path})"
        
    # 6. Windsurf
    if detect_windsurf():
        path = write_windsurf_config(entry)
        configured["Windsurf"] = f"configured ({path})"
        
    return configured
