<!-- ==============================================================================
(a) What this file is: Multi-tool setup documentation for MENO.
(b) What it does: Guides developers and teams through configuring multiple AI coding editors/clients to use a shared MENO knowledge store.
(c) How it fits into the MENO system: Serves as the central user manual for multi-tool integration.
============================================================================== -->

<!-- MENO — Multi-Tool Setup Guide -->
# MENO Multi-Tool Setup

## The Problem
AI coding tool credits run out. You switch tools. All context is lost. Every switch is a re-explanation event. At team scale, knowledge lives inside individual chat histories no one else can see.

## The Fix
One MENO instance. Any MCP-compatible tool. Knowledge survives the switch.

## Supported Tools

| Tool | Transport | Config Location | Key |
|-----------------------|-----------|----------------------------------------------|------------|
| VS Code / Copilot | stdio | .vscode/mcp.json | servers |
| Claude Code | stdio | claude mcp add command | — |
| Claude Desktop | stdio | claude_desktop_config.json | mcpServers |
| Codex CLI/IDE | stdio | .codex/config.toml | mcp.servers|
| Google Antigravity | stdio | .gemini/antigravity*/mcp_config.json | mcpServers |
| Cursor | stdio | .cursor/mcp.json | mcpServers |
| Windsurf | stdio | .windsurf/mcp.json | mcpServers |
| Any tool (team) | HTTP | each tool's remote server config | varies |

## Solo Quick Start (1 minute)
```bash
pip install meno-cli
meno init
```

## Team Quick Start

### On the shared host:
```bash
docker compose up --build
```

### Each teammate:
```bash
pip install meno-cli
meno init --remote https://meno.yourteam.internal
```

## Troubleshooting
- **Tool not detecting MCP server**: check that tool's MCP log; verify config path and key name.
- **Knowledge not appearing across tools**: confirm both tools use the same `tenant_id`.
- **`python -m apps.mcp` fails**: run it in shell first to see the error.
- **HTTP transport 401**: `X-API-Key` header must match `SECRET_KEY` in `.env`.
