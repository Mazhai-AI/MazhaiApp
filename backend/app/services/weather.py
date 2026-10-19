import json
import os
from datetime import datetime, timezone, date, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from ..database.db import connect
from ..districts import DISTRICTS

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
TIMEOUT = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "12"))
CACHE_TTL_SECONDS = int(os.getenv("WEATHER_CACHE_TTL_SECONDS", "900"))

class ProviderError(RuntimeError):
    pass

def _get_json(url, params):
    request = Request(url + "?" + urlencode(params), headers={"User-Agent":"MazhaiAI/1.0 (Tamil Nadu rainfall intelligence)"})
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            if response.status != 200:
                raise ProviderError(f"Weather provider returned HTTP {response.status}")
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        reason = ""
        try:
            reason = json.loads(exc.read().decode("utf-8")).get("reason", "")
        except Exception:
            pass
        raise ProviderError(f"Weather provider rejected the request (HTTP {exc.code}){': ' + reason if reason else ''}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ProviderError(f"Weather provider unavailable: {exc.__class__.__name__}") from exc
    if not isinstance(data, dict) or data.get("error"):
        raise ProviderError("Weather provider returned an invalid response")
    return data

def _cached(key):
    with connect() as conn:
        row = conn.execute("SELECT payload, fetched_at FROM api_cache WHERE cache_key=?", (key,)).fetchone()
    if not row:
        return None
    try:
        fetched = datetime.fromisoformat(row["fetched_at"])
        age = (datetime.now(timezone.utc) - fetched).total_seconds()
        return {"payload": json.loads(row["payload"]), "fetched_at": row["fetched_at"], "stale": age > CACHE_TTL_SECONDS}
    except (ValueError, json.JSONDecodeError):
        return None

def _save_cache(key, payload):
    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        conn.execute("INSERT INTO api_cache(cache_key,payload,fetched_at) VALUES(?,?,?) ON CONFLICT(cache_key) DO UPDATE SET payload=excluded.payload,fetched_at=excluded.fetched_at", (key, json.dumps(payload), now))
    return now

def district_by_id(district_id):
    return next((d for d in DISTRICTS if d["id"] == str(district_id).strip().lower()), None)

def get_forecast(district_id, force=False):
    district = district_by_id(district_id)
    if not district:
        raise ValueError("Unknown district")
    district_id = district["id"]
    key = f"forecast:{district_id}"
    cached = _cached(key)
    if cached and not force and not cached["stale"]:
        return {**cached["payload"], "cached": True, "stale": False, "retrieved_at": cached["fetched_at"]}
    params = {
        "latitude": district["lat"], "longitude": district["lon"],
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,cloud_cover",
        "hourly": "precipitation,precipitation_probability,temperature_2m",
        "daily": "precipitation_sum,precipitation_probability_max,temperature_2m_max,temperature_2m_min",
        "forecast_days": 7, "timezone": "Asia/Kolkata"
    }
    try:
        raw = _get_json(FORECAST_URL, params)
        current = raw.get("current", {})
        daily = raw.get("daily", {})
        hourly = raw.get("hourly", {})
        hourly_times = hourly.get("time", [])
        current_time = current.get("time")
        # Forecast API hourly arrays often begin at local midnight. Start the
        # display/evidence window at the current provider timestamp instead of
        # accidentally summing hours that have already elapsed.
        hourly_start = next(
            (i for i, stamp in enumerate(hourly_times)
             if isinstance(stamp, str) and isinstance(current_time, str) and stamp >= current_time),
            0,
        )
        hourly_end = min(hourly_start + 48, len(hourly_times))
        hourly_indices = range(hourly_start, hourly_end)
        payload = {
            "district": district, "source": "Open-Meteo Forecast API",
            "source_url": "https://open-meteo.com/en/docs",
            "model_timezone": raw.get("timezone", "Asia/Kolkata"),
            "current": {
                "time": current.get("time"), "temperature_c": current.get("temperature_2m"),
                "humidity_pct": current.get("relative_humidity_2m"), "precipitation_mm": current.get("precipitation"),
                "wind_kmh": current.get("wind_speed_10m"), "wind_direction_deg": current.get("wind_direction_10m"),
                "cloud_cover_pct": current.get("cloud_cover")
            },
            "daily": [
                {"date": daily.get("time", [])[i],
                 "precipitation_mm": _at(daily.get("precipitation_sum"), i),
                 "precipitation_probability_pct": _at(daily.get("precipitation_probability_max"), i),
                 "temp_max_c": _at(daily.get("temperature_2m_max"), i),
                 "temp_min_c": _at(daily.get("temperature_2m_min"), i)}
                for i in range(len(daily.get("time", [])))
            ],
            "hourly": [
                {"time": hourly.get("time", [])[i],
                 "precipitation_mm": _at(hourly.get("precipitation"), i),
                 "precipitation_probability_pct": _at(hourly.get("precipitation_probability"), i),
                 "temperature_c": _at(hourly.get("temperature_2m"), i)}
                for i in hourly_indices
            ],
            "fetched_live": True
        }
        fetched_at = _save_cache(key, payload)
        return {**payload, "cached": False, "stale": False, "retrieved_at": fetched_at}
    except ProviderError:
        if cached:
            return {**cached["payload"], "cached": True, "stale": True, "retrieved_at": cached["fetched_at"], "warning": "Provider unavailable; showing cached data."}
        raise

def _at(values, i):
    return values[i] if isinstance(values, list) and i < len(values) else None

def get_history(district_id, start, end, force=False):
    district = district_by_id(district_id)
    if not district:
        raise ValueError("Unknown district")
    district_id = district["id"]
    try:
        start_d, end_d = date.fromisoformat(start), date.fromisoformat(end)
    except ValueError as exc:
        raise ValueError("Dates must use YYYY-MM-DD format") from exc
    if end_d < start_d:
        raise ValueError("End date must be on or after start date")
    if (end_d - start_d).days > 3660:
        raise ValueError("Date range cannot exceed 10 years")
    key = f"history:{district_id}:{start}:{end}"
    cached = _cached(key)
    if cached and not force and not cached["stale"]:
        return {**cached["payload"], "cached": True, "stale": False, "retrieved_at": cached["fetched_at"]}
    params = {"latitude":district["lat"], "longitude":district["lon"], "start_date":start, "end_date":end, "daily":"precipitation_sum", "timezone":"Asia/Kolkata"}
    try:
        raw = _get_json(ARCHIVE_URL, params)
        daily = raw.get("daily", {})
        records = [{"date": daily["time"][i], "precipitation_mm": _at(daily.get("precipitation_sum"), i)} for i in range(len(daily.get("time", [])))]
        payload = {"district":district, "source":"Open-Meteo Historical Weather API (reanalysis)", "source_url":"https://open-meteo.com/en/docs/historical-weather-api", "records":records, "fetched_live":True}
        fetched_at = _save_cache(key, payload)
        with connect() as conn:
            conn.executemany("INSERT INTO rainfall_observations(district_id,observed_date,precipitation_mm,source,retrieved_at) VALUES(?,?,?,?,?) ON CONFLICT(district_id,observed_date,source) DO UPDATE SET precipitation_mm=excluded.precipitation_mm,retrieved_at=excluded.retrieved_at",
                [(district_id, r["date"], r["precipitation_mm"], payload["source"], fetched_at) for r in records])
        return {**payload, "cached":False, "stale":False, "retrieved_at":fetched_at}
    except ProviderError:
        if cached:
            return {**cached["payload"], "cached":True, "stale":True, "retrieved_at":cached["fetched_at"], "warning":"Provider unavailable; showing cached data."}
        raise

def get_source_status():
    with connect() as conn:
        rows = conn.execute("SELECT source, MAX(retrieved_at) AS latest, COUNT(*) AS records FROM rainfall_observations GROUP BY source").fetchall()
        cache_count = conn.execute("SELECT COUNT(*) FROM api_cache").fetchone()[0]
    return {
        "providers":[
            {"name":"Open-Meteo Forecast API","kind":"Forecast and current conditions","status":"configured","url":"https://open-meteo.com/en/docs","notes":"Forecast/reanalysis model data at district representative coordinates; not an official IMD warning."},
            {"name":"Open-Meteo Historical Weather API","kind":"Historical daily precipitation","status":"configured","url":"https://open-meteo.com/en/docs/historical-weather-api","notes":"Historical reanalysis/grid estimates, not direct rain-gauge observations."},
            {"name":"India Meteorological Department (IMD)","kind":"Official observations and warnings","status":"not_integrated","url":"https://mausam.imd.gov.in/","notes":"No direct feed configured; consult official IMD bulletins for authoritative warnings."}
        ],
        "stored_history":[dict(r) for r in rows], "cache_entries":cache_count,
        "generated_at":datetime.now(timezone.utc).isoformat()
    }
