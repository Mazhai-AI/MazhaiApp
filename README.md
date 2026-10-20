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
- Optional Mistral assistant that receives retrieved weather/history evidence and returns validated structured sections (current forecast, historical context, what to watch, actions, and limitations).
- English/Tamil interface language selector in Settings, saved in the browser; the AI assistant follows the selected language for response content.
- AI response-language enforcement: the backend checks every generated answer section against the selected English/Tamil language, retries once on a mismatch, and uses a localized fallback if the provider still returns the wrong language.
- The AI system prompt emphasizes evidence-grounded answers, conversational follow-up continuity, concise recommendations, valid structured output, and clear handling of missing or stale data.
- An explicitly labelled app-generated rainfall-attention indicator that combines upcoming forecast rainfall with recent historical rainfall; it never claims to be an official warning.
- A statewide forecast map: every district marker is coloured from a single multi-location Open-Meteo request (missing values stay "not available", never zero).
- API validation, bounded upstream timeouts, one automatic retry for transient upstream failures, a SQLite cache (longer for settled historical ranges), and tests.
- Baseline security headers and gzip compression, plus basic keyboard/screen-reader navigation aids (skip link, `aria-current`).

## Important data limitations

- Open-Meteo forecast responses are model forecasts; historical API values are reanalysis/grid estimates. They are **not direct IMD rain-gauge observations** and the representative coordinates are not district boundaries.
- Coverage can vary by date and location. Missing values are not treated as zero.
- IMD data and official warnings are listed as not integrated. The application links to IMD, but does not claim to ingest or reproduce official warnings.
- This initial version does not ingest verified historical flood/incident reports, does not train a local ML model, and does not issue flood forecasts or emergency alerts.
- The dashboard signal and AI rainfall-attention bands are preliminary app-generated screening indicators based on available forecast amounts and recent rainfall context. Their thresholds are not calibrated, validated impact thresholds, or official IMD categories; they are not flood predictions or emergency alerts. Follow official IMD bulletins and local authority instructions for safety decisions.
- Mistral is an optional explanation layer, not a numerical weather prediction engine. Its prompt directs it to use retrieved evidence rather than invent measurements, avoid treating prior assistant responses as facts, answer narrow follow-ups directly, and retain the user's selected English/Tamil response language.

## Requirements

- Python 3.10 or newer.
- A modern browser with JavaScript enabled; the Tamil interface uses the Noto Sans Tamil web font when available.
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
| `UPSTREAM_RETRIES` | Extra attempts for transient upstream failures (HTTP 429/5xx, timeouts, connection errors) | `1` |
| `UPSTREAM_RETRY_BACKOFF_SECONDS` | Base delay between those attempts | `0.5` |
| `HISTORY_PAST_CACHE_TTL_SECONDS` | Cache TTL for historical ranges that ended more than 7 days ago (recent ranges use `WEATHER_CACHE_TTL_SECONDS`) | `86400` |
| `CACHE_RETENTION_DAYS` | `api_cache` rows older than this are deleted at startup (stored rainfall observations are kept) | `30` |
| `FORWARDED_ALLOW_IPS` | uvicorn setting: proxy addresses whose `X-Forwarded-For` is trusted (see Production notes) | `127.0.0.1` |
| `LOG_LEVEL` | Backend log level | `INFO` |

## API endpoints

- `GET /api/health`
- `GET /api/districts?q=...`
- `GET /api/districts/{district_id}`
- `GET /api/weather/forecast?district_id=chennai&refresh=false`
- `GET /api/weather/statewide?refresh=false` (7-day forecast totals for all districts, one upstream request)
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

Tests cover `.env` load order, district-ID normalization, API validation, language selection/AI language instructions, comparison, the AI layer (string/list answers, chat history, error mapping, malformed responses), upstream retries, cache TTLs and pruning, the statewide endpoint, SQLite WAL mode, security headers/gzip, and the AI rate limiter, all with mocked upstreams. Real-provider integration requires network access and is intentionally not part of deterministic unit tests.

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
- The AI endpoint has a basic in-memory per-IP rate limit; behind multiple workers, add real throttling/authentication before exposing it publicly.
- Behind a reverse proxy or platform router (Render, nginx, a load balancer) every request appears to come from the proxy's address unless you tell uvicorn to trust it, so the per-IP limit becomes one shared limit for all users. Set `FORWARDED_ALLOW_IPS` to your proxy's address (or `*` only if the app is reachable exclusively through that proxy, since otherwise clients could spoof their IP).
- Responses carry baseline security headers (`X-Content-Type-Options`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy`, `Permissions-Policy`). A strict `Content-Security-Policy` and Subresource Integrity for the CDN scripts are not set yet: the UI uses inline styles and unpinned CDN assets.
- Never commit `.env`. If a key was ever committed, rotate it at the provider; deleting the file does not remove it from git history.
- For reliable scheduled ingestion and larger concurrent deployments, move refresh work into a background job and consider PostgreSQL.
- Chennai's city explorer includes 200 numbered ward polygons from the DataMeet Municipal Spatial Data project, attributed to Transparent Chennai and licensed under CC BY-SA 2.5 India. See [`frontend/data/geo/README.md`](frontend/data/geo/README.md) for provenance and limitations. The dataset is community-curated and should be checked against current Greater Chennai Corporation/Government Gazette ward maps before authoritative use.
- Check provider terms, attribution, licensing, rate limits, and model metadata before public/commercial deployment.

## Site
https://mazhaiapp.onrender.com/
