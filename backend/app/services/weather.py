import json
import os
import time
from datetime import datetime, timezone, date, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from ..database.db import connect
from ..districts import DISTRICTS
from ..places import place_by_id, places_for_district

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
TIMEOUT = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "12"))
CACHE_TTL_SECONDS = int(os.getenv("WEATHER_CACHE_TTL_SECONDS", "900"))
# Historical days that are safely in the past rarely change, so they can be cached much longer.
HISTORY_PAST_CACHE_TTL_SECONDS = int(os.getenv("HISTORY_PAST_CACHE_TTL_SECONDS", "86400"))
# Reanalysis for the most recent days can still be revised; only ranges ending before this margin get the long TTL.
HISTORY_SETTLED_AFTER_DAYS = 7
# Transient upstream failures (HTTP 429/5xx, timeouts, connection errors) are retried this many extra times.
UPSTREAM_RETRIES = max(0, int(os.getenv("UPSTREAM_RETRIES", "1")))
RETRY_BACKOFF_SECONDS = float(os.getenv("UPSTREAM_RETRY_BACKOFF_SECONDS", "0.5"))
RETRYABLE_HTTP_STATUS = {429, 500, 502, 503, 504}
IST = timezone(timedelta(hours=5, minutes=30))  # India has no DST, so a fixed offset is exact.
STATEWIDE_CACHE_KEY = "statewide:forecast"

class ProviderError(RuntimeError):
    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.retryable = retryable

def _get_json_once(url, params, expect_list=False):
    request = Request(url + "?" + urlencode(params), headers={"User-Agent":"MazhaiAI/1.0 (Tamil Nadu rainfall intelligence)"})
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            if response.status != 200:
                raise ProviderError(f"Weather provider returned HTTP {response.status}", retryable=response.status in RETRYABLE_HTTP_STATUS)
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        reason = ""
        try:
            reason = json.loads(exc.read().decode("utf-8")).get("reason", "")
        except Exception:
            pass
        raise ProviderError(f"Weather provider rejected the request (HTTP {exc.code}){': ' + reason if reason else ''}", retryable=exc.code in RETRYABLE_HTTP_STATUS) from exc
    except (URLError, TimeoutError) as exc:
        raise ProviderError(f"Weather provider unavailable: {exc.__class__.__name__}", retryable=True) from exc
    except json.JSONDecodeError as exc:
        raise ProviderError(f"Weather provider unavailable: {exc.__class__.__name__}") from exc
    # A single location answers with an object; several locations answer with a list of objects.
    if expect_list:
        if not isinstance(data, list) or any(not isinstance(item, dict) or item.get("error") for item in data):
            raise ProviderError("Weather provider returned an invalid response")
    elif not isinstance(data, dict) or data.get("error"):
        raise ProviderError("Weather provider returned an invalid response")
    return data

def _get_json(url, params, expect_list=False):
    """Fetch JSON, retrying transient upstream failures with a short linear backoff."""
    attempts = UPSTREAM_RETRIES + 1
    for attempt in range(attempts):
        try:
            return _get_json_once(url, params, expect_list=expect_list)
        except ProviderError as exc:
            if attempt + 1 >= attempts or not exc.retryable:
                raise
            time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))

def _cached(key, ttl=None):
    ttl = CACHE_TTL_SECONDS if ttl is None else ttl
    with connect() as conn:
        row = conn.execute("SELECT payload, fetched_at FROM api_cache WHERE cache_key=?", (key,)).fetchone()
    if not row:
        return None
    try:
        fetched = datetime.fromisoformat(row["fetched_at"])
        age = (datetime.now(timezone.utc) - fetched).total_seconds()
        return {"payload": json.loads(row["payload"]), "fetched_at": row["fetched_at"], "stale": age > ttl}
    except (ValueError, json.JSONDecodeError):
        return None

def _save_cache(key, payload):
    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        conn.execute("INSERT INTO api_cache(cache_key,payload,fetched_at) VALUES(?,?,?) ON CONFLICT(cache_key) DO UPDATE SET payload=excluded.payload,fetched_at=excluded.fetched_at", (key, json.dumps(payload), now))
    return now

def district_by_id(district_id):
    return next((d for d in DISTRICTS if d["id"] == str(district_id).strip().lower()), None)

def _forecast_for(key, location, extra, force):
    """Cached 7-day forecast for ``location`` (any mapping with lat/lon).

    ``extra`` is merged into the payload to say what the point represents (a district, or a
    place inside one). Cache lookup, TTL and stale-fallback behaviour are shared by both.
    """
    cached = _cached(key)
    if cached and not force and not cached["stale"]:
        return {**cached["payload"], "cached": True, "stale": False, "retrieved_at": cached["fetched_at"]}
    params = {
        "latitude": location["lat"], "longitude": location["lon"],
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
            **extra, "source": "Open-Meteo Forecast API",
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

def get_forecast(district_id, force=False):
    district = district_by_id(district_id)
    if not district:
        raise ValueError("Unknown district")
    return _forecast_for(f"forecast:{district['id']}", district, {"district": district}, force)

def get_place_forecast(district_id, place_id, force=False):
    """Forecast at a place (town/taluk HQ) inside a district; same shape as ``get_forecast``."""
    district = district_by_id(district_id)
    if not district:
        raise ValueError("Unknown district")
    place = place_by_id(district["id"], place_id)
    if not place:
        raise ValueError("Unknown place")
    return _forecast_for(f"forecast:{district['id']}:{place['id']}", place, {"district": district, "place": place}, force)

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
    settled = end_d <= datetime.now(IST).date() - timedelta(days=HISTORY_SETTLED_AFTER_DAYS)
    cached = _cached(key, ttl=HISTORY_PAST_CACHE_TTL_SECONDS if settled else None)
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

def get_statewide_forecast(force=False):
    """7-day precipitation totals for every district from ONE multi-location upstream request.

    Open-Meteo accepts comma-separated coordinates and answers with a list in the same order,
    so the map can colour all 38 districts without 38 separate calls.
    """
    cached = _cached(STATEWIDE_CACHE_KEY)
    if cached and not force and not cached["stale"]:
        return {**cached["payload"], "cached": True, "stale": False, "retrieved_at": cached["fetched_at"]}
    params = {
        "latitude": ",".join(str(d["lat"]) for d in DISTRICTS),
        "longitude": ",".join(str(d["lon"]) for d in DISTRICTS),
        "daily": "precipitation_sum", "forecast_days": 7, "timezone": "Asia/Kolkata",
    }
    try:
        raw = _get_json(FORECAST_URL, params, expect_list=True)
        if len(raw) != len(DISTRICTS):
            # Without a one-to-one match we cannot safely attribute values to districts.
            raise ProviderError("Weather provider returned an unexpected number of locations")
        rows = []
        for district, item in zip(DISTRICTS, raw):
            daily = item.get("daily") if isinstance(item.get("daily"), dict) else {}
            sums = daily.get("precipitation_sum")
            values = [v for v in (sums if isinstance(sums, list) else []) if isinstance(v, (int, float)) and not isinstance(v, bool)]
            rows.append({
                "district_id": district["id"], "district": district["name"],
                "lat": district["lat"], "lon": district["lon"],
                # Missing values are unknown, never zero: no valid day means no total.
                "total_mm": round(sum(values), 1) if values else None,
                "max_daily_mm": round(max(values), 1) if values else None,
                "valid_days": len(values),
            })
        payload = {
            "source": "Open-Meteo Forecast API", "source_url": "https://open-meteo.com/en/docs",
            "districts": rows,
            "note": "7-day model forecast totals at representative district coordinates; not official district-wide forecasts or IMD warnings.",
            "fetched_live": True,
        }
        fetched_at = _save_cache(STATEWIDE_CACHE_KEY, payload)
        return {**payload, "cached": False, "stale": False, "retrieved_at": fetched_at}
    except ProviderError:
        if cached:
            return {**cached["payload"], "cached": True, "stale": True, "retrieved_at": cached["fetched_at"], "warning": "Provider unavailable; showing cached data."}
        raise

def get_district_places_forecast(district_id, force=False):
    """7-day precipitation totals for every place in a district from ONE multi-location request."""
    district = district_by_id(district_id)
    if not district:
        raise ValueError("Unknown district")
    places = places_for_district(district["id"]) or []
    if not places:
        raise ValueError("No places configured for this district")
    key = f"places:{district['id']}"
    cached = _cached(key)
    if cached and not force and not cached["stale"]:
        return {**cached["payload"], "cached": True, "stale": False, "retrieved_at": cached["fetched_at"]}
    params = {
        "latitude": ",".join(str(p["lat"]) for p in places),
        "longitude": ",".join(str(p["lon"]) for p in places),
        "daily": "precipitation_sum", "forecast_days": 7, "timezone": "Asia/Kolkata",
    }
    try:
        # A single location is answered with an object, several with a list: normalise to a list.
        raw = _get_json(FORECAST_URL, params, expect_list=len(places) > 1)
        if isinstance(raw, dict):
            raw = [raw]
        if len(raw) != len(places):
            # Without a one-to-one match we cannot safely attribute values to places.
            raise ProviderError("Weather provider returned an unexpected number of locations")
        rows = []
        for place, item in zip(places, raw):
            daily = item.get("daily") if isinstance(item.get("daily"), dict) else {}
            sums = daily.get("precipitation_sum")
            values = [v for v in (sums if isinstance(sums, list) else []) if isinstance(v, (int, float)) and not isinstance(v, bool)]
            rows.append({
                "place_id": place["id"], "place": place["name"], "lat": place["lat"], "lon": place["lon"],
                # Missing values are unknown, never zero: no valid day means no total.
                "total_mm": round(sum(values), 1) if values else None,
                "max_daily_mm": round(max(values), 1) if values else None,
                "valid_days": len(values),
            })
        payload = {
            "district": district, "source": "Open-Meteo Forecast API", "source_url": "https://open-meteo.com/en/docs",
            "places": rows,
            "note": "7-day model forecast totals at approximate town coordinates; not official forecasts, rain-gauge readings or IMD warnings.",
            "fetched_live": True,
        }
        fetched_at = _save_cache(key, payload)
        return {**payload, "cached": False, "stale": False, "retrieved_at": fetched_at}
    except ProviderError:
        if cached:
            return {**cached["payload"], "cached": True, "stale": True, "retrieved_at": cached["fetched_at"], "warning": "Provider unavailable; showing cached data."}
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
