# HR Recruitment Assistant

AI-powered resume screening and candidate matching system built with FastAPI, PostgreSQL, Gemini AI, and ChromaDB.

## Stack

- **API:** FastAPI + Uvicorn
- **Database:** PostgreSQL + SQLAlchemy (async) + Alembic
- **AI:** Google Gemini 2.0 Flash (parsing + explanations) + text-embedding-004
- **Vector Store:** ChromaDB (semantic search)
- **File Processing:** pdfplumber, python-docx
- **Package Manager:** uv
- **Containerization:** Docker + Docker Compose

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker & Docker Compose (for PostgreSQL + ChromaDB)
- Google AI API key ([get one here](https://aistudio.google.com/))

## Quick Start

### With Docker (recommended)

```bash
# Copy and fill in your API key
cp .env.example .env
# Edit .env and set GOOGLE_AI_API_KEY=your-key

# Start PostgreSQL + ChromaDB + app
docker compose up --build -d

# Run migrations
docker compose exec app uv run alembic upgrade head

# API is available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Local Development

```bash
# Install dependencies
uv sync

# Start PostgreSQL + ChromaDB (via Docker)
docker compose up db chromadb -d

# Copy env and set your API key
cp .env.example .env

# Run migrations
uv run alembic upgrade head

# Start dev server
uv run uvicorn app.main:create_app --factory --reload --app-dir src
```

## API Endpoints

All endpoints are under `/api/v1`.

### Core CRUD

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (DB connectivity) |
| GET | `/status` | Liveness probe |
| POST | `/candidates` | Create candidate |
| GET | `/candidates` | List candidates (paginated) |
| GET | `/candidates/{id}` | Get candidate |
| PATCH | `/candidates/{id}` | Update candidate |
| DELETE | `/candidates/{id}` | Delete candidate |
| POST | `/jobs` | Create job (auto-embeds in background) |
| GET | `/jobs` | List jobs (paginated) |
| GET | `/jobs/{id}` | Get job |
| PATCH | `/jobs/{id}` | Update job (re-embeds if changed) |
| DELETE | `/jobs/{id}` | Delete job |

### Resume Management

| Method | Path | Description |
|--------|------|-------------|
| POST | `/candidates/{id}/resumes` | Upload resume (auto-pipeline: extract → parse → embed) |
| GET | `/candidates/{id}/resumes` | List candidate's resumes |
| GET | `/resumes/{id}` | Get resume metadata |
| GET | `/resumes/{id}/download` | Download original file |
| GET | `/resumes/{id}/text` | Get extracted text |
| POST | `/resumes/{id}/extract` | Re-run text extraction |
| POST | `/resumes/{id}/parse` | Trigger Gemini AI parsing |
| GET | `/resumes/{id}/parsed` | Get parsed structured data |
| POST | `/resumes/{id}/embed` | Generate and store embedding |
| DELETE | `/resumes/{id}` | Delete resume |

### AI Matching

| Method | Path | Description |
|--------|------|-------------|
| POST | `/jobs/{id}/embed` | Generate and store job embedding |
| GET | `/matching/jobs/{id}/candidates` | Ranked candidates for a job (with explanations) |
| GET | `/matching/candidates/{id}/jobs` | Matching jobs for a candidate (with explanations) |

## Running Tests

```bash
# All tests
uv run pytest tests/ -v

# By tier
uv run pytest tests/unit/ -v           # No DB required (66 tests)
uv run pytest tests/integration/ -v     # Requires PostgreSQL
uv run pytest tests/smoke/ -v           # End-to-end workflows

# With coverage
uv run pytest tests/ -v --cov=src/app --cov-report=term-missing
```

## Project Structure

```
src/app/
├── main.py              # App factory
├── core/                # Config, database, exceptions, LLM client
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic request/response models
├── api/v1/              # FastAPI routers
├── services/            # Business logic (parsing, embedding, matching, pipeline)
└── storage/             # File storage + vector store abstractions
```

## Environment Variables

See [.env.example](.env.example) for all configurable values.
