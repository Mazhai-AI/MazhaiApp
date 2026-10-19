# Mazhai AI — Tamil Nadu Rainfall Intelligence

Mazhai AI is a full-stack web application with an HTML/CSS/vanilla JavaScript frontend, FastAPI backend, SQLite persistence, Open-Meteo weather integrations, and optional Mistral AI explanations.

## Current capabilities

- Directory for all 38 Tamil Nadu districts, with representative reference coordinates.
- Current conditions and up to 7 days of provider forecasts.
- Historical daily precipitation queries and local persistence.
- Historical summaries, interactive charts, and CSV export.
- District comparison for a selected period.
- Leaflet district-reference map and district explorer.
- Source registry, data freshness, cached-data fallback, and transparent provider limitations.
- Optional Mistral assistant that receives retrieved weather/history evidence.
- API validation, bounded upstream timeouts, SQLite cache, and tests.

## Important data limitations

- Open-Meteo forecast responses are model forecasts; historical API values are reanalysis/grid estimates. They are **not direct IMD rain-gauge observations** and the representative coordinates are not district boundaries.
- Coverage can vary by date and location. Missing values are not treated as zero.
- IMD data and official warnings are listed as not integrated. The application links to IMD, but does not claim to ingest or reproduce official warnings.
- This initial version does not ingest verified historical flood/incident reports, does not train a local ML model, and does not issue flood forecasts or emergency alerts.
- The rainfall signal is not a calibrated risk score. Follow official IMD and local authority instructions for safety decisions.
- Mistral is an optional explanation layer, not a numerical weather prediction engine.

## Requirements

- Python 3.10 or newer.
- Internet connectivity for Open-Meteo and CDN assets.
- Optional Mistral API key for the AI assistant.

## Run locally

```bash
chmod +x run.sh
./run.sh
```

Open <http://127.0.0.1:8001>. The script creates `.venv`, installs backend requirements, and copies `.env.example` to `.env` if needed.

Manual setup:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
python -m pip install -r backend/requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8001
```

API docs: <http://127.0.0.1:8001/docs>

## Configure Mistral

Set these in `.env` on the server:

```dotenv
MISTRAL_API_KEY=your_server_side_key
MISTRAL_MODEL=ministral-8b-2512
```

Never put the key in frontend files, browser storage, or a committed repository. Leave `MAZHAI_DB_PATH` unset for local runs; the Dockerfile sets it for containers. The application starts without this key and shows a clear unavailable state.

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `MISTRAL_API_KEY` | Server-side Mistral credential | empty |
| `MISTRAL_MODEL` | Mistral chat model | `ministral-8b-2512` |
| `MAZHAI_DB_PATH` | SQLite database file | `./data/mazhai.db` |
| `UPSTREAM_TIMEOUT_SECONDS` | Upstream API timeout | `12` |
| `WEATHER_CACHE_TTL_SECONDS` | Weather cache TTL | `900` |
| `CORS_ORIGINS` | Allowed browser origins | local development origins |
| `AI_RATE_LIMIT_PER_MIN` | Max AI questions per client IP per minute (`0` disables) | `10` |
| `COMPARISON_WORKERS` | Parallel upstream requests for district comparison | `6` |
| `LOG_LEVEL` | Backend log level | `INFO` |

## API endpoints

- `GET /api/health`
- `GET /api/districts?q=...`
- `GET /api/districts/{district_id}`
- `GET /api/weather/forecast?district_id=chennai&refresh=false`
- `GET /api/rainfall/history?district_id=chennai&start=2026-09-01&end=2026-10-01`
- `GET /api/rainfall/summary?district_id=chennai&start=2026-09-01&end=2026-10-01`
- `GET /api/analytics/district-comparison?start=2026-09-01&end=2026-10-01`
- `GET /api/sources/status`
- `POST /api/ai/ask`
- `GET /docs` for interactive API documentation.

Historical requests are limited to 10 years per query. District comparison makes one historical request per district (with bounded parallelism) and may take time or partially fail if the upstream provider is rate-limited.

## Tests

```bash
python -m pip install -r backend/requirements.txt
python -m pip install httpx
python -m unittest discover -s tests -v
```

Tests cover `.env` load order, district-ID normalization, API validation, comparison, and the AI layer (string/list answers, chat history, error mapping, malformed responses), all with mocked upstreams. Real-provider integration requires network access and is intentionally not part of deterministic unit tests.

## Architecture

```text
frontend/               Static HTML, CSS, JavaScript modules
backend/app/main.py     FastAPI routes and static frontend hosting
backend/app/districts.py District directory
backend/app/services/   Weather and Mistral integrations
backend/app/database/   SQLite schema and connection handling
data/                   Runtime database (created automatically)
tests/                  Automated tests
```

## Production notes

- Serve over HTTPS behind a production ASGI server/reverse proxy.
- Set `CORS_ORIGINS` to the exact production origin.
- The AI endpoint has a basic in-memory per-IP rate limit; behind a proxy or multiple workers, add real throttling/authentication before exposing it publicly.
- For reliable scheduled ingestion and larger concurrent deployments, move refresh work into a background job and consider PostgreSQL.
- Add verified district boundary GeoJSON before rendering choropleths; this version intentionally uses representative coordinate markers.
- Check provider terms, attribution, licensing, rate limits, and model metadata before public/commercial deployment.
