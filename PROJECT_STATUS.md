# Mazhai AI — Project Status

Updated: 2026-10-20

## Completed in this implementation
- [x] Responsive dark dashboard shell with navigation for all requested sections.
- [x] Directory of 38 Tamil Nadu districts with representative coordinates.
- [x] FastAPI application, health endpoint, validation, and SQLite initialization.
- [x] Open-Meteo current/forecast integration and historical reanalysis integration.
- [x] SQLite response cache and persisted historical precipitation records.
- [x] Forecast, history, summary, district-comparison, and source-status API routes.
- [x] Optional server-side Mistral integration with evidence retrieval and graceful missing-key behavior.
- [x] Leaflet map markers, overview metrics, charts, CSV export, district explorer, assistant, sources, settings.
- [x] Documentation, `.env.example`, launch script, and deterministic tests.

## Added in the hardening pass (2026-10-20)
- [x] Fixed three escaping bugs in `ai.py`: the trailing-comma JSON repair never matched, the array-salvage escape handling was dead code, and combined retry instructions were joined with a literal `\n\n` instead of newlines.
- [x] `.env` and `data/mazhai.db` removed from git tracking (they were already listed in `.gitignore`). **A Mistral key was committed earlier; rotate it** — it remains in git history.
- [x] Upstream: one retry for transient failures, longer cache TTL for settled historical ranges, `api_cache` pruning at startup.
- [x] SQLite WAL mode and busy timeout for the threaded district comparison.
- [x] Security headers, gzip, thread-safe AI rate limiter that no longer grows without bound.
- [x] `GET /api/weather/statewide` and a statewide-coloured district map (single multi-location upstream request).
- [x] Skip link and `aria-current` navigation state.

## Added: places inside a district
- [x] Every district now has a list of towns / taluk headquarters (`backend/app/places.py`, ~230 places), shown as markers and a list when a district is selected in the weather explorer.
- [x] `GET /api/districts/{id}/places`, `GET /api/weather/place` (forecast at a place's own coordinates, cached per place) and `GET /api/weather/district-places` (7-day totals for all places in a district, one upstream request).
- [x] Selecting a place opens its current conditions and 7-day outlook; Back returns to the district.
- [x] Fixed: Chennai's ward polygons stayed on the map after selecting another district.

## Explicitly not completed / limitations
- IMD observation ingestion and official warning ingestion are not implemented.
- No verified historical flood/incident dataset is connected.
- District coordinates are representative points; district/taluk boundary polygons and true station locations are not included. Place coordinates are hand-compiled approximate town centres and have not been verified against an official gazetteer.
- No trained/calibrated local ML model, hindcast evaluation, or calibrated flood-risk model.
- No email/push notifications or scheduled ingestion worker.
- External CDN assets require network connectivity.
- Real upstream API access and Mistral credentials must be verified in the target runtime.

## Validation
- `python -m unittest discover -s tests -v`: **55 tests passed**. `node tests/test_markdown_renderer.cjs` and `node tests/test_i18n.cjs`: passed.
- `python -m compileall -q backend tests`: passed.
- `node --check frontend/js/app.js`: passed.
- Local Uvicorn smoke test: `/api/health` returned HTTP 200; frontend `/` returned HTTP 200; `/api/districts` returned all 38 districts.
- Live Open-Meteo request attempted, but the build environment could not reach the upstream network (`URLError`). The app correctly returned HTTP 503 and did not fabricate a forecast. Verify live weather in a network-enabled environment.
- Statewide forecast: verified against a mocked multi-location upstream response and a local server smoke test (honest 503 without network). It has **not** been run against the live Open-Meteo API from the build environment; confirm the colours appear on the map after deploying.
- Not covered by automated tests: the map/popup rendering in a real browser.
