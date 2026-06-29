<!-- OpenAI Codex CLI and IDE — shared config between both -->
CLI: codex mcp add meno -- python -m apps.mcp
Or add to .codex/config.toml:
[mcp.servers.meno]
command = "python"
args = ["-m", "apps.mcp"]
