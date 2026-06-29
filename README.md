<!--
(a) What this file is: MENO System README.md.
(b) What it does: Serves as the primary documentation entrypoint, detailing architecture, knowledge types, setup, python SDK usage, running demos, tests, and future roadmaps.
(c) How it fits into the MENO system: Global user-facing documentation located at the project root.
-->

# MENO — Persistent Intelligence Platform

> Persistent intelligence infrastructure for humans, AI agents, codebases, and organizations.

MENO bridges the gap between transient conversation context and long-term repository knowledge. By extracting structured decisions, architectures, bug reports, and code patterns from developers' interactions and codebase histories, MENO forms a contextually aware, queryable knowledge graph with type-aware decay ranking.

---

## What Makes MENO Different

Traditional systems treat context as transient chat history (working memory) or generic vector embeddings without relationship edges. MENO divides memory into structured layers, separating immediate conversation details from long-term verified facts.

| Dimension | Working Memory (Tier 0) | Extracted Knowledge (Tier 1-2) | Persistent Intelligence (Tier 3) |
|---|---|---|---|
| **Focus** | Session context & message history | Verified facts, decisions, structures | Cross-context heuristics & patterns |
| **Storage** | Redis + PostgreSQL | PostgreSQL + pgvector | Graph + Relational Summaries |
| **Lifespan** | Temporary (Evicts on inactivity) | Configurable (Ages with half-life decay) | Permanent |
| **Search Mode** | Key-Value / Session ID Lookup | Cosine Vector Search + Type-Aware Re-ranking | Graph Traversal (BFS) / Narrative Walking |

---

## Quick Start

Get MENO up and running in less than 5 minutes.

### 1. Clone & Configure
```bash
git clone https://github.com/aakash-kr-7/meno.git
cd meno
cp .env.example .env
```

### 2. Launch Services
Spin up the PostgreSQL (pgvector enabled) and Redis instances:
```bash
docker compose up --build -d
```
Check health by visiting: `http://localhost:8000/health` (requires a `200 OK` return with a `"tiers"` object).

### 3. Initialize in 3 lines of Python SDK
```python
from meno import Meno
sdk = Meno(base_url="http://localhost:8000")
sdk.store(user_id="user_123", content="We decided to cache DB calls.", type="decision")
```

---

## Architecture Overview

MENO's storage and processing flow are organized into distinct layers (Tiers):

| Tier | Name | Engine / Technology | Purpose |
|---|---|---|---|
| **Tier 0** | Working Memory | Redis (Cache) + PostgreSQL | Immediate chat context, messages cache, and session logs. |
| **Tier 1** | Scoped Knowledge | PostgreSQL + pgvector (BAAI/bge-small-en-v1.5) | Vector search of specific context objects (code patterns, decisions). |
| **Tier 2** | Relationship Graph | PostgreSQL Foreign Keys + BFS traversal | Graph connections linking objects together (e.g. DECISION implements CODE_PATTERN). |
| **Tier 3** | Behavioral Profiles | PostgreSQL JSONB + Context Heuristics | User-specific context lengths, preferences, and language tones. |

For a deep-dive design blueprint, view the complete [ARCHITECTURE.md](file:///c:/Users/aakash09/Desktop/meno/ARCHITECTURE.md).

---

## Knowledge Types & Ranking

Not all knowledge ages equally. A software architecture decision is relevant for months, whereas a temporary bug report decays quickly. MENO applies a type-aware decay function using configurable half-lives:

| Type | Use Case | Ranking Half-Life |
|---|---|---|
| **`decision`** | Key architectural or business choices. | 180 Days |
| **`architecture`**| Overall system designs, components, and module relations. | 180 Days |
| **`api_spec`** | API contracts, endpoints, schemas, or interfaces. | 90 Days |
| **`code_pattern`** | Code decorators, caching designs, batch configurations. | 60 Days |
| **`refactoring`** | Refactoring actions, codebase cleanup, simplifications. | 60 Days |
| **`bug_report`** | Database pool issues, memory leaks, crashing stacktraces. | 30 Days |
| **`memory`** | Conversations, general statements, transient observations. | 7 Days |

---

## API Reference

All requests must pass authentication (handled via the `X-API-Key` header when enabled).

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Server status, version, active env, and tiers configuration. |
| `POST`| `/knowledge/store` | Store a new typed knowledge object scoped to contexts. |
| `POST`| `/knowledge/retrieve` | Semantic vector search with type-aware decay re-ranking. |
| `POST`| `/knowledge/search/structured` | Structured search by type, context, and limits. |
| `GET` | `/knowledge/{object_id}` | Fetch a specific knowledge object and its graph edges. |
| `DELETE`| `/knowledge/{object_id}` | Remove a specific knowledge object from store. |
| `POST`| `/knowledge/relate` | Link two knowledge objects with a typed relationship edge. |
| `GET` | `/knowledge/{object_id}/relationships` | Fetch direct incoming or outgoing relationships. |
| `GET` | `/knowledge/graph/{object_id}` | Walk the graph using BFS out to `max_depth` levels. |
| `POST`| `/context/` | Register a new metadata context (e.g., `project`, `team`). |
| `GET` | `/context/{context_type}/{context_id}` | Fetch context configuration and metadata. |
| `GET` | `/context/{context_uuid}/knowledge` | Retrieve all knowledge objects belonging to a context. |
| `POST`| `/sessions/` | Create a new conversation session. |
| `POST`| `/sessions/{session_id}/messages` | Append a message to active working memory. |
| `GET` | `/sessions/{session_id}` | Get complete message history of a session. |
| `DELETE`| `/sessions/{session_id}` | Expire working memory cache and delete session database rows. |
| `GET` | `/sessions/{session_id}/extracted` | Get all objects promoted from a session. |
| `POST`| `/worker/promote/{session_id}` | Manually trigger extraction pipeline for a session. |
| `POST`| `/worker/promote-all` | Scan and promote all eligible inactive sessions. |
| `GET` | `/profile/{user_id}` | Fetch behavioral preferences and tone metrics. |
| `PATCH`| `/profile/{user_id}` | Update context sizes, tone, preferred language, or custom extra properties. |

---

## Python SDK

To install the SDK locally:
```bash
pip install -e sdk/python
```

### Quick Start Code Block
```python
from meno import Meno, KnowledgeType, RelationshipType

# Initialize MENO Client
sdk = Meno(base_url="http://localhost:8000")

# 1. Store context
ctx = sdk.define_context("project", "sol_demo")

# 2. Store knowledge objects scoped to context
pattern = sdk.store(
    user_id="dev_user",
    content="Use batch processing with chunks of 500.",
    type=KnowledgeType.CODE_PATTERN,
    context_ids=[ctx.id]
)

decision = sdk.store(
    user_id="dev_user",
    content="We chose 500-sized batching chunks to optimize PostgreSQL memory.",
    type=KnowledgeType.DECISION,
    context_ids=[ctx.id]
)

# 3. Create relationship edges
sdk.relate(
    source_id=decision.id,
    target_id=pattern.id,
    relationship_type=RelationshipType.IMPLEMENTS
)

# 4. Semantic query retrieval
results = sdk.retrieve(
    user_id="dev_user",
    query="how to batch insertions in database?",
    context_id=ctx.id,
    expand_relationships=True
)
print("Top Result:", results[0].content)
```

---

## Running the Demo

Ensure docker compose containers are up and running, then execute:
```bash
python examples/demo_knowledge.py
```
This runs the full walkthrough: context registration, object storage, relationship linking, expanded retrieval, graph traversal, and automated session promotion.

---

## Running Tests

All integration and unit tests are run using `pytest`. Ensure Docker Compose services are running before executing:
```bash
pytest tests/ -v
```

---

## Project Structure

```
├── .github/
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md        # Issue template for bugs
│       └── feature_request.md   # Issue template for feature proposals
├── apps/
│   ├── api/                     # FastAPI backend
│   │   ├── middleware/          # Security, auth, & API key middleware
│   │   ├── routes/              # Health, context, knowledge, session routers
│   │   ├── main.py              # Application entrypoint & startup lifespans
│   │   └── schemas.py           # Pydantic v2 schemas
│   ├── mcp/                     # Model Context Protocol integrations (future)
│   └── worker/                  # Session promotion background workers
├── core/                        # Configuration & engine singletons
│   ├── auth.py                  # API Key validation logic
│   ├── config.py                # Environment & settings configurations
│   ├── embeddings.py            # Sentence-Transformers BGE model server
│   ├── llm.py                   # Rule-based & LLM extraction pipelines
│   ├── ranking.py               # Time-decay re-ranking functions
│   └── types.py                 # Canonical Type Enums
├── db/                          # Database connection and model layers
│   ├── migrations/              # Alembic database migration versions
│   ├── models/                  # SQLAlchemy ORM declarations
│   ├── base.py                  # Declarative base mappings
│   └── session.py               # Postgres engine and session makers
├── examples/
│   └── demo_knowledge.py        # Complete SDK usage demonstration script
├── knowledge/                   # Search, store, and extraction components
│   ├── context.py               # Context linking & context scoping
│   ├── extraction.py            # Rule-based and LLM parser triggers
│   ├── relationships.py         # Relationship creation & graph queries
│   ├── retrieval.py             # Cosine distance retrieval wrappers
│   └── store.py                 # Knowledge storage controllers
├── memory/
│   └── working/                 # Redis working memory cache layers
├── sdk/
│   └── python/                  # MENO Python SDK source code
└── tests/                       # Unit and integration test suites
```

---

## Roadmap

- **Year 1**: Establish reliable local-first extraction pipelines, single-tenant FastAPI backends, and simple key-based auth.
- **Year 2**: Multi-tenant database partitioning, enhanced model contexts (MCP servers), and visual graph explorers.
- **Year 3**: Advanced vector re-ranking models and LLM agentic memory loopback.
- **Year 4**: Autonomous memory cleaning, auto-supersedes updates, and conflict resolution algorithms.
- **Year 5**: Complete organizational intelligence ledger with cross-tenant context routing.

For the full roadmap and architecture constraints, view the [ARCHITECTURE.md](file:///c:/Users/aakash09/Desktop/meno/ARCHITECTURE.md).

---

## Contributing

We love pull requests! Please read our [CONTRIBUTING.md](file:///c:/Users/aakash09/Desktop/meno/CONTRIBUTING.md) to learn about our developer setup, coding standards (like mandatory file headers and enum usages), and PR checklist.

---

## License

This project is licensed under the MIT License — see the LICENSE file for details.

<!-- MULTI_TOOL_CONTINUITY_SECTION_INSERTED_BY_PROMPT_12 -->
