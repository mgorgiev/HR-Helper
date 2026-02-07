# HR Recruitment Assistant

AI-powered resume screening and candidate matching system built with FastAPI, PostgreSQL, and Claude API.

## Stack

- **API:** FastAPI + Uvicorn
- **Database:** PostgreSQL + SQLAlchemy (async) + Alembic
- **File Processing:** pdfplumber, python-docx
- **Package Manager:** uv
- **Containerization:** Docker + Docker Compose

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker & Docker Compose (for PostgreSQL)

## Quick Start

### With Docker (recommended)

```bash
# Start PostgreSQL + app
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

# Start PostgreSQL (via Docker)
docker compose up db -d

# Run migrations
uv run alembic upgrade head

# Start dev server
uv run uvicorn app.main:create_app --factory --reload
```

## API Endpoints

All endpoints are under `/api/v1`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (DB connectivity) |
| GET | `/status` | Liveness probe |
| POST | `/candidates` | Create candidate |
| GET | `/candidates` | List candidates (paginated) |
| GET | `/candidates/{id}` | Get candidate |
| PATCH | `/candidates/{id}` | Update candidate |
| DELETE | `/candidates/{id}` | Delete candidate |
| POST | `/jobs` | Create job |
| GET | `/jobs` | List jobs (paginated) |
| GET | `/jobs/{id}` | Get job |
| PATCH | `/jobs/{id}` | Update job |
| DELETE | `/jobs/{id}` | Delete job |
| POST | `/candidates/{id}/resumes` | Upload resume (PDF/DOCX/TXT) |
| GET | `/candidates/{id}/resumes` | List candidate's resumes |
| GET | `/resumes/{id}` | Get resume metadata |
| GET | `/resumes/{id}/download` | Download original file |
| GET | `/resumes/{id}/text` | Get extracted text |
| POST | `/resumes/{id}/extract` | Re-run text extraction |
| DELETE | `/resumes/{id}` | Delete resume |

## Running Tests

```bash
# All tests
uv run pytest tests/ -v

# By tier
uv run pytest tests/unit/ -v           # No DB required
uv run pytest tests/integration/ -v     # Requires PostgreSQL
uv run pytest tests/smoke/ -v           # End-to-end workflows

# With coverage
uv run pytest tests/ -v --cov=src/app --cov-report=term-missing
```

## Project Structure

```
src/app/
├── main.py              # App factory
├── core/                # Config, database, exceptions
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic request/response models
├── api/v1/              # FastAPI routers
├── services/            # Business logic layer
└── storage/             # File storage abstraction
```

## Environment Variables

See [.env.example](.env.example) for all configurable values.
