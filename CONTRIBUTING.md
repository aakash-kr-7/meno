<!--
(a) What this file is: MENO Developer Contribution Guidelines (CONTRIBUTING.md).
(b) What it does: Specifies requirements for setup, coding standards, types, and the pull request process.
(c) How it fits into the MENO system: Main entrypoint for contributors to ensure quality and compatibility.
-->

# Contributing to MENO

First off, thank you for contributing to MENO! These guidelines ensure that your contributions are high-quality, secure, and compatible with our multi-tiered memory architecture.

---

## 1. Local Developer Setup

To set up a local development environment, follow these steps:

### Prerequisites
* **Python 3.12+**
* **Docker & Docker Desktop** (running and configured)
* **Git**

### Installation Steps

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/aakash-kr-7/meno.git
   cd meno
   ```

2. **Set Up the Virtual Environment**:
   Create and activate a virtual environment, then install both the core library and client SDK packages in editable mode:
   ```bash
   # Create environment
   python -m venv venv

   # Activate environment
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On Windows (cmd):
   .\venv\Scripts\activate.bat

   # Install dependencies
   pip install --upgrade pip
   pip install -e .
   pip install -e sdk/python
   ```

3. **Configure Environment Variables**:
   Initialize your `.env` configuration:
   ```bash
   cp .env.example .env
   ```
   *Note: In development, `LLM_EXTRACTION_ENABLED=false` is default. The system runs entirely offline using local regex and keyword parsing rules.*

4. **Spin Up Infrastructure Tiers**:
   Launch the Redis and PostgreSQL (with pgvector) backend services:
   ```bash
   docker compose up --build -d
   ```

5. **Verify the Health Check**:
   Wait for services to start and execute a curl request:
   ```bash
   curl http://localhost:8000/health
   ```
   You should receive a `200 OK` status outlining active database and Redis engines.

---

## 2. Core Coding Standards

To maintain standard formatting and reliability, every contributor must follow these three architectural constraints:

### 2.1. File Header Comments
Every new or modified file must start with a three-part structural header comment explaining:
- **(a) What the file is**
- **(b) What it does**
- **(c) How it fits into the MENO system**

**Example for Python Files (`.py`)**:
```python
"""
(a) What this file is: [Description of module]
(b) What it does: [Specify functionalities]
(c) How it fits into the MENO system: [Connection to core database/mcp layers]
"""
```

**Example for Markdown & Configurations (`.md`, `.yml`)**:
```markdown
<!--
(a) What this file is: [Description]
(b) What it does: [Functionality]
(c) How it fits into the MENO system: [Role]
-->
```

### 2.2. No Raw SQL Queries
All database interactions must be structured via SQLAlchemy ORM models.
- **ORM Models**: Defined in `db/models/`.
- **Database Access Logic**: Encapsulated in the `knowledge/` write/read path scripts (`store.py`, `retrieval.py`, `relationships.py`, `context.py`).
- **Migrations**: Any database column alterations must include an Alembic migration revision. Always ensure the migrations in `db/migrations/versions/` match model upgrades:
  ```bash
  alembic revision --autogenerate -m "describe_changes"
  ```

### 2.3. Type Enum Verification
Never use raw string literals where standard type mappings are available. Import and leverage:
- **Core Library**: `core/types.py` (`KnowledgeType`, `RelationshipType`, `ContextType`).
- **SDK**: `meno/types.py` (matching enum interfaces).

### 2.4. Ban on Placeholders
We do not accept contributions containing `TODO` notes, missing function bodies, or empty mocks. All code submitted must be robust, complete, and fully validated.

---

## 3. Testing Framework

MENO runs integration tests utilizing `pytest`. Tests cover Redis working caches, vector similarities, DB models, and MCP tools configurations.

### Running Tests
Ensure your local Docker services are running, then run the test suites:
```bash
pytest tests/ -v
```

Before committing code, verify all tests pass:
```
tests/test_auth.py::test_auth_success PASSED
tests/test_knowledge.py::test_store_and_retrieve PASSED
tests/test_mcp.py::test_mcp_server_tools PASSED
...
```

---

## 4. Pull Request Checklist

Before submitting a pull request, ensure you have ticked all items on this checklist:

- [ ] Every new or modified file contains a three-part header comment block.
- [ ] No raw SQL is used; all reads and writes go through SQLAlchemy models and repositories.
- [ ] Standard enums (`KnowledgeType`, `RelationshipType`) are used instead of raw strings.
- [ ] The database schemas match your Alembic migrations (`db/migrations/versions/`).
- [ ] Code formatting has been run using standard tools (`black`, `isort`, `autoflake`).
- [ ] Running `pytest tests/ -v` completes with zero failures.
- [ ] Git hook validation is verified (run `meno hooks install` locally and execute a test commit).
- [ ] No credential files (`.env`, database backups) are tracked by Git.
