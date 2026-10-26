import logging
import os
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

# Load .env first: db.py and weather.py read MAZHAI_DB_PATH / timeouts / TTL at import time.
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

from fastapi import FastAPI, HTTPException, Query, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.middleware.gzip import GZipMiddleware  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field, field_validator  # noqa: E402
from .districts import DISTRICTS  # noqa: E402
from .places import places_for_district  # noqa: E402
from .database.db import init_db, prune_cache  # noqa: E402
from .services.weather import get_forecast, get_place_forecast, get_district_places_forecast, get_history, get_statewide_forecast, get_source_status, ProviderError  # noqa: E402
from .services.ai import ask_mistral  # noqa: E402

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("mazhai.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    try:
        removed = prune_cache(int(os.getenv("CACHE_RETENTION_DAYS", "30")))
        if removed:
            log.info("Pruned %d expired api_cache rows", removed)
    except Exception:  # housekeeping must never stop the app from starting
        log.exception("api_cache pruning failed")
    yield

app = FastAPI(title="Mazhai AI API", version="1.0.0", description="Tamil Nadu rainfall intelligence API", lifespan=lifespan)
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://127.0.0.1:8001,http://localhost:8001").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET","POST"], allow_headers=["Content-Type"])
app.add_middleware(GZipMiddleware, minimum_size=1024)

# Conservative headers that do not interfere with the CDN-hosted Leaflet/Chart.js/fonts the frontend uses.
# (A strict Content-Security-Policy is deliberately not set: the UI relies on inline styles and third-party CDNs.)
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
}

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response

class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1500)

    @field_validator("content", mode="before")
    @classmethod
    def bound_history_content(cls, value):
        # Older assistant answers can be longer than the per-turn context budget.
        # Trim history rather than rejecting the user's next chat request (422).
        if isinstance(value, str):
            return value[:1500]
        return value

class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1200)
    district_id: str | None = None
    language: Literal["en", "ta"] = "en"
    start: str | None = None
    end: str | None = None
    history: list[ChatTurn] = Field(default_factory=list, max_length=12)

# Simple in-memory sliding-window limiter for the costly AI endpoint (per client IP).
AI_RATE_LIMIT = int(os.getenv("AI_RATE_LIMIT_PER_MIN", "10"))
_ai_hits = defaultdict(deque)
_ai_lock = threading.Lock()
_AI_SWEEP_THRESHOLD = 1000  # sweep idle clients once this many are tracked

def _check_ai_rate(client_id):
    if AI_RATE_LIMIT <= 0:
        return
    now = time.monotonic()
    # Sync endpoints run in a thread pool, so the check-then-append must be atomic.
    with _ai_lock:
        if len(_ai_hits) > _AI_SWEEP_THRESHOLD:
            # Without this, every distinct client IP would stay in memory forever.
            for key in [k for k, q in _ai_hits.items() if not q or now - q[-1] > 60]:
                del _ai_hits[key]
        hits = _ai_hits[client_id]
        while hits and now - hits[0] > 60:
            hits.popleft()
        if len(hits) >= AI_RATE_LIMIT:
            raise HTTPException(429, "Too many AI requests. Please wait a minute and try again.")
        hits.append(now)

@app.get("/api/health")
def health():
    return {"status":"ok","service":"Mazhai AI","time":datetime.now(timezone.utc).isoformat()}

@app.get("/api/districts")
def districts(q: str | None = None):
    items = DISTRICTS
    if q:
        needle = q.casefold().strip()
        items = [d for d in DISTRICTS if needle in d["name"].casefold() or needle in d["id"]]
    return {"count":len(items),"districts":items,"coordinate_note":"Representative district coordinates for grid-based weather lookups; not station locations or district boundaries."}

@app.get("/api/districts/{district_id}")
def district_detail(district_id: str):
    district = next((d for d in DISTRICTS if d["id"] == district_id.casefold()), None)
    if not district:
        raise HTTPException(404, "District not found")
    return {**district,"coordinate_note":"Representative district coordinates; town and station coverage may differ."}

@app.get("/api/districts/{district_id}/places")
def district_places(district_id: str):
    """Towns / taluk headquarters inside a district, as map points (not boundaries)."""
    district = next((d for d in DISTRICTS if d["id"] == district_id.casefold()), None)
    if not district:
        raise HTTPException(404, "District not found")
    places = places_for_district(district["id"]) or []
    return {"district": district, "count": len(places), "places": places, "coordinate_note": "Approximate town-centre points, not administrative boundaries. Weather for a place is a model/grid estimate at that point."}

@app.get("/api/weather/forecast")
def forecast(district_id: str = Query(..., min_length=2), refresh: bool = False):
    try:
        return get_forecast(district_id, force=refresh)
    except ValueError as exc:
        raise HTTPException(404 if str(exc) == "Unknown district" else 400, str(exc))
    except ProviderError as exc:
        raise HTTPException(503, {"message":str(exc),"hint":"Check network connectivity; retry later. No fabricated forecast is shown."})

@app.get("/api/weather/place")
def place_forecast(district_id: str = Query(..., min_length=2), place_id: str = Query(..., min_length=2), refresh: bool = False):
    try:
        return get_place_forecast(district_id, place_id, force=refresh)
    except ValueError as exc:
        raise HTTPException(404 if str(exc).startswith("Unknown") else 400, str(exc))
    except ProviderError as exc:
        raise HTTPException(503, {"message":str(exc),"hint":"Check network connectivity; retry later. No fabricated forecast is shown."})

@app.get("/api/weather/district-places")
def district_places_forecast(district_id: str = Query(..., min_length=2), refresh: bool = False):
    """7-day forecast totals for every place in a district, fetched with a single upstream request."""
    try:
        return get_district_places_forecast(district_id, force=refresh)
    except ValueError as exc:
        raise HTTPException(404 if str(exc).startswith(("Unknown", "No places")) else 400, str(exc))
    except ProviderError as exc:
        raise HTTPException(503, {"message":str(exc),"hint":"Check network connectivity; retry later. No fabricated forecast is shown."})

@app.get("/api/weather/statewide")
def statewide(refresh: bool = False):
    """7-day forecast totals for all districts, fetched with a single upstream request."""
    try:
        return get_statewide_forecast(force=refresh)
    except ProviderError as exc:
        raise HTTPException(503, {"message":str(exc),"hint":"Check network connectivity; retry later. No fabricated forecast is shown."})

@app.get("/api/rainfall/history")
def history(district_id: str = Query(..., min_length=2), start: str = Query(...), end: str = Query(...), refresh: bool = False):
    try:
        return get_history(district_id, start, end, force=refresh)
    except ValueError as exc:
        raise HTTPException(404 if str(exc) == "Unknown district" else 400, str(exc))
    except ProviderError as exc:
        raise HTTPException(503, {"message":str(exc),"hint":"Historical data could not be retrieved. Try again later."})

@app.get("/api/rainfall/summary")
def summary(district_id: str = Query(...), start: str = Query(...), end: str = Query(...)):
    try:
        result = get_history(district_id, start, end)
    except ValueError as exc:
        raise HTTPException(404 if str(exc) == "Unknown district" else 400, str(exc))
    except ProviderError as exc:
        raise HTTPException(503, str(exc))
    values = [r["precipitation_mm"] for r in result["records"] if isinstance(r.get("precipitation_mm"), (int,float))]
    wet = [v for v in values if v >= 1.0]
    return {"district":result["district"],"start":start,"end":end,"days_returned":len(result["records"]),"valid_days":len(values),"total_precipitation_mm":round(sum(values),2) if values else None,"wet_days_1mm_or_more":len(wet),"mean_daily_mm":round(sum(values)/len(values),2) if values else None,"max_daily_mm":max(values) if values else None,"source":result["source"],"retrieved_at":result.get("retrieved_at"),"stale":result.get("stale",False)}

@app.get("/api/sources/status")
def source_status():
    return get_source_status()

@app.post("/api/ai/ask")
def ai_ask(body: AskRequest, request: Request):
    _check_ai_rate(request.client.host if request.client else "unknown")
    district_id = body.district_id.strip().casefold() if body.district_id else None
    if district_id and not any(d["id"] == district_id for d in DISTRICTS):
        raise HTTPException(404, "District not found")
    if bool(body.start) != bool(body.end):
        raise HTTPException(400, "Provide both start and end dates for historical context.")
    if body.start and body.end:
        try:
            if date.fromisoformat(body.end) < date.fromisoformat(body.start):
                raise HTTPException(400, "End date must be on or after start date.")
        except ValueError:
            raise HTTPException(400, "Dates must use YYYY-MM-DD format")
    return ask_mistral(body.question.strip(), district_id, body.start, body.end, [t.model_dump() for t in body.history], language=body.language)

@app.get("/api/analytics/district-comparison")
def comparison(start: str = Query(...), end: str = Query(...)):
    # Validate once so a bad range gives one clear 400 instead of 38 identical failures.
    try:
        s_d, e_d = date.fromisoformat(start), date.fromisoformat(end)
    except ValueError:
        raise HTTPException(400, "Dates must use YYYY-MM-DD format")
    if e_d < s_d:
        raise HTTPException(400, "End date must be on or after start date")
    if (e_d - s_d).days > 3660:
        raise HTTPException(400, "Date range cannot exceed 10 years")

    def fetch(district):
        try:
            data = get_history(district["id"], start, end)
            values = [r["precipitation_mm"] for r in data["records"] if isinstance(r.get("precipitation_mm"), (int, float))]
            return {"district_id": district["id"], "district": district["name"], "total_mm": round(sum(values), 2) if values else None, "valid_days": len(values), "source": data["source"], "error": None}
        except Exception as exc:
            return {"district_id": district["id"], "district": district["name"], "total_mm": None, "valid_days": 0, "source": None, "error": exc.__class__.__name__}

    # Bounded concurrency: much faster than 38 sequential calls, gentle on the upstream rate limit.
    with ThreadPoolExecutor(max_workers=int(os.getenv("COMPARISON_WORKERS", "6"))) as pool:
        results = list(pool.map(fetch, DISTRICTS))
    valid = [r for r in results if r["total_mm"] is not None]
    return {"start": start, "end": end, "districts": results, "successful_districts": len(valid), "note": "Totals are grid/reanalysis estimates at representative coordinates, not official district-wide rainfall totals."}

FRONTEND = ROOT / "frontend"
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
