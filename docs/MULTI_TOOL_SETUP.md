<!-- ==============================================================================
(a) What this file is: Multi-tool setup documentation for MENO.
(b) What it does: Guides developers and teams through configuring multiple AI coding editors/clients to use a shared MENO knowledge store.
(c) How it fits into the MENO system: Serves as the central user manual for multi-tool integration.
============================================================================== -->

# MENO — Multi-Tool Setup & Integration Guide

AI coding tool credits run out. You switch tools. All context is lost. Every switch is a re-explanation event. At team scale, knowledge lives inside individual chat histories that no one else can see.

MENO resolves this by acting as a single, unified database of structured memory. By configuring all your AI editors to speak to the same local or remote MENO instance via the Model Context Protocol (MCP), your architectural decisions, code patterns, and bug reports survive the switch.

---

## 1. Supported Client Tools Configuration

MENO supports both local (`stdio` transport) and remote (`HTTP/SSE` transport) integrations. Below are the configurations for all major AI-supported editors and agents:

### 1.1. VS Code / Copilot Chat
* **Config File**: `.vscode/mcp.json`
* **JSON Snippet**:
  ```json
  {
    "servers": {
      "meno": {
        "command": "python",
        "args": [
          "-m",
          "apps.mcp"
        ]
      }
    }
  }
  ```

### 1.2. Claude Code (CLI)
Claude Code interacts with MCP servers using command-line arguments.
* **Command to Add Local Server**:
  ```bash
  claude mcp add meno -- python -m apps.mcp
  ```
* **Command to Add Remote Server**:
  ```bash
  claude mcp add meno https://meno.yourteam.internal
  ```

### 1.3. Claude Desktop
* **Config File**: 
  - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
  - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
* **JSON Snippet**:
  ```json
  {
    "mcpServers": {
      "meno": {
        "command": "python",
        "args": [
          "-m",
          "apps.mcp"
        ]
      }
    }
  }
  ```

### 1.4. Cursor
Cursor configures MCP servers via its settings interface or using local project config files.
* **Config File**: `.cursor/mcp.json`
* **JSON Snippet**:
  ```json
  {
    "mcpServers": {
      "meno": {
        "command": "python",
        "args": [
          "-m",
          "apps.mcp"
        ]
      }
    }
  }
  ```

### 1.5. Windsurf
* **Config File**: `.windsurf/mcp.json`
* **JSON Snippet**:
  ```json
  {
    "mcpServers": {
      "meno": {
        "command": "python",
        "args": [
          "-m",
          "apps.mcp"
        ]
      }
    }
  }
  ```

### 1.6. Google Antigravity
* **Config File**: Located in your project root or user home: `.gemini/antigravity*/mcp_config.json`
* **JSON Snippet**:
  ```json
  {
    "mcpServers": {
      "meno": {
        "command": "python",
        "args": [
          "-m",
          "apps.mcp"
        ]
      }
    }
  }
  ```

### 1.7. OpenAI Codex CLI/IDE
* **Config File**: `.codex/config.toml`
* **TOML Snippet**:
  ```toml
  [mcp.servers.meno]
  command = "python"
  args = ["-m", "apps.mcp"]
  ```

---

## 2. Solo Developer Setup (Local Mode)

If you are running MENO locally on your machine, bootstrapping takes 1 minute:

1. **Install CLI and Initialize**:
   ```bash
   pip install meno-cli
   meno init
   ```
   *Note: `meno init` will bring up the docker-compose services (PostgreSQL + Redis), poll the FastAPI health endpoint until it is online, scan the current workspace for installed editors, and automatically write their config files.*

2. **Ingest Workspace**:
   Seed MENO with your repository files (like `README.md`, `ARCHITECTURE.md`, docs, and well-commented scripts):
   ```bash
   meno ingest .
   ```

---

## 3. Team Deployment (Remote Mode)

Teams can deploy a shared MENO instance to central cloud providers (like Railway, Render, or Fly.io) to synchronize database states across developer machines.

### 3.1. Deploying the Shared Server
1. **Infrastructure**: Provision a PostgreSQL database (enable the `pgvector` plugin) and a Redis cache.
2. **Environment Variables**:
   ```env
   APP_ENV=production
   SECRET_KEY=your_secure_hash_token_here
   DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname
   REDIS_URL=redis://host:port
   ```
3. **Deploy Container**: Build and deploy using the root `Dockerfile` or link `docker-compose.yml` configurations.

### 3.2. Connecting Teammates to the Shared Server
Each developer installs the CLI and connects directly to the remote URL:
```bash
pip install meno-cli
meno init --remote https://meno.yourteam.internal
```
When prompted, input the `SECRET_KEY` configured on the server. The CLI will automatically construct the remote SSE configuration payload:
```json
{
  "url": "https://meno.yourteam.internal",
  "headers": {
    "X-API-Key": "your_secure_hash_token_here"
  }
}
```

---

## 4. Diagnostics & Troubleshooting

If you experience configuration errors, use this reference checklist to resolve them:

| Symptom | Root Cause | Resolution |
| :--- | :--- | :--- |
| **Tool fails to load MCP server** | Command `python` points to system python rather than your virtual environment. | Modify the client configuration file to point directly to the virtual environment's Python executable path (e.g., `"command": "/absolute/path/to/meno/venv/bin/python"`). |
| **Knowledge not appearing across tools** | The tool sessions are querying distinct scoping contexts. | Check that all client commands query with the same `tenant_id` and matching `user_id`. Ensure you run `meno_define_context` on new workspaces. |
| **Local server fails on `meno init`** | Docker is not active or user has port conflicts on `5432` (Postgres) or `6379` (Redis). | Run `docker ps` to verify container statuses. Free standard ports on the host machine or modify mapping values in `docker-compose.yml`. |
| **Remote connections yield 401 Unauthorized** | The client `X-API-Key` header does not match the server's `SECRET_KEY`. | Verify the value passed during `meno init --remote` or check client config headers directly. |
| **Python package import errors** | CLI running from an isolated system path. | Run `sys.path.insert(0, os.getcwd())` inside your execution script or run commands from the project root folder. |
