# Cocktail Database API (Phase 0)

Read-only FastAPI service for the existing `cocktail_database.db`.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Environment File

- Backend loads env values from `web/backend/.env` automatically at startup.
- Put your API keys in `web/backend/.env`, then restart backend.

## Endpoints

- `GET /health`
- `GET /meta/db-path`
- `GET /meta/counts`
- `GET /alcohol?limit=200&offset=0`
- `POST /alcohol`
- `PUT /alcohol/id/{row_id}`
- `DELETE /alcohol/id/{row_id}`
- `GET /cocktails?limit=200&offset=0`
- `POST /cocktails`
- `PUT /cocktails/id/{row_id}`
- `DELETE /cocktails/id/{row_id}`
- `GET /alcohol/{brand}`
- `GET /cocktails/{name}`
- `GET /tasting-logs`
- `POST /tasting-logs`
- `DELETE /tasting-logs/{id}`
- `GET /saved-views`
- `POST /saved-views`
- `DELETE /saved-views/{view_id}`
- `GET /tags`
- `POST /tags`
- `DELETE /tags/{tag_id}`
- `GET /analytics/cost-insights`
- `POST /ai/twist-suggestions`

## Data Safety

- Existing data is preserved; writes are enabled only through controlled API endpoints listed above.
- Additive schema changes only: `tasting_log`, `saved_views`, and `tags` tables are created if missing.
- Write/delete operations currently enabled for `tasting_log`, `saved_views`, `tags`, rowid-addressed alcohol CRUD, and rowid-addressed cocktail CRUD endpoints.
- DB path defaults to the project root `cocktail_database.db`.
- Override DB path with env var `COCKTAIL_DB_PATH`.

## Tasting Log Persistence

- On startup, backend runs additive migration: `CREATE TABLE IF NOT EXISTS tasting_log (...)`.
- Existing tables/data are not modified.
- Frontend tasting entries now persist in SQLite through `/tasting-logs` endpoints.

## Backup and Validation Scripts

- Create timestamped DB backup + checksum report:
  - `python scripts/backup_db.py`
- Validate DB integrity and required tables/counts:
  - `python scripts/validate_db.py`
- Optional explicit DB path:
  - `python scripts/backup_db.py --db "C:\path\to\cocktail_database.db"`
  - `python scripts/validate_db.py --db "C:\path\to\cocktail_database.db"`
- CRUD parity smoke (create/update/delete for alcohol + cocktails, then drift check):
  - `python scripts/smoke_crud_parity.py --api-base http://127.0.0.1:8001`
- Cutover gate (DB validation + endpoint health + CRUD parity smoke):
  - `python scripts/cutover_gate.py --api-base http://127.0.0.1:8001`

## Cutover Readiness

- Manual + operational checks are documented in:
  - `CUTOVER_CHECKLIST.md`

## AI Twist Suggestions

- `POST /ai/twist-suggestions` supports `provider=local`, `provider=groq`, or `provider=gemini`.
- Local mode returns deterministic twist suggestions (no external API call).
- Groq mode calls `https://api.groq.com/openai/v1/chat/completions` when `GROQ_API_KEY` is configured.
- Gemini mode calls `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` when `GEMINI_API_KEY` is configured.
- Optional env vars:
  - `GROQ_API_KEY` (required for cloud mode)
  - `GROQ_MODEL` (default: `llama-3.1-8b-instant`)
  - `GROQ_TIMEOUT_SECONDS` (default: `20`)
  - `GEMINI_API_KEY` (required for Gemini mode)
  - `GEMINI_MODEL` (default: `gemini-1.5-flash`)
  - `GEMINI_TIMEOUT_SECONDS` (default: `20`)
- If cloud keys are missing or requests fail, backend returns local fallback suggestions with an explanatory note.
