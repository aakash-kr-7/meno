<!-- MENO project instructions for AI coding agents. Read by Copilot, Codex, and compatible tools. Keep under 15 lines — read on every turn. -->

This project uses MENO for persistent knowledge.
Before starting any non-trivial task:

1. Call meno_retrieve with a query describing what you are about to do.
2. Check for existing decisions, patterns, or bug fixes before re-deriving them.
   After completing a task involving a decision, pattern, or bug fix:
3. Call meno_store with the appropriate type (decision/code_pattern/bug_report/etc).
   Before ending a long session or switching tools:
4. Call meno_promote_session to extract structured knowledge from this session.
   The knowledge graph is the source of truth. Prefer it over re-deriving.
