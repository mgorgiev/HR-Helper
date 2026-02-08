# Month 1 Recap — HR Recruitment Assistant

> **TL;DR:** We built the entire foundation layer — a FastAPI backend with PostgreSQL, full CRUD for candidates/jobs/resumes, file upload with automatic text extraction (PDF, DOCX, TXT), Docker setup, CI pipeline, and 72 passing tests across 3 tiers.

---

## What Got Built

### The API (16 endpoints)

Everything lives under `/api/v1`. Hit `http://localhost:8000/docs` for the interactive Swagger UI.

| Method | Endpoint | What it does |
|--------|----------|-------------|
| `GET` | `/status` | Liveness check — always returns `{status: "ok"}` |
| `GET` | `/health` | Checks DB connectivity |
| `POST` | `/candidates` | Create a candidate |
| `GET` | `/candidates` | List candidates (paginated, filterable by status) |
| `GET` | `/candidates/{id}` | Get one candidate |
| `PATCH` | `/candidates/{id}` | Update candidate fields |
| `DELETE` | `/candidates/{id}` | Delete candidate + all their resumes |
| `POST` | `/jobs` | Create a job posting |
| `GET` | `/jobs` | List jobs (paginated, filterable by active/inactive) |
| `GET` | `/jobs/{id}` | Get one job |
| `PATCH` | `/jobs/{id}` | Update job fields |
| `DELETE` | `/jobs/{id}` | Delete job |
| `POST` | `/candidates/{id}/resumes` | Upload a resume file (auto-extracts text) |
| `GET` | `/candidates/{id}/resumes` | List resumes for a candidate |
| `GET` | `/resumes/{id}` | Get resume details |
| `GET` | `/resumes/{id}/download` | Download the actual file |
| `GET` | `/resumes/{id}/text` | Get just the extracted text |
| `POST` | `/resumes/{id}/extract` | Re-run text extraction |
| `DELETE` | `/resumes/{id}` | Delete resume + stored file |

### The Database (3 tables)

All IDs are UUIDs. All tables have `created_at` and `updated_at` timestamps.

**candidates**
- `first_name`, `last_name`, `email` (unique), `phone`, `status`, `notes`
- Status options: `new` → `screening` → `interview` → `offer` → `hired` / `rejected`

**jobs**
- `title`, `department`, `description`, `requirements`, `location`, `employment_type`, `is_active`
- Employment types: `full_time`, `part_time`, `contract`, `internship`

**resumes**
- Linked to a candidate (cascade delete — delete candidate, resumes go too)
- Stores: `original_filename`, `stored_filename`, `file_path`, `content_type`, `file_size_bytes`
- Text extraction fields: `extracted_text`, `extraction_status` (pending/completed/failed), `extraction_error`

### File Upload & Text Extraction

When you upload a resume:
1. File gets validated (must be `.pdf`, `.docx`, or `.txt`, max 10MB)
2. Stored on disk via a storage abstraction (local now, easy to swap to S3 later)
3. Text gets extracted automatically in the background:
   - **PDF** → `pdfplumber` (reads each page, joins text)
   - **DOCX** → `python-docx` (reads each paragraph)
   - **TXT** → plain file read (tries UTF-8, falls back to Latin-1)
4. Extraction result saved to the database

### Testing (72 tests, 3 tiers)

| Tier | Count | What it covers | Needs DB? |
|------|-------|---------------|-----------|
| **Unit** | 27 | Config, schemas, storage interface, text extraction | No |
| **Integration** | 41 | API endpoints, service layer, DB operations | Yes |
| **Smoke** | 4 | Full workflows (create candidate → upload resume → verify extraction) | Yes |

### Docker & CI

- **docker-compose.yml** — PostgreSQL 17 + the FastAPI app, ready to `docker compose up`
- **Dockerfile** — Production image based on Python 3.13-slim
- **GitHub Actions CI** — Lint (ruff + mypy) → Test (against real PostgreSQL) → Coverage

---

## Decisions That Were Made (and Why)

### Package Manager: `uv` (not pip/poetry)

Fast, modern, handles lockfiles. Installed via pip because it wasn't on PATH natively, so we invoke it as `python -m uv` when needed. The `.venv` was created by uv.

### Build Backend: `hatchling` (not uv_build)

We tried `uv_build` first — it couldn't find the `src/app` package and wanted `src/hr_helper/` instead. Switched to `hatchling` with an explicit package config:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/app"]
```

### Package Layout: `src/app/`

The code lives in `src/app/` (not at the root). This is a standard "src layout" that keeps the package isolated from project root files. When running tools, we pass `--app-dir src` or set `PYTHONPATH=src`.

### App Factory Pattern

Instead of a global `app = FastAPI()`, we use `create_app()` that returns a new FastAPI instance. This makes testing easier (each test can get a fresh app) and is the standard pattern for production apps. To run it:

```bash
uvicorn "app.main:create_app" --factory --reload --app-dir src
```

### Async Everything

- **SQLAlchemy 2.0** async mode with `asyncpg` driver
- **AsyncSession** for database operations
- File I/O wrapped in `asyncio.to_thread()` to avoid blocking the event loop
- All test fixtures are async with session-scoped event loops

### Services Don't Commit

The service layer uses `flush()` + `refresh()` instead of `commit()`. The commit happens in the `get_db()` dependency (auto-commits if no exception, rolls back otherwise). This means:
- Services are transaction-safe
- Multiple service calls can share one transaction
- Tests can easily roll back everything

### Storage Abstraction

File storage is behind an abstract base class (`FileStorage`). Right now it's `LocalFileStorage` (writes to disk). In Month 2+, we can swap in an S3 implementation without touching any API code.

### Ruff Config Exceptions

Two lint rules are intentionally ignored:
- **B008** — Ruff flags `Depends()` in function defaults as a mutable default. But that's exactly how FastAPI dependency injection works.
- **UP046** — Ruff wants us to use PEP 695 type params (`type X = ...`), but Pydantic doesn't support that syntax yet for Generics.

### Test Infrastructure

This was the trickiest part. Getting `pytest-asyncio` + `async SQLAlchemy` to play nice required:

1. **Session-scoped event loop** — All async fixtures share one event loop (otherwise the DB engine and test functions fight over different loops)
2. **Connection-bound sessions** — Each test gets a session bound to a connection with an open transaction. After the test, we roll back — so tests never pollute each other.
3. **`follow_redirects=True`** on the test HTTP client — FastAPI redirects `/candidates` to `/candidates/` (trailing slash). Without this, tests get 307 instead of the expected response.

Config in `pyproject.toml`:
```toml
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "session"
```

---

## Project Structure

```
HR-Helper/
├── src/app/                     # Main application
│   ├── main.py                  # App factory + lifespan
│   ├── api/
│   │   ├── deps.py              # Shared dependencies (DB, storage)
│   │   └── v1/
│   │       ├── router.py        # Aggregates all v1 routes
│   │       ├── health.py        # /health, /status
│   │       ├── candidates.py    # Candidate CRUD endpoints
│   │       ├── jobs.py          # Job CRUD endpoints
│   │       └── resumes.py       # Resume upload/download/extract
│   ├── core/
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── database.py          # Engine, session factory, get_db
│   │   └── exceptions.py        # NotFoundError, ConflictError, etc.
│   ├── models/
│   │   ├── base.py              # Base class + UUID/Timestamp mixins
│   │   ├── candidate.py         # Candidate ORM model
│   │   ├── job.py               # Job ORM model
│   │   └── resume.py            # Resume ORM model
│   ├── schemas/
│   │   ├── __init__.py          # PaginatedResponse[T]
│   │   ├── candidate.py         # CandidateCreate/Update/Read
│   │   ├── job.py               # JobCreate/Update/Read
│   │   ├── resume.py            # ResumeRead, ResumeTextResponse
│   │   └── health.py            # Health check response
│   ├── services/
│   │   ├── candidate_service.py # Candidate CRUD logic
│   │   ├── job_service.py       # Job CRUD logic
│   │   ├── resume_service.py    # Resume CRUD logic
│   │   └── text_extraction.py   # PDF/DOCX/TXT extractors
│   └── storage/
│       ├── base.py              # Abstract FileStorage interface
│       └── local.py             # Local filesystem implementation
├── tests/
│   ├── conftest.py              # Fixtures: engine, session, client
│   ├── unit/                    # 27 tests (no DB)
│   ├── integration/             # 41 tests (needs PostgreSQL)
│   └── smoke/                   # 4 end-to-end workflow tests
├── alembic/                     # Database migrations
│   ├── env.py
│   └── versions/
│       └── 679b598f8acb_initial_tables.py
├── sample_data/resumes/         # Test files (PDF, DOCX, TXT)
├── .github/workflows/ci.yml    # Lint → Test → Coverage
├── docker-compose.yml           # PostgreSQL + App
├── Dockerfile                   # Production image
├── pyproject.toml               # All config in one place
└── uv.lock                      # Locked dependencies
```

---

## How to Run Things

### Start the database
```bash
docker compose up -d db
```

### Run migrations (creates tables)
```bash
set PYTHONPATH=src && .venv/Scripts/alembic upgrade head
```

### Start the dev server
```bash
.venv/Scripts/uvicorn "app.main:create_app" --factory --reload --app-dir src
```
Then open: http://localhost:8000/docs

### Run all tests
```bash
.venv/Scripts/pytest tests/ -v
```

### Run only unit tests (no DB needed)
```bash
.venv/Scripts/pytest tests/unit/ -v
```

### Lint & format check
```bash
.venv/Scripts/ruff check src/ tests/
.venv/Scripts/ruff format --check src/ tests/
```

---

## Dependencies

| Package | What it does |
|---------|-------------|
| `fastapi` | Web framework |
| `uvicorn[standard]` | ASGI server |
| `sqlalchemy[asyncio]` | Async ORM |
| `asyncpg` | PostgreSQL driver |
| `alembic` | Database migrations |
| `pydantic` / `pydantic-settings` | Validation + config |
| `email-validator` | Email format checking |
| `python-multipart` | File upload support |
| `pdfplumber` | PDF text extraction |
| `python-docx` | DOCX text extraction |
| `python-dotenv` | .env file loading |
| `pytest` + `pytest-asyncio` | Test framework |
| `httpx` | Async HTTP client for tests |
| `ruff` | Linter + formatter |
| `mypy` | Type checker |

---

## What's Next (Month 2 — Intelligence Layer)

- **Claude API** integration for smart resume parsing (structured data extraction)
- **ChromaDB** for vector embeddings and semantic search
- **Semantic matching** — match candidates to jobs by meaning, not keywords
- **Auth** — JWT + OAuth2 (was skipped in Month 1 to focus on the foundation)

---

## Git History

```
3d0fc0e Fix test infrastructure: session-scoped event loop and transactional isolation
7b01e0a Month 1 Foundation: FastAPI scaffold with CRUD, file upload, and text extraction
```
