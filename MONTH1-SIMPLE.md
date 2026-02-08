# Month 1 — What Did We Actually Build?

## The App In One Sentence

A backend API that lets you manage job candidates, job postings, and resumes — including uploading resume files and automatically reading the text out of them.

There's no frontend yet. You interact with it through a web page at `localhost:8000/docs` that lets you click buttons and fill in forms to test everything.

---

## Think Of It Like A Restaurant

```
src/app/
├── api/          = The MENU         (what you can ask the app to do)
├── services/     = The KITCHEN      (where the work actually happens)
├── models/       = The RECIPE BOOK  (what data looks like in the database)
├── schemas/      = The ORDER FORMS  (what info you need to send)
├── storage/      = The FRIDGE       (where uploaded files are kept)
├── core/         = The BACK OFFICE  (settings, database connection, errors)
└── main.py       = The FRONT DOOR   (starts the whole thing)
```

When someone sends a request:
1. **API** receives it (the waiter takes the order)
2. **Schemas** validate it (is this order even possible?)
3. **Services** do the work (the kitchen cooks it)
4. **Models** talk to the database (save/load data)
5. **API** sends back the result (waiter brings the food)

---

## What You Can Do With It

### Candidates (people applying for jobs)
- **Create** one — give it a name and email
- **List** all of them — with pages (not everything at once)
- **Filter** by status — show me only "new" or "interviewing" ones
- **Update** one — change their name, status, whatever
- **Delete** one — also deletes their resumes

### Jobs (open positions)
- Same thing — create, list, filter, update, delete
- Can filter by active/inactive

### Resumes (uploaded files)
- **Upload** a PDF, Word, or text file for a candidate
- The app **reads the text out of it automatically**
- You can **download** the original file
- You can **see just the text** it extracted
- You can tell it to **re-read** the file if extraction failed

---

## The Database

Three tables, super simple:

| Table | What it stores |
|-------|---------------|
| **candidates** | Name, email, phone, status (new/screening/interview/offer/hired/rejected) |
| **jobs** | Title, department, description, requirements, location, full-time/part-time/etc |
| **resumes** | Which candidate owns it, the file info, and the text pulled out of it |

Delete a candidate = their resumes get deleted too. Makes sense.

---

## The Tests

72 tests. They all pass. Three levels:

| Level | What | Count |
|-------|------|-------|
| **Unit** | Tests tiny pieces in isolation. No database needed. | 27 |
| **Integration** | Tests real API calls with a real database. | 41 |
| **Smoke** | Tests full workflows end-to-end (create person, upload resume, check text came out). | 4 |

---

## Decisions Made & Why

| Decision | Why |
|----------|-----|
| **`uv` for packages** | Way faster than pip. Same job. |
| **`hatchling` for building** | We tried another one first, it broke. This one worked. |
| **Code lives in `src/app/`** | Prevents weird Python import bugs. Standard practice. |
| **`create_app()` factory** | Instead of one global app, we make fresh ones. Makes testing easy. |
| **Everything is async** | Server can handle many requests at once instead of waiting one-by-one. |
| **Services don't save to DB** | They do the work, the API layer saves. If something crashes, nothing half-saves. |
| **File storage is swappable** | Files go to hard drive now. Later we can swap to cloud storage without changing anything else. |
| **No auth yet** | We skipped login/passwords to focus on getting the foundation right first. Coming in Month 2. |

---

## How To Run It

**Start the database:**
```bash
docker compose up -d db
```

**Create the tables (only first time):**
```bash
set PYTHONPATH=src && .venv/Scripts/alembic upgrade head
```

**Start the server:**
```bash
.venv/Scripts/uvicorn "app.main:create_app" --factory --reload --app-dir src
```
Go to **http://localhost:8000/docs** and play around.

**Run tests:**
```bash
.venv/Scripts/pytest tests/ -v
```

---

## What Each Package Does

| Package | In plain english |
|---------|-----------------|
| **fastapi** | The web framework. Receives requests, sends responses. |
| **uvicorn** | The server. Runs FastAPI. |
| **sqlalchemy** | Talks to the database using Python instead of writing raw SQL. |
| **asyncpg** | The cable that connects Python to PostgreSQL. |
| **alembic** | Version control for your database. When you add a column, it handles it. |
| **pydantic** | Checks incoming data. "You said email but this isn't an email." |
| **pdfplumber** | Reads text out of PDF files. |
| **python-docx** | Reads text out of Word documents. |
| **ruff** | Spell-checker for code. Catches style issues and bugs. |
| **mypy** | Type-checker. "You said this is a string but it's actually a number." |
| **pytest** | Runs the tests. |
| **httpx** | Fake browser for tests. Pretends to be a user calling the API. |

---

## What's Coming Next (Month 2)

| Feature | What it means |
|---------|--------------|
| **Claude API** | Instead of just reading raw text from resumes, Claude will *understand* them — pull out skills, experience, education as structured data. |
| **ChromaDB** | A special database that understands *meaning*. Lets you search "find me someone who knows backend development" even if their resume says "Python and SQL experience." |
| **Matching** | "This candidate is 87% match for this job." Based on meaning, not keyword matching. |
| **Auth** | Login system. Right now anyone can use the API. |

---

## Git Commits

```
3d0fc0e  Fixed testing setup (async event loop issues)
7b01e0a  Built everything
```

That's it. Two commits. The whole foundation.
