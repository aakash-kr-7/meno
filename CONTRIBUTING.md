<!--
(a) What this file is: MENO Developer Contribution Guidelines (CONTRIBUTING.md).
(b) What it does: Specifies requirements for setup, coding standards, types, and the pull request process.
(c) How it fits into the MENO system: Main entrypoint for contributors to ensure quality and compatibility.
-->

# Contributing to MENO

First off, thank you for contributing to MENO! These guidelines help ensure that your contributions are high-quality, secure, and maintainable.

---

## Developer Setup

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- Git

### Initial Setup Steps
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/aakash-kr-7/meno.git
   cd meno
   ```

2. **Set Up the Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install -e .           # Install package in editable mode
   pip install -e sdk/python  # Install python SDK in editable mode
   ```

3. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and fill in any required variables. Note that by default `LLM_EXTRACTION_ENABLED` is `false`, running MENO entirely locally with zero API keys required.

4. **Spin Up Infrastructure**:
   ```bash
   docker compose up --build -d
   ```
   This starts the PostgreSQL (with pgvector) database and the Redis cache server.

5. **Verify the Installation**:
   Open a browser or run a GET request to `http://localhost:8000/health`. You should receive a `200 OK` response with a JSON payload outlining the active backend tiers.

---

## Coding Standards

### 1. Mandatory File Headers
Every new or modified file must include a structured header comment explaining what the file is, what it does, and how it fits into the MENO architecture.
- **Python Files (`.py`)**: Use docstrings at the top of the file:
  ```python
  """
  (a) What this file is: [Description]
  (b) What it does: [Functionality]
  (c) How it fits into the MENO system: [Role in Architecture]
  """
  ```
- **Markdown / Config Files (`.md`, `.yml`)**: Use HTML comments or file comments:
  ```markdown
  <!--
  (a) What this file is: [Description]
  (b) What it does: [Functionality]
  (c) How it fits into the MENO system: [Role in Architecture]
  -->
  ```

### 2. Type Enums
Avoid raw string literals for knowledge types, relationships, and context scopes. Always import and use the standard enums:
- Backend types: Import from `core/types.py` (`KnowledgeType`, `RelationshipType`, `ContextType`).
- Python SDK types: Import from `meno/types.py` (`KnowledgeType`, `RelationshipType`, `ContextType`).

### 3. No Placeholders
Never submit code containing `TODO` placeholders or empty mock features that are not fully operational. All code contributed must be fully runnable and validated.

---

## Pull Request Checklist

Before submitting a pull request, please verify that your changes satisfy the following criteria:

- [ ] All new files contain a proper header comment block.
- [ ] No raw strings are used where standard enums (e.g. `KnowledgeType` or `RelationshipType`) are available.
- [ ] Code has been formatted using standard formatters (like black / autoflake / isort).
- [ ] Local server passes `/health` diagnostics.
- [ ] All automated tests run and pass successfully:
  ```bash
  pytest tests/ -v
  ```
- [ ] No secrets or `.env` files are tracked by Git (check `.gitignore`).
- [ ] The change is accompanied by tests or an interactive demo.
