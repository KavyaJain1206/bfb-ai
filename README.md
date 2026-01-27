# Community Water Health Early Warning API

AI-assisted FastAPI service that ingests community water-health comments, structures them with Gemini, and runs rule-based alerts for early outbreak detection.

## What it does

- Accepts raw water-health reports (`/comments`) and stores them in `data/raw_community_comments_FINAL.json`.
- Uses Gemini 2.5 (via google-genai) to turn free-text comments into structured health signals (`/process`, `/process/test`), saved to `data/structured_signals.json`.
- Applies a rule engine (`rules.py`) to generate village-level alerts based on severity, volume, and symptom patterns (`/alerts`), saved to `data/alerts.json`.
- Exposes read-only endpoints for raw comments and structured signals (`/comments`, `/signals`).

## Architecture at a glance

- **API**: FastAPI app in [main.py](main.py); Pydantic model for input validation.
- **AI layer**: Gemini client (model `gemini-2.5-flash`) called with a constrained JSON prompt; responses parsed safely via `extract_json()`.
- **Rule engine**: `run_all_rules()` in [rules.py](rules.py) (severity clusters, volume spikes, symptom combinations, trend detection, weighted scores, multi-rule escalation).
- **Storage**: JSON files under `data/`; directories auto-created if missing.
- **Utilities**: Basic health check at `/health`; batch size and rate-limit handling in `/process` (max 5 per run).

## Key endpoints

- `GET /health` — service liveness probe.
- `GET /comments` — list stored raw comments.
- `POST /comments` — add a comment (fields: `user_id`, `village`, `comment`).
- `POST /process` — batch-process up to 5 new comments through Gemini into structured signals.
- `POST /process/test` — run a single comment through Gemini for quick inspection.
- `GET /signals` — list structured signals.
- `GET /alerts` — run rule engine on signals and return alerts (also writes `data/alerts.json`).

## Data flow

1. POST comment → stored raw with timestamp.
2. `/process` or `/process/test` → Gemini converts to `{village, water_source, symptoms[], severity}` JSON.
3. Structured records accumulate in `data/structured_signals.json`.
4. `/alerts` applies rules over recent timestamps to emit alert objects.

## Running locally

1. Install deps (e.g., `pip install fastapi uvicorn python-dotenv google-genai pydantic`).
2. Set `GEMINI_API_KEY` in `.env` (required).
3. Start the API: `uvicorn main:app --reload`.
4. Try it:
   - Add data: `curl -X POST http://localhost:8000/comments -H "Content-Type: application/json" -d '{"user_id":1,"village":"Laketown","comment":"People have fever and loose motion"}'`
   - Process: `curl -X POST http://localhost:8000/process`
   - Alerts: `curl http://localhost:8000/alerts`

## Prompts and limits

- Prompt restricts symptoms to: loose motion, fever, stomach pain, vomiting, weakness, headache.
- Severity logic: low (1 symptom), medium (2 symptoms), high (3+ symptoms).
- `/process` caps each run at 5 new comments; backs off on 429/RESOURCE_EXHAUSTED signals.

## Files of interest

- [main.py](main.py) — API, Gemini calls, JSON I/O.
- [rules.py](rules.py) — 13 alert rules + escalation.
- [cleaning.py](cleaning.py) — placeholder.
- [data/](data) — JSON storage (auto-created on run).
- [README_FIXES.md](README_FIXES.md), [FIXES_SUMMARY.md](FIXES_SUMMARY.md), [QUICK_FIX_GUIDE.md](QUICK_FIX_GUIDE.md) — prior code review notes.

## Safety and validation

- Input validation blocks empty/oversized comments and blank villages.
- Robust JSON extraction guards against malformed Gemini responses.
- Timestamps preserved end-to-end to keep rules accurate.
- Errors returned with context; rate-limit flag surfaced to clients.

## Limitations and next steps

- JSON file storage is not ideal for scale; consider SQLite/Postgres.
- Processing is synchronous; move to background jobs for high volume.
- Add metrics/logging for observability; add auth if exposed beyond trusted network.
