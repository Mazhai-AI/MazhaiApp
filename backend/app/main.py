from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .districts import DISTRICTS
from .database.db import init_db
from .services.weather import get_forecast, get_history, get_source_status, ProviderError
from .services.ai import ask_mistral

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Mazhai AI API", version="1.0.0", description="Tamil Nadu rainfall intelligence API", lifespan=lifespan)
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://127.0.0.1:8001,http://localhost:8001").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET","POST"], allow_headers=["Content-Type"])

class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1200)
    district_id: str | None = None
    start: str | None = None
    end: str | None = None

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

@app.get("/api/weather/forecast")
def forecast(district_id: str = Query(..., min_length=2), refresh: bool = False):
    try:
        return get_forecast(district_id, force=refresh)
    except ValueError as exc:
        raise HTTPException(404 if str(exc) == "Unknown district" else 400, str(exc))
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
def ai_ask(body: AskRequest):
    if body.district_id and not any(d["id"] == body.district_id.casefold() for d in DISTRICTS):
        raise HTTPException(404, "District not found")
    if bool(body.start) != bool(body.end):
        raise HTTPException(400, "Provide both start and end dates for historical context.")
    return ask_mistral(body.question, body.district_id.casefold() if body.district_id else None, body.start, body.end)

@app.get("/api/analytics/district-comparison")
def comparison(start: str = Query(...), end: str = Query(...)):
    # Keep requests bounded and report partial provider failures instead of fabricating values.
    results=[]
    for district in DISTRICTS:
        try:
            data=get_history(district["id"],start,end)
            values=[r["precipitation_mm"] for r in data["records"] if isinstance(r.get("precipitation_mm"),(int,float))]
            results.append({"district_id":district["id"],"district":district["name"],"total_mm":round(sum(values),2) if values else None,"valid_days":len(values),"source":data["source"],"error":None})
        except Exception as exc:
            results.append({"district_id":district["id"],"district":district["name"],"total_mm":None,"valid_days":0,"source":None,"error":exc.__class__.__name__})
    valid=[r for r in results if r["total_mm"] is not None]
    return {"start":start,"end":end,"districts":results,"successful_districts":len(valid),"note":"Totals are grid/reanalysis estimates at representative coordinates, not official district-wide rainfall totals."}

FRONTEND = ROOT / "frontend"
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
