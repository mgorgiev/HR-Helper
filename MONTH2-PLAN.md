# Month 2 Plan — Intelligence Layer

## Goal

Make the app smart. Right now it just stores candidates, jobs, and raw resume text. After Month 2, it will:

1. **Parse resumes** — Gemini reads a resume and extracts structured data (skills, experience, education)
2. **Embed everything** — Turn resumes and jobs into vectors (numbers that represent meaning)
3. **Match candidates to jobs** — "This person is a 87% match" based on semantic similarity
4. **Answer questions** — "Which candidates have Python experience and worked at startups?" (RAG)

---

## Tech Stack Additions

| What | Tool | Why |
|------|------|-----|
| LLM | **Gemini 2.0 Flash** | Free tier (15 RPM), great at structured extraction, cheap at scale |
| Embeddings | **Gemini text-embedding-004** | Same vendor, one API key, solid quality |
| Vector DB | **ChromaDB** | Already in docker-compose (commented out), lightweight, works with any embeddings |
| SDK | **google-genai** | Official Google AI Python SDK |

---

## Week-by-Week Breakdown

### Week 1 — Gemini Integration + Resume Parsing

**What we're building:** A service that sends resume text to Gemini and gets back structured JSON.

**New files:**
- `src/app/core/llm.py` — Gemini client setup (API key from settings, model config)
- `src/app/services/resume_parser.py` — Send extracted text to Gemini, get structured data back
- `src/app/schemas/parsed_resume.py` — Pydantic models for parsed resume data

**New database fields (migration):**
```
resumes table:
  + parsed_data      JSONB    (structured extraction result)
  + parsed_at        TIMESTAMP
  + parsing_status   VARCHAR  (pending/completed/failed)
  + parsing_error    TEXT
```

**The flow:**
1. Resume is uploaded (already works from Month 1)
2. Text is extracted (already works)
3. **NEW:** Extracted text is sent to Gemini with a prompt like:

```
Parse this resume and return JSON with:
- full_name
- email, phone
- summary (1-2 sentences)
- skills (list)
- experience (list of {company, title, start_date, end_date, description})
- education (list of {institution, degree, field, year})
```

4. Gemini returns structured JSON
5. We validate it with Pydantic and save to `parsed_data`

**New endpoints:**
- `POST /api/v1/resumes/{id}/parse` — Trigger Gemini parsing
- `GET /api/v1/resumes/{id}/parsed` — Get parsed structured data

**Tests:**
- Unit: Mock Gemini responses, test parsing logic, test schema validation
- Integration: Test parse endpoint with real (or mocked) Gemini calls
- Test error handling (what if Gemini returns garbage?)

---

### Week 2 — ChromaDB + Embeddings

**What we're building:** Store vector embeddings of resumes and jobs so we can search by meaning.

**New files:**
- `src/app/core/embeddings.py` — Gemini embedding client
- `src/app/services/embedding_service.py` — Generate and store embeddings
- `src/app/storage/vector_store.py` — ChromaDB wrapper (abstract interface like FileStorage)

**Docker update:**
- Uncomment ChromaDB in `docker-compose.yml`
- ChromaDB runs on port 8001

**The flow:**
1. When a resume is parsed, we take the parsed text/skills/experience
2. Send it to Gemini's embedding model → get back a vector (list of numbers)
3. Store that vector in ChromaDB with the resume ID as metadata
4. Same thing for job descriptions when a job is created/updated

**What gets embedded:**
- **Resumes:** Combine skills + experience + summary into one chunk of text, embed that
- **Jobs:** Combine title + description + requirements, embed that

**New endpoints:**
- `POST /api/v1/resumes/{id}/embed` — Generate and store embedding for a resume
- `POST /api/v1/jobs/{id}/embed` — Generate and store embedding for a job

**Tests:**
- Unit: Mock embedding responses, test vector store interface
- Integration: Test ChromaDB storage and retrieval
- Test that embeddings are created on resume parse / job create

---

### Week 3 — Semantic Matching

**What we're building:** Given a job, find the best matching candidates (and vice versa).

**New files:**
- `src/app/services/matching_service.py` — Query ChromaDB for similar vectors, calculate scores
- `src/app/schemas/match.py` — Match result schemas (candidate, score, reasoning)

**The flow:**
1. HR person asks "who matches this job?"
2. We take the job's embedding from ChromaDB
3. ChromaDB finds the N most similar resume embeddings
4. We return the candidates ranked by similarity score
5. **Optional (RAG):** Send top matches + job description to Gemini and ask "explain why each candidate matches"

**New endpoints:**
- `GET /api/v1/jobs/{id}/matches` — Get ranked candidates for a job
  - Query params: `limit` (how many), `min_score` (threshold)
  - Returns: list of `{candidate, score, reasoning}`
- `GET /api/v1/candidates/{id}/matches` — Get matching jobs for a candidate
  - Same idea, reversed

**Tests:**
- Unit: Test scoring logic, test result ranking
- Integration: End-to-end match flow (create job, create candidate with resume, parse, embed, match)
- Smoke: Full workflow — upload resume → parse → embed → create job → embed → match → verify results

---

### Week 4 — Polish, Auto-Pipeline, Error Handling

**What we're building:** Wire everything together so it's automatic, not manual trigger after manual trigger.

**The auto-pipeline:**
When a resume is uploaded:
1. Extract text (already automatic from Month 1)
2. **Auto-parse** with Gemini (new)
3. **Auto-embed** (new)
4. Ready for matching immediately

When a job is created/updated:
1. **Auto-embed** the job description
2. Ready for matching immediately

**New files:**
- `src/app/services/pipeline.py` — Orchestrates the full flow
- Update existing upload/job endpoints to trigger pipeline

**Other work:**
- Retry logic for Gemini API failures (rate limits, timeouts)
- Background task processing (don't make the user wait for Gemini)
- Proper error handling for all AI operations
- Cost tracking (log token usage)
- Update CI pipeline for new dependencies
- Update README and docs

**Configuration additions (.env):**
```
GOOGLE_AI_API_KEY=your-key-here
CHROMADB_HOST=localhost
CHROMADB_PORT=8001
GEMINI_MODEL=gemini-2.0-flash
GEMINI_EMBEDDING_MODEL=text-embedding-004
```

---

## New Dependencies

```toml
[project]
dependencies = [
    # ... existing ...
    "google-genai>=1.0.0",        # Gemini SDK
    "chromadb>=0.5.0",            # Vector database client
]
```

---

## Database Migration

One new migration adding fields to the `resumes` table:

```sql
ALTER TABLE resumes ADD COLUMN parsed_data JSONB;
ALTER TABLE resumes ADD COLUMN parsed_at TIMESTAMP;
ALTER TABLE resumes ADD COLUMN parsing_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE resumes ADD COLUMN parsing_error TEXT;
```

---

## New Test Count Estimate

| Tier | Month 1 | New in Month 2 | Total |
|------|---------|----------------|-------|
| Unit | 27 | ~20 | ~47 |
| Integration | 41 | ~25 | ~66 |
| Smoke | 4 | ~4 | ~8 |
| **Total** | **72** | **~49** | **~121** |

---

## What's NOT in Month 2

- **Auth** — Moved to Month 3. Intelligence layer is more important right now.
- **Frontend** — Still API-only. Swagger UI for testing.
- **LangGraph workflows** — Month 4+. We'll add multi-step agent workflows later.
- **Batch processing** — Month 3. Process 100 resumes at once.

---

## Cost Estimate

With Gemini's free tier (15 requests/minute):

| Operation | Gemini Model | Free? |
|-----------|-------------|-------|
| Parse 1 resume | 2.0 Flash | Yes (within free tier) |
| Embed 1 resume | text-embedding-004 | Yes (within free tier) |
| Match query | ChromaDB (local) | Yes (no API call) |
| RAG answer | 2.0 Flash | Yes (within free tier) |

For development and testing: **$0.**
At scale (beyond free tier): ~$0.01-0.03 per resume processed.
