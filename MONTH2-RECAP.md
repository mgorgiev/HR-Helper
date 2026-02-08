# Month 2 Recap — Intelligence Layer

> **TL;DR:** We added the AI brain — Gemini 2.0 Flash parses resumes into structured data, embeddings go into ChromaDB for semantic search, and a matching engine ranks candidates against jobs with human-readable explanations. Upload a resume → it auto-extracts, parses, and embeds. Query a job → get ranked candidates with "why they match" explanations from Gemini.

---

## What Got Built

### 6 New API Endpoints

| Method | Endpoint | What it does |
|--------|----------|-------------|
| `POST` | `/resumes/{id}/parse` | Send extracted text to Gemini → get structured JSON (name, skills, experience, education) |
| `GET` | `/resumes/{id}/parsed` | Retrieve the parsed structured data |
| `POST` | `/resumes/{id}/embed` | Generate embedding vector and store in ChromaDB |
| `POST` | `/jobs/{id}/embed` | Generate embedding vector for a job |
| `GET` | `/matching/jobs/{id}/candidates` | Rank all candidates for a job — returns scores + Gemini explanations |
| `GET` | `/matching/candidates/{id}/jobs` | Rank all jobs for a candidate — same format |

### The AI Pipeline (auto on upload)

When you upload a resume, a background pipeline kicks off automatically:

```
Upload → Extract Text → Parse with Gemini → Embed → Store in ChromaDB
         (pdfplumber)    (structured JSON)    (vector)   (semantic search)
```

The upload returns immediately (201) — the AI pipeline runs in the background via FastAPI `BackgroundTasks`. You can check status by polling `GET /resumes/{id}` and watching `parsing_status` go from `"pending"` → `"completed"`.

Jobs also auto-embed on create and re-embed when title/description/requirements change.

### Resume Parsing (Gemini 2.0 Flash)

Gemini receives the raw extracted text and returns structured JSON:

```json
{
  "full_name": "Borche Chestojnov",
  "email": "borcecestojnov75@gmail.com",
  "phone": "077880167",
  "summary": "Data Entry professional with 3 years of experience...",
  "skills": ["Microsoft Excel", "Database Entry & Management", "Google Sheets", ...],
  "experience": [
    {
      "company": "Juridika Skopje",
      "title": "Data Entry Clerk",
      "start_date": "11/2023",
      "end_date": "11/2025",
      "description": "Performed accurate and timely data entry..."
    }
  ],
  "education": [...],
  "languages": ["Macedonian", "English"],
  "certifications": []
}
```

This uses Gemini's `response_schema` feature — we pass our Pydantic model as the schema and get guaranteed structured output (no regex parsing, no prompt hacks).

### Embeddings & Vector Store (ChromaDB)

Every parsed resume and job gets converted to a 768-dimensional embedding vector using `gemini-embedding-001`. These vectors are stored in ChromaDB with cosine similarity search.

- **Resumes** get embedded from a composite of: summary + skills + experience + education
- **Jobs** get embedded from: title + description + requirements
- Task types: `RETRIEVAL_DOCUMENT` for storage, `RETRIEVAL_QUERY` for search queries

### Semantic Matching

The matching engine:
1. Takes a job (or candidate) and generates a query embedding
2. Searches ChromaDB for the nearest resume (or job) vectors
3. Converts cosine distance to a 0-1 similarity score
4. Sends the top matches to Gemini for human-readable explanations
5. Returns ranked results with scores + explanations

**Real test results from live testing:**

| Job | Candidate | Score | Gemini's Explanation |
|-----|-----------|-------|---------------------|
| Data Entry Specialist | Borche (Data Entry) | **0.8783** | "strong match due to extensive experience in data entry, proficiency in Excel..." |
| House Cleaner | Borche (Data Entry) | **0.8039** | "poor match, lacks any mention of cleaning or cooking skills..." |

The system correctly distinguishes between relevant and irrelevant matches.

### Database Changes

Added 4 new columns to the `resumes` table:

| Column | Type | What it stores |
|--------|------|---------------|
| `parsed_data` | JSONB | Structured resume data from Gemini |
| `parsing_status` | String(20) | `pending` / `completed` / `failed` (indexed) |
| `parsing_error` | Text | Error message if parsing failed |
| `parsed_at` | DateTime (tz) | When parsing completed |

Alembic migration: `a1b2c3d4e5f6_add_resume_parsing_fields.py`

---

## Decisions That Were Made (and Why)

### LLM Provider: Google Gemini (not OpenAI/Claude)

- **Free tier** — good enough for development and small-scale use
- **Built-in embeddings** — one provider for both parsing and embeddings (simpler than mixing OpenAI embeddings + Claude parsing)
- **Structured output** — Gemini's `response_schema` accepts a Pydantic model directly, no prompt engineering needed for JSON format
- **SDK** — `google-genai` (official Google AI Python SDK), fully async via `client.aio.models`

### Embedding Model: `gemini-embedding-001`

Originally planned `text-embedding-004` but it wasn't available on the account. `gemini-embedding-001` works and produces 768-dimensional vectors. Can swap later without code changes (just update `.env`).

### ChromaDB (not Pinecone/Weaviate/pgvector)

- **Free and self-hosted** — runs as a simple Python process or Docker container
- **Easy to set up** — `chroma run --port 8001` and you're done
- **Good enough** — for our scale (hundreds to low thousands of candidates), ChromaDB is more than sufficient
- **Abstract interface** — `VectorStore` ABC means we can swap to Pinecone or pgvector later if needed

### Background Pipeline (not synchronous)

Upload returns 201 immediately. The AI pipeline (parse + embed) runs in FastAPI `BackgroundTasks`. This means:
- Users don't wait 5-10 seconds for Gemini to respond
- If the API is rate-limited, the error gets logged but doesn't break the upload
- Status can be checked by polling the resume endpoint

### Explanation Generation (always on)

Every match includes a Gemini-generated explanation. This is slightly slower (one extra API call per match query) but makes the results actually useful — recruiters can see *why* someone matches, not just a number.

### Settings: `extra="ignore"`

Added `extra="ignore"` to the pydantic-settings config so Docker env vars like `POSTGRES_USER`, `POSTGRES_PASSWORD` don't crash the app. These vars are needed by the PostgreSQL container but aren't in our Settings model.

---

## New Files Created (12)

```
src/app/
├── core/
│   └── llm.py                    # Gemini client factory
├── schemas/
│   ├── parsed_resume.py          # ParsedResumeData, WorkExperience, Education
│   └── match.py                  # CandidateMatch, JobMatch, MatchResults
├── services/
│   ├── resume_parser.py          # Gemini structured parsing
│   ├── embedding_service.py      # Embedding generation
│   ├── matching_service.py       # Semantic matching + explanations
│   └── pipeline.py               # Auto-pipeline (parse → embed)
├── storage/
│   ├── vector_store.py           # Abstract VectorStore ABC
│   └── chroma.py                 # ChromaDB implementation
└── api/v1/
    └── matching.py               # Matching endpoints

tests/
├── mocks/
│   └── mock_vector_store.py      # InMemoryVectorStore for tests
├── unit/
│   ├── test_parsed_resume_schema.py
│   ├── test_match_schemas.py
│   ├── test_resume_parser.py
│   ├── test_embedding_service.py
│   ├── test_vector_store.py
│   └── test_matching_service.py
├── integration/
│   ├── test_resume_parsing_api.py
│   ├── test_embedding_api.py
│   └── test_matching_api.py
└── smoke/
    └── test_ai_workflows.py

alembic/versions/
└── a1b2c3d4e5f6_add_resume_parsing_fields.py
```

### Modified Files (12)

- `pyproject.toml` — Added `google-genai`, `chromadb` dependencies
- `src/app/core/config.py` — Gemini + ChromaDB settings, `extra="ignore"`
- `src/app/core/exceptions.py` — `AIServiceError` (502), `PreconditionError` (422)
- `src/app/api/deps.py` — `get_llm_client()`, `get_vector_store()` dependencies
- `src/app/api/v1/router.py` — Added matching router
- `src/app/api/v1/resumes.py` — Parse/embed endpoints + background pipeline on upload
- `src/app/api/v1/jobs.py` — Embed endpoint + auto-embed on create/update + vector cleanup on delete
- `src/app/models/resume.py` — JSONB `parsed_data`, `parsing_status`, `parsing_error`, `parsed_at`
- `src/app/schemas/resume.py` — `ParsingStatus` enum, `ResumeParsedResponse`
- `src/app/services/resume_service.py` — `update_parsing()` function
- `docker-compose.yml` — ChromaDB service container
- `.env.example` — Gemini + ChromaDB env vars

---

## Testing

### Test Counts

| Tier | Month 1 | Month 2 Added | Total |
|------|---------|---------------|-------|
| **Unit** | 27 | 39 | **66** |
| **Integration** | 21 | 15 | **36** |
| **Smoke** | 4 | 2 | **6** |
| **Total** | 52 | 56 | **108** |

### What the New Tests Cover

**Unit tests (39 new):**
- Parsed resume schema validation (full, minimal, defaults, missing required fields)
- Match schema validation (CandidateMatch, JobMatch, MatchResults)
- Resume parser with mocked Gemini (structured output, empty response, minimal response)
- Embedding service (generate, build resume text, embed resume, embed job, None fields)
- InMemoryVectorStore (upsert, get, delete, search ordering, n_results, empty collection, overwrite)
- Distance-to-score conversion (identical, opposite, mid, clamped)

**Integration tests (15 new):**
- Parse resume API (200, 404, get parsed data, pending before parse)
- Embed resume API (200, 422 without parsed data, 404)
- Embed job API (200, 404)
- Matching API (candidates for job, empty results, limit param, 404, jobs for candidate)

**Smoke tests (2 new):**
- Full resume intelligence pipeline: upload → extract → parse → embed → verify
- Full matching workflow: candidate + resume + job → parse → embed → match both directions

### Mock Strategy

Tests don't hit real Gemini or ChromaDB:
- **`InMemoryVectorStore`** — Dict-based vector store with real cosine distance calculation
- **Mocked `genai.Client`** — `AsyncMock` that returns fake parse responses and embedding vectors
- **Dependency overrides** — `get_llm_client` and `get_vector_store` are overridden in the test client

---

## New Dependencies

| Package | What it does |
|---------|-------------|
| `google-genai` | Official Google AI SDK (Gemini) |
| `chromadb` | Vector database for semantic search |

---

## How to Run the Full Stack Locally

### Terminal 1 — ChromaDB
```bash
.venv\Scripts\chroma.exe run --path ./chroma_data --port 8001
```

### Terminal 2 — Server
```bash
.venv\Scripts\alembic.exe upgrade head
.venv\Scripts\uvicorn.exe "app.main:create_app" --factory --reload --app-dir src
```

### Quick Pipeline Test
1. `POST /candidates` → create candidate
2. `POST /candidates/{id}/resumes` → upload PDF (auto-triggers parse + embed)
3. Wait 5s, then `GET /resumes/{id}` → check `parsing_status` = `"completed"`
4. `POST /jobs` → create job (auto-embeds)
5. `GET /matching/jobs/{id}/candidates` → see ranked results with explanations

---

## Git History

```
e03d337 Month 2 Intelligence Layer: Gemini AI parsing, ChromaDB embeddings, semantic matching
0a827ce Fix test infrastructure: session-scoped event loop and transactional isolation
7b01e0a Month 1 Foundation: FastAPI scaffold with CRUD, file upload, and text extraction
```

---

## What's Next (Month 3)

- **Auth** — JWT + OAuth2 (token-based access control)
- **LangGraph agent workflows** — multi-step AI reasoning (e.g. "find me a senior Python dev who speaks Serbian")
- **Advanced search/filtering** — combine semantic search with traditional filters (status, location, employment type)
