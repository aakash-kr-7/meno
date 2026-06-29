<!-- Claude Code and Claude Desktop MCP configuration -->
Claude Code:
claude mcp add meno -- python -m apps.mcp
(run from project root)
Claude Desktop — add to mcpServers in config file:
macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
Windows: %APPDATA%\Claude\claude_desktop_config.json
Block: {"mcpServers": {"meno": {"command": "python", "args": ["-m", "apps.mcp"]}}}
