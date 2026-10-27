import json
import logging
import math
import os
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from http.client import HTTPException as HTTPClientError
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from ..districts import DISTRICTS
from ..places import PLACES_BY_DISTRICT
from .weather import get_forecast, get_place_forecast, get_history, ProviderError

log = logging.getLogger("mazhai.ai")

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MAX_HISTORY_TURNS = 6
MAX_HISTORY_CHARS = 1800


def _extract_text(content):
    """Mistral may return a plain string or a list of content chunks."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for chunk in content:
            if isinstance(chunk, str):
                parts.append(chunk)
            elif isinstance(chunk, dict) and chunk.get("type", "text") == "text":
                text = chunk.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts).strip()
    return ""


def _clean_history(history):
    """Keep a small, total-bounded conversation window for reference resolution only."""
    cleaned = []
    budget = MAX_HISTORY_CHARS
    valid = []
    for turn in (history or [])[-MAX_HISTORY_TURNS:]:
        role = turn.get("role") if isinstance(turn, dict) else None
        content = turn.get("content") if isinstance(turn, dict) else None
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            valid.append({"role": role, "content": content.strip()})
    # Walk backwards so the newest turns win the total character budget, then restore chronology.
    for turn in reversed(valid):
        if budget <= 0:
            break
        content = turn["content"][-min(500, budget):]
        cleaned.append({"role": turn["role"], "content": content})
        budget -= len(content)
    return list(reversed(cleaned))


def _user_message(status, language="en"):
    english = {
        401: "Mistral rejected the API key. Check MISTRAL_API_KEY on the server.",
        403: "Mistral denied access for this key or model.",
        404: "Mistral does not recognise the configured model. Check MISTRAL_MODEL.",
        422: "Mistral rejected the request format.",
        429: "Mistral rate limit reached. Try again shortly.",
    }
    tamil = {
        401: "Mistral API விசை ஏற்கப்படவில்லை. சேவையகத்தில் MISTRAL_API_KEY அமைப்பைச் சரிபார்க்கவும்.",
        403: "இந்த API விசை அல்லது மாதிரிக்கு Mistral அனுமதி வழங்கவில்லை.",
        404: "அமைக்கப்பட்ட Mistral மாதிரி கிடைக்கவில்லை. MISTRAL_MODEL அமைப்பைச் சரிபார்க்கவும்.",
        422: "Mistral கோரிக்கை வடிவத்தை ஏற்கவில்லை.",
        429: "Mistral கோரிக்கை வரம்பை எட்டிவிட்டது. சிறிது நேரம் கழித்து முயற்சிக்கவும்.",
    }
    fallback = ("Mistral சேவையில் பிழை ஏற்பட்டது. வானிலை மற்றும் வரலாற்று அம்சங்கள் தொடர்ந்து கிடைக்கும்."
                if language == "ta" else
                "Mistral service returned an error. Weather and history features remain available.")
    return (tamil if language == "ta" else english).get(status, fallback)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _resolve_district(question, district_id, use_context=True):
    """Resolve English or Tamil district names, including common colloquial spellings."""
    text = str(question or "")
    unsupported_places = (
        "bengaluru", "bangalore", "hyderabad", "mumbai", "delhi", "new delhi",
        "kolkata", "pune", "kochi", "thiruvananthapuram", "kerala", "karnataka",
        "andhra pradesh", "telangana", "maharashtra", "pondicherry", "puducherry",
        "goa", "jaipur", "lucknow", "ahmedabad", "bhopal",
        "பெங்களூரு", "பெங்களூர்", "ஹைதராபாத்", "மும்பை", "டெல்லி", "புது டெல்லி",
        "கொல்கத்தா", "புனே", "கொச்சி", "திருவனந்தபுரம்", "கேரளா", "கர்நாடகா",
        "ஆந்திரப் பிரதேசம்", "தெலங்கானா", "மகாராஷ்டிரா", "புதுச்சேரி", "கோவா",
        "ஜெய்ப்பூர்", "லக்னோ", "அகமதாபாத்", "போபால்",
    )
    def candidates(name):
        values = [name]
        if any(ord(ch) > 127 for ch in name):
            if name.endswith("ம்"):
                stem = name[:-2]
                values.extend((stem + "த்தில்", stem + "த்துக்கு", stem + "த்தின்"))
            elif name.endswith(("ர்", "ல்", "ள்", "ன்")):
                stem = name[:-1]
                values.extend((stem + "ில்", stem + "ுக்கு", stem + "ின்"))
        return tuple(dict.fromkeys(values))

    def mentions(name):
        for candidate in candidates(name):
            if any(ord(ch) > 127 for ch in candidate):
                matched = re.search(re.escape(candidate), text, re.IGNORECASE)
            else:
                matched = re.search(r"(?<![\w])" + re.escape(candidate) + r"(?![\w])", text, re.IGNORECASE)
            if matched:
                return True
        return False

    if any(mentions(place) for place in unsupported_places):
        return None

    aliases = {
        "ariyalur": ("அரியலூர்",),
        "chengalpattu": ("செங்கல்பட்டு",),
        "chennai": ("சென்னை",),
        "coimbatore": ("கோயம்புத்தூர்", "கோவை"),
        "cuddalore": ("கடலூர்",),
        "dharmapuri": ("தர்மபுரி",),
        "dindigul": ("திண்டுக்கல்",),
        "erode": ("ஈரோடு",),
        "kallakurichi": ("கள்ளக்குறிச்சி",),
        "kanchipuram": ("காஞ்சிபுரம்",),
        "kanniyakumari": ("கன்னியாகுமரி",),
        "karur": ("கரூர்",),
        "krishnagiri": ("கிருஷ்ணகிரி",),
        "madurai": ("மதுரை",),
        "mayiladuthurai": ("மயிலாடுதுறை",),
        "nagapattinam": ("நாகப்பட்டினம்",),
        "namakkal": ("நாமக்கல்",),
        "nilgiris": ("நீலகிரி",),
        "perambalur": ("பெரம்பலூர்",),
        "pudukkottai": ("புதுக்கோட்டை",),
        "ramanathapuram": ("இராமநாதபுரம்", "ராமநாதபுரம்"),
        "ranipet": ("ராணிப்பேட்டை",),
        "salem": ("சேலம்",),
        "sivaganga": ("சிவகங்கை",),
        "tenkasi": ("தென்காசி",),
        "thanjavur": ("தஞ்சாவூர்",),
        "theni": ("தேனி",),
        "thoothukudi": ("தூத்துக்குடி", "tuticorin"),
        "tiruchirappalli": ("திருச்சிராப்பள்ளி", "திருச்சி", "trichy"),
        "tirunelveli": ("திருநெல்வேலி", "நெல்லை"),
        "tirupathur": ("திருப்பத்தூர்",),
        "tiruppur": ("திருப்பூர்",),
        "tiruvallur": ("திருவள்ளூர்",),
        "tiruvannamalai": ("திருவண்ணாமலை",),
        "tiruvarur": ("திருவாரூர்",),
        "vellore": ("வேலூர்",),
        "viluppuram": ("விழுப்புரம்", "villupuram"),
        "virudhunagar": ("விருதுநகர்",),
        "nilgiris": ("நீலகிரி", "the nilgiris",),
    }
    legacy_aliases = {
        "tiruchirappalli": ("trichy",),
        "thoothukudi": ("tuticorin",),
        "kanniyakumari": ("kanyakumari",),
        "kanchipuram": ("kancheepuram",),
        "the nilgiris": ("nilgiris",),
        "viluppuram": ("villupuram",),
    }
    for district in sorted(DISTRICTS, key=lambda item: len(item["name"]), reverse=True):
        names = (district["name"], district["id"], *legacy_aliases.get(district["id"], ()), *aliases.get(district["id"], ()))
        for name in names:
            if mentions(name):
                return district
    return next((item for item in DISTRICTS if item["id"] == str(district_id or "").strip().casefold()), None) if use_context else None


_UNSUPPORTED_LOCATION_NAMES = (
    "bengaluru", "bangalore", "hyderabad", "mumbai", "delhi", "new delhi", "kolkata",
    "pune", "kochi", "thiruvananthapuram", "kerala", "karnataka", "andhra pradesh",
    "telangana", "maharashtra", "pondicherry", "puducherry", "goa", "jaipur",
    "lucknow", "ahmedabad", "bhopal", "பெங்களூரு", "பெங்களூர்", "ஹைதராபாத்",
    "மும்பை", "டெல்லி", "புது டெல்லி", "கொல்கத்தா", "புனே", "கொச்சி",
    "திருவனந்தபுரம்", "கேரளா", "கர்நாடகா", "ஆந்திரப் பிரதேசம்", "தெலங்கானா",
    "மகாராஷ்டிரா", "புதுச்சேரி", "கோவா", "ஜெய்ப்பூர்", "லக்னோ", "அகமதாபாத்", "போபால்",
)
_LOCATION_STOP_WORDS = {
    "the", "a", "an", "next", "last", "coming", "this", "today", "tomorrow", "yesterday",
    "week", "month", "year", "days", "day", "period", "forecast", "weather", "rain",
    "rainfall", "probability", "chance", "mean", "means", "simple", "plain", "general",
    "terms", "context", "detail", "details", "me", "my", "our", "it", "there", "now",
}


def _classify_intent(question):
    """Cheap, deterministic routing; explanations and unrelated questions need no weather data."""
    text = re.sub(r"\s+", " ", str(question or "").casefold()).strip()
    definition_terms = ("rainfall probability", "precipitation probability", "probability of rain", "chance of rain")
    if any(term in text for term in definition_terms) and any(
        cue in text for cue in ("what does", "what is meant by", "meaning", "define", "explain", "mean?")
    ):
        return "explanation"
    if ("மழை வாய்ப்பு" in text or "மழை பெய்யும் வாய்ப்பு" in text) and ("என்றால் என்ன" in text or "விளக்க" in text):
        return "explanation"
    if any(term in text for term in ("compared to", "compare", "comparison", "versus", " vs ", "against last", "forecast and history")) or re.search(
        r"\\b(?:more|less|higher|lower|wetter|drier|different|similar)\\b.{0,40}\\b(?:last|past|previous|historical|history|week|month|year)\\b",
        text,
    ):
        return "comparison"
    if any(term in text for term in ("rainfall alert", "weather alert", "risk assessment", "rainfall assessment", "assess the rainfall", "flood risk", "should i worry", "பாதிப்பு மதிப்பீடு", "எச்சரிக்கை")):
        return "assessment"
    if any(term in text for term in (
        "historical", "history", "last week", "last month", "past week", "past month",
        "yesterday", "previous", "recorded", "rain fell", "rainfall over", "rainfall between",
        "how much rain did", "how much rain fell", "rainfall total", "வரலாற்று", "நேற்று",
        "கடந்த வாரம்", "கடந்த மாதம்", "மழைப்பொழிவு எவ்வளவு", "மழை பெய்தது",
    )):
        return "history"
    if any(term in text for term in (
        "forecast", "will it rain", "will rain", "chance of rain", "rain tomorrow",
        "rain today", "rain tonight", "weather tomorrow", "weather today", "tomorrow", "today", "tonight", "next 24",
        "next 48", "next few days", "rain probability", "precipitation", "umbrella",
        "மழை பெய்யுமா", "நாளை மழை", "இன்று மழை", "வானிலை", "முன்னறிவிப்பு",
    )):
        return "forecast"
    return "general"


def _is_rain_probability_definition(question):
    text = re.sub(r"\s+", " ", str(question or "").casefold()).strip()
    return (
        any(term in text for term in ("rainfall probability", "precipitation probability", "probability of rain", "chance of rain"))
        and any(cue in text for cue in ("what does", "meaning", "define", "explain", "mean?"))
    ) or (("மழை வாய்ப்பு" in text or "மழை பெய்யும் வாய்ப்பு" in text) and "என்றால் என்ன" in text)


def _explicit_location_name(question):
    """Return a likely explicitly requested location phrase, if present."""
    text = str(question or "")
    for name in _UNSUPPORTED_LOCATION_NAMES:
        pattern = re.escape(name)
        if not any(ord(ch) > 127 for ch in name):
            pattern = r"(?<![\w])" + pattern + r"(?![\w])"
        found = re.search(pattern, text, re.IGNORECASE)
        if found:
            return found.group(0)
    pattern = re.compile(
        r"\b(?:in|at|near|around|for|from)\s+([A-Za-z][A-Za-z.'’-]*(?:\s+[A-Za-z][A-Za-z.'’-]*){0,2})",
        re.IGNORECASE,
    )
    stop = _LOCATION_STOP_WORDS | {
        "is", "was", "were", "will", "would", "could", "should", "can", "do", "does",
        "did", "have", "has", "had", "rainy", "raining", "expected", "likely", "possible",
    }
    for match in pattern.finditer(text):
        words = match.group(1).split()
        useful = []
        for word in words:
            if word.casefold() in stop:
                break
            useful.append(word)
        if useful and useful[0].casefold() not in stop:
            candidate = " ".join(useful).strip(" .,'?-")
            if candidate and candidate.casefold() not in stop:
                return candidate
    # Also avoid falling back for common "Bengaluru weather" style prompts without a preposition.
    leading = re.match(
        r"\\s*([A-Za-z][A-Za-z.'’-]*)\\s+(?:weather|forecast|rainfall|rain)\\b",
        text,
        re.IGNORECASE,
    )
    if leading:
        return leading.group(1)
    return None


def _resolve_location(question, district_id=None):
    """Resolve a named district or supported town before considering dashboard context."""
    district = _resolve_district(question, None, use_context=False)
    if district:
        return {"status": "resolved", "kind": "district", "district": district, "place": None,
                "name": district["name"], "scope": "district reference-point forecast"}

    text = str(question or "")
    for unsupported in _UNSUPPORTED_LOCATION_NAMES:
        pattern = re.escape(unsupported)
        if not any(ord(ch) > 127 for ch in unsupported):
            pattern = r"(?<![\w])" + pattern + r"(?![\w])"
        found = re.search(pattern, text, re.IGNORECASE)
        if found:
            return {"status": "unsupported", "kind": "unknown", "name": found.group(0)}
    matches = []
    for owner_id, places in PLACES_BY_DISTRICT.items():
        for place in places:
            name = place.get("name", "")
            variants = {
                name,
                place.get("id", "").replace("-", " "),
                *re.findall(r"\(([^)]+)\)", name),
                re.sub(r"\s*\([^)]*\)", "", name).strip(),
            }
            for variant in variants - {""}:
                if any(ord(ch) > 127 for ch in variant):
                    found = re.search(re.escape(variant), text, re.IGNORECASE)
                else:
                    found = re.search(r"(?<![\w])" + re.escape(variant) + r"(?![\w])", text, re.IGNORECASE)
                if found:
                    matches.append((len(variant), variant, place, owner_id))
    if matches:
        longest = max(item[0] for item in matches)
        unique = {}
        for size, variant, place, owner_id in matches:
            if size == longest:
                unique[(owner_id, place["id"])] = (place, owner_id, variant)
        if len(unique) > 1:
            names = {entry[2].casefold() for entry in unique.values()}
            # Only ask for clarification when the same town label maps to different districts.
            if len(names) == 1:
                choices = sorted({next(d["name"] for d in DISTRICTS if d["id"] == owner_id)
                                  for _, owner_id, _ in unique.values()})
                return {"status": "ambiguous", "kind": "place", "name": next(iter(names)), "choices": choices}
        place, owner_id, _ = next(iter(unique.values()))
        owner = next((item for item in DISTRICTS if item["id"] == owner_id), None)
        return {"status": "resolved", "kind": "place", "district": owner, "place": place,
                "name": place["name"], "scope": "town-point model/grid forecast"}

    explicit = _explicit_location_name(text)
    if explicit:
        return {"status": "unsupported", "kind": "unknown", "name": explicit}
    district = _resolve_district(question, district_id, use_context=True)
    if district:
        return {"status": "resolved", "kind": "district", "district": district, "place": None,
                "name": district["name"], "scope": "district reference-point forecast"}
    return {"status": "missing", "kind": None, "district": None, "place": None, "name": None, "scope": None}


def _history_range(question, start, end, today):
    """Choose only the historical window the current request needs."""
    yesterday = today - timedelta(days=1)
    if start and end:
        history_start = date.fromisoformat(start)
        history_end = date.fromisoformat(end)
        if history_end >= today:
            history_end = yesterday
        if history_start > history_end:
            history_start = history_end
        return history_start.isoformat(), history_end.isoformat()
    text = str(question or "").casefold()
    if "yesterday" in text or "நேற்று" in text:
        history_start = history_end = yesterday
    else:
        match = re.search(r"(?:last|past|previous)\s+(\d{1,2})\s+days?", text)
        if match:
            days = max(1, min(30, int(match.group(1))))
        elif any(word in text for word in ("last month", "past month", "கடந்த மாதம்")):
            days = 30
        elif any(word in text for word in ("last week", "past week", "previous week", "கடந்த வாரம்")):
            days = 7
        else:
            days = 7
        history_end = yesterday
        history_start = history_end - timedelta(days=days - 1)
    return history_start.isoformat(), history_end.isoformat()


def _direct_answer(message, language, location=None, intent="general"):
    """Return a compatible concise response without paying for a model call."""
    return {
        "available": True, "language": language, "model": "deterministic",
        "answer": message, "location": location, "alert": None,
        "historical_context_available": False, "evidence_types": [], "intent": intent,
    }


def _summarize_forecast(forecast):
    """Create compact, explicit forecast evidence and preserve unknown values as unknown."""
    daily = forecast.get("daily") if isinstance(forecast.get("daily"), list) else []
    hourly = forecast.get("hourly") if isinstance(forecast.get("hourly"), list) else []
    daily_values = [(row.get("date"), row.get("precipitation_mm")) for row in daily
                    if isinstance(row, dict) and _is_number(row.get("precipitation_mm"))]
    hourly_window = [row for row in hourly[:48] if isinstance(row, dict)]
    hourly_values = [row.get("precipitation_mm") for row in hourly_window if _is_number(row.get("precipitation_mm"))]
    probability_values = [row.get("precipitation_probability_pct") for row in hourly_window
                          if _is_number(row.get("precipitation_probability_pct"))]
    if not probability_values:
        probability_values = [row.get("precipitation_probability_pct") for row in daily[:3]
                              if isinstance(row, dict) and _is_number(row.get("precipitation_probability_pct"))]
    max_daily = max(daily_values, key=lambda pair: pair[1]) if daily_values else (None, None)
    current = forecast.get("current") if isinstance(forecast.get("current"), dict) else {}
    hourly_total = round(sum(hourly_values), 1) if len(hourly_values) == len(hourly_window) and len(hourly_window) == 48 else None
    daily_valid_count = len(daily_values)
    return {
        "source": forecast.get("source"),
        "retrieved_at": forecast.get("retrieved_at"),
        "cached": bool(forecast.get("cached")),
        "stale": bool(forecast.get("stale")),
        "current": current,
        "forecast_days_returned": len(daily),
        "valid_daily_precipitation_values": daily_valid_count,
        "daily_forecast": daily,
        "next_48_hours": {
            "precipitation_mm": hourly_total,
            "hours_returned": len(hourly_window),
            "valid_precipitation_hours": len(hourly_values),
            "peak_precipitation_probability_pct": max(probability_values) if probability_values else None,
        },
        "maximum_daily_forecast": {
            "date": max_daily[0],
            "precipitation_mm": round(max_daily[1], 1) if max_daily[1] is not None else None,
        },
    }


def _summarize_history(history, requested_start, requested_end, today):
    """Summarize returned historical records without converting missing data to zero."""
    records = history.get("records") if isinstance(history.get("records"), list) else []
    valid = [(row.get("date"), row.get("precipitation_mm")) for row in records
             if isinstance(row, dict) and isinstance(row.get("date"), str)
             and _is_number(row.get("precipitation_mm"))]
    max_record = max(valid, key=lambda pair: pair[1]) if valid else (None, None)
    last_week_start = (today - timedelta(days=7)).isoformat()
    last_completed_day = (today - timedelta(days=1)).isoformat()
    last_week = [(day, value) for day, value in valid if last_week_start <= day <= last_completed_day]
    recent_max = max(last_week, key=lambda pair: pair[1]) if last_week else (None, None)
    return {
        "source": history.get("source"),
        "requested_range": {"start": requested_start, "end": requested_end},
        "records_returned": len(records),
        "valid_daily_values": len(valid),
        "missing_daily_values": max(0, len(records) - len(valid)),
        "total_precipitation_mm": round(sum(value for _, value in valid), 1) if valid else None,
        "mean_daily_precipitation_mm": round(sum(value for _, value in valid) / len(valid), 1) if valid else None,
        "days_at_least_1mm": sum(value >= 1 for _, value in valid),
        "days_at_least_20mm": sum(value >= 20 for _, value in valid),
        "maximum_daily_record": {"date": max_record[0], "precipitation_mm": round(max_record[1], 1) if max_record[1] is not None else None},
        "last_7_calendar_days_total_mm": round(sum(value for _, value in last_week), 1) if last_week else None,
        "last_7_calendar_days_max_daily_record": {"date": recent_max[0], "precipitation_mm": round(recent_max[1], 1) if recent_max[1] is not None else None},
        "stale": bool(history.get("stale")),
        "retrieved_at": history.get("retrieved_at"),
    }


def _build_rainfall_alert(forecast_summary, history_summary=None):
    """Transparent preliminary screening bands, not an official warning or calibrated risk score."""
    if not forecast_summary:
        return {
            "level": "Unable to assess",
            "rationale": "No usable forecast was retrieved for this location.",
            "basis": "Forecast data is unavailable; no safety conclusion can be drawn.",
            "is_official": False,
        }

    window = forecast_summary.get("next_48_hours") or {}
    rain_48h = window.get("precipitation_mm")
    peak_probability = window.get("peak_precipitation_probability_pct")
    max_day = forecast_summary.get("maximum_daily_forecast") or {}
    max_daily = max_day.get("precipitation_mm")
    has_amounts = _is_number(rain_48h) or _is_number(max_daily)
    if not has_amounts:
        return {
            "level": "Unable to assess",
            "rationale": "The forecast contained no usable precipitation amounts.",
            "basis": "Missing values are unknown, not zero.",
            "is_official": False,
            "forecast_stale": forecast_summary.get("stale", False),
        }

    daily_peak = max_daily if _is_number(max_daily) else 0
    window_peak = rain_48h if _is_number(rain_48h) else 0
    amount_peak = max(daily_peak, window_peak)
    valid_days = forecast_summary.get("valid_daily_precipitation_values", 0)
    returned_days = forecast_summary.get("forecast_days_returned", 0)
    if amount_peak >= 50:
        level = "High attention"
    elif amount_peak >= 25:
        level = "Elevated"
    elif amount_peak >= 10 or (_is_number(peak_probability) and peak_probability >= 60 and amount_peak >= 5):
        level = "Watch"
    else:
        level = "Routine"

    recent_total = history_summary.get("last_7_calendar_days_total_mm") if history_summary else None
    recent_max = (history_summary.get("last_7_calendar_days_max_daily_record") or {}).get("precipitation_mm") if history_summary else None
    recent_max_date = (history_summary.get("last_7_calendar_days_max_daily_record") or {}).get("date") if history_summary else None
    has_recent_heavy_rain = (_is_number(recent_total) and recent_total >= 50) or (_is_number(recent_max) and recent_max >= 20)
    upcoming_rain = (_is_number(rain_48h) and rain_48h >= 5) or (_is_number(max_daily) and max_daily >= 5)
    history_modifier = False
    if has_recent_heavy_rain and upcoming_rain and level == "Routine":
        level = "Watch"
        history_modifier = True
    elif has_recent_heavy_rain and upcoming_rain and level == "Watch":
        level = "Elevated"
        history_modifier = True

    # Don't label an incomplete forecast Routine just because only a few values arrived.
    if level == "Routine" and returned_days and valid_days < min(5, returned_days):
        level = "Unable to assess"

    # The daily peak must be explained from the Watch threshold (10 mm) upward; with a higher
    # cut-off a 10-25 mm day outside the 48-hour window produced "Watch" with a rationale
    # claiming the amounts were below the Watch threshold.
    if _is_number(max_daily) and max_daily == amount_peak and max_daily >= 10:
        rationale = f"The highest daily forecast is {max_daily:.1f} mm on {max_day.get('date') or 'an unspecified forecast date'}."
    elif _is_number(rain_48h) and rain_48h == amount_peak and rain_48h >= 10:
        rationale = f"The forecast indicates about {rain_48h:.1f} mm over the next 48 hours."
    elif _is_number(peak_probability) and peak_probability >= 60 and amount_peak >= 5:
        rationale = f"Rainfall probability peaks at {peak_probability:.0f}% and the available forecast indicates some rainfall."
    else:
        rationale = "The available forecast amounts are below the app's Watch threshold."
    if history_modifier:
        if _is_number(recent_total):
            rationale += f" Recent historical rainfall was {recent_total:.1f} mm across the last 7 calendar days."
        if _is_number(recent_max):
            rationale += f" The largest returned recent daily record was {recent_max:.1f} mm on {recent_max_date or 'an unspecified date'}."
        rationale += " Recent rainfall plus additional forecast rain raises the app's attention level; it does not prove saturated ground or flooding."
    elif history_summary and (has_recent_heavy_rain and not upcoming_rain):
        rationale += " Recent historical rainfall was high, but the currently available forecast does not indicate enough additional rain to trigger the app's historical-context adjustment."
    if forecast_summary.get("stale"):
        rationale += " The forecast is stale cached data, so refresh and verify current conditions."
    return {
        "level": level,
        "rationale": rationale,
        "basis": "Preliminary in-app rainfall screening only: High attention at 50 mm or more in a forecast day or 48-hour window; Elevated at 25 mm or more; Watch at 10 mm or more, or at least 60% rain probability with at least 5 mm indicated; Routine otherwise. One context step is added (Routine to Watch or Watch to Elevated) if recent historical rainfall was at least 50 mm over 7 days or at least 20 mm on a day and additional forecast rain of 5 mm or more is indicated. These bands are not official IMD categories, validated impact thresholds, or a flood-risk model.",
        "next_48h_mm": rain_48h if _is_number(rain_48h) else None,
        "peak_probability_pct": peak_probability if _is_number(peak_probability) else None,
        "max_daily_mm": max_daily if _is_number(max_daily) else None,
        "max_daily_date": max_day.get("date"),
        "recent_7_day_historical_total_mm": recent_total if _is_number(recent_total) else None,
        "recent_historical_max_daily_mm": recent_max if _is_number(recent_max) else None,
        "recent_historical_max_daily_date": recent_max_date,
        "historical_context_applied": history_modifier,
        "forecast_stale": bool(forecast_summary.get("stale")),
        "is_official": False,
    }


def _parse_json_object(raw):
    """Parse plain, fenced, double-encoded, or JSON embedded in extra prose."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    candidates = [text]
    unfenced = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text, flags=re.IGNORECASE).strip()
    if unfenced and unfenced not in candidates:
        candidates.append(unfenced)
    for item in list(candidates):
        first, last = item.find("{"), item.rfind("}")
        if first >= 0 and last > first:
            extracted = item[first:last + 1].strip()
            if extracted not in candidates:
                candidates.append(extracted)

    for candidate in candidates:
        attempts = [candidate]
        repaired = _repair_unescaped_json_quotes(candidate)
        if repaired != candidate:
            attempts.append(repaired)
        for attempt in list(attempts):
            trailing_comma_fixed = re.sub(r",\s*([}\]])", r"\1", attempt)
            if trailing_comma_fixed not in attempts:
                attempts.append(trailing_comma_fixed)
        for attempt in attempts:
            for strict in (True, False):
                try:
                    parsed = json.loads(attempt, strict=strict)
                except (TypeError, json.JSONDecodeError):
                    continue
                if isinstance(parsed, str):
                    try:
                        parsed = json.loads(parsed.strip(), strict=False)
                    except (TypeError, json.JSONDecodeError):
                        continue
                if isinstance(parsed, dict):
                    return parsed

    # A response can be truncated at the token limit or contain malformed quoting.
    # Recover any complete schema fields rather than discarding an otherwise useful answer.
    salvaged = _salvage_structured_json(text)
    if salvaged:
        salvaged["_parse_error"] = True
    return salvaged


def _repair_unescaped_json_quotes(candidate):
    """Escape embedded prose quotes while preserving actual JSON delimiters."""
    output = []
    in_string = False
    escaped = False
    index = 0
    while index < len(candidate):
        char = candidate[index]
        if not in_string:
            output.append(char)
            if char == '"':
                in_string = True
            index += 1
            continue
        if escaped:
            output.append(char)
            escaped = False
            index += 1
            continue
        if char == "\\":
            output.append(char)
            escaped = True
            index += 1
            continue
        if char == '"':
            look = index + 1
            while look < len(candidate) and candidate[look].isspace():
                look += 1
            following = candidate[look] if look < len(candidate) else ""
            closes_string = following in ("", "}", "]", ":")
            if following == ",":
                after_comma = look + 1
                while after_comma < len(candidate) and candidate[after_comma].isspace():
                    after_comma += 1
                next_value = candidate[after_comma] if after_comma < len(candidate) else ""
                closes_string = next_value in ('"', "{", "[", "}", "]") or not next_value
            output.append(char if closes_string else '\\"')
            if closes_string:
                in_string = False
            index += 1
            continue
        output.append(char)
        index += 1
    return "".join(output)


def _decode_salvaged_json_string(value):
    """Decode a recovered JSON string, repairing embedded quotes if possible."""
    value = value.strip()
    try:
        return json.loads('"' + value + '"')
    except (TypeError, json.JSONDecodeError):
        wrapped = '{"value":"' + value + '"}'
        repaired = _repair_unescaped_json_quotes(wrapped)
        try:
            return json.loads(repaired).get("value", value)
        except (TypeError, json.JSONDecodeError):
            return value.replace('\\"', '"').replace("\\n", " ").replace("\\r", " ")


def _salvage_json_array(value):
    """Recover complete string elements from a partly malformed/truncated JSON array."""
    value = value.strip()
    if not value.startswith("["):
        return []
    value = value[1:]
    items = []
    index = 0
    while index < len(value) and len(items) < 6:
        while index < len(value) and (value[index].isspace() or value[index] == ","):
            index += 1
        if index >= len(value) or value[index] == "]":
            break
        if value[index] != '"':
            # Stop rather than guessing at an unquoted item or nested object.
            break
        index += 1
        chars = []
        escaped = False
        while index < len(value):
            char = value[index]
            if escaped:
                # Keep the escape sequence intact so _decode_salvaged_json_string can decode it.
                chars.append("\\" + char)
                escaped = False
                index += 1
                continue
            if char == "\\":
                escaped = True
                index += 1
                continue
            if char == '"':
                look = index + 1
                while look < len(value) and value[look].isspace():
                    look += 1
                following = value[look] if look < len(value) else ""
                closes_item = following in ("", "]", "}")
                if following == ",":
                    after_comma = look + 1
                    while after_comma < len(value) and value[after_comma].isspace():
                        after_comma += 1
                    closes_item = after_comma >= len(value) or value[after_comma] in ('"', "]", "}")
                if closes_item:
                    index += 1
                    break
                chars.append(char)
                index += 1
                continue
            chars.append(char)
            index += 1
        item = _decode_salvaged_json_string("".join(chars)).strip()
        if item:
            items.append(item)
        # Continue at the current cursor; it is either after an item quote or at end.
    return items


def _salvage_structured_json(raw):
    """Recover fields from JSON-like output even when the full object will not parse."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    keys = (
        "current_conditions_and_forecast",
        "historical_context",
        "what_to_watch_next",
        "recommended_actions",
        "confidence_and_limitations",
    )
    key_pattern = re.compile(r"""["']?(""" + "|".join(re.escape(key) for key in keys) + r""")["']?\s*:""")
    matches = list(key_pattern.finditer(raw))
    if not matches:
        return None

    recovered = {}
    array_keys = {"what_to_watch_next", "recommended_actions"}
    for i, match in enumerate(matches):
        key = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        segment = raw[start:end].strip()
        if i + 1 < len(matches):
            segment = re.sub(r",\s*$", "", segment).strip()
        else:
            # Remove the outer object brace, not a brace inside quoted prose.
            segment = re.sub(r"}\s*$", "", segment).strip()

        if key in array_keys:
            values = _salvage_json_array(segment)
            if values:
                recovered[key] = values
            continue

        if not segment:
            continue
        # Trim the delimiter around a scalar string. The quote repair helper
        # escapes quotes inside the field while preserving its outer delimiter.
        if segment.startswith('"'):
            segment = segment[1:]
        segment = re.sub(r",\s*$", "", segment).strip()
        if segment.endswith('"'):
            segment = segment[:-1]
        segment = segment.strip()
        if segment:
            recovered[key] = _decode_salvaged_json_string(segment)

    return recovered if recovered else None


def _normalize_structured_answer(raw):
    """Validate model JSON, recover fields, and flag output that needs a format retry."""
    parsed = _parse_json_object(raw)
    parse_error = False
    if isinstance(parsed, dict):
        parse_error = bool(parsed.pop("_parse_error", False))
    else:
        looks_structured = isinstance(raw, str) and (
            raw.lstrip().startswith("{")
            or "current_conditions_and_forecast" in raw
            or "recommended_actions" in raw
        )
        if not looks_structured:
            return None
        parse_error = True
        parsed = {
            "current_conditions_and_forecast": "The AI response could not be formatted into the expected sections. Please retry your question.",
            "historical_context": "This response could not be parsed, so no historical comparison is displayed.",
            "what_to_watch_next": ["Retry the question to request a fresh structured response."],
            "recommended_actions": ["For safety decisions, check current official IMD and local authority advisories."],
            "confidence_and_limitations": "The generated response format was invalid. No new measurements or warnings have been inferred.",
        }

    def clean_text(value, fallback):
        if isinstance(value, str) and value.strip():
            return value.strip()[:1800]
        return fallback

    def clean_list(value, fallback):
        if not isinstance(value, list):
            return fallback
        items = [item.strip()[:500] for item in value if isinstance(item, str) and item.strip()]
        return items[:6] or fallback

    return {
        "_parse_error": parse_error,
        "current_conditions_and_forecast": clean_text(parsed.get("current_conditions_and_forecast"), "The model did not provide a current forecast summary."),
        "historical_context": clean_text(parsed.get("historical_context"), "Historical rainfall context is unavailable or was not returned."),
        "what_to_watch_next": clean_list(parsed.get("what_to_watch_next"), ["Check updated forecast data and official weather bulletins."]),
        "recommended_actions": clean_list(parsed.get("recommended_actions"), ["Use local conditions and official authority guidance when deciding what to do."]),
        "confidence_and_limitations": clean_text(parsed.get("confidence_and_limitations"), "This is a preliminary model-data explanation, not an official warning."),
    }


def _structured_answer_markdown(answer):
    """Keep a readable text transcript for chat history, APIs, and non-rich clients."""
    sections = [
        ("## Current conditions and forecast", answer["current_conditions_and_forecast"]),
        ("## Historical context", answer["historical_context"]),
        ("## What to watch next", "\n".join(f"- {item}" for item in answer["what_to_watch_next"])),
        ("## Recommended actions", "\n".join(f"- {item}" for item in answer["recommended_actions"])),
        ("## Confidence and limitations", answer["confidence_and_limitations"]),
    ]
    return "\n\n".join(f"{heading}\n{body}" for heading, body in sections)



def _answer_language_mismatch(answer, language):
    """Check each user-facing value, allowing numbers, acronyms, and proper names."""
    if isinstance(answer, dict):
        values = []
        for value in answer.values():
            if isinstance(value, str):
                values.append(value)
            elif isinstance(value, list):
                values.extend(item for item in value if isinstance(item, str))
    elif isinstance(answer, str):
        values = [answer]
    else:
        return True

    checked = 0
    all_letters = []
    for value in values:
        letters = [char for char in value if char.isalpha()]
        all_letters.extend(letters)
        if len(letters) < 5:
            # Very short labels/acronyms are not meaningful language samples.
            continue
        checked += 1
        tamil = sum(0x0B80 <= ord(char) <= 0x0BFF for char in letters)
        ratio = tamil / len(letters)
        if language == "ta":
            # Each prose field/list item should be Tamil, not merely one Tamil sentence in an English answer.
            if tamil < 5 or ratio < 0.15:
                return True
        elif tamil >= 5 and ratio >= 0.20:
            return True
    if checked == 0:
        tamil_all = sum(0x0B80 <= ord(char) <= 0x0BFF for char in all_letters)
        # Tiny but clearly wrong-language text such as "ok" should still trigger a Tamil retry.
        return tamil_all < len(all_letters) if language == "ta" else tamil_all > 0
    return False




def _language_fallback(language):
    """Localized, safe response when the model cannot obey the selected language."""
    if language == "ta":
        return {
            "current_conditions_and_forecast": "மன்னிக்கவும், தேர்ந்தெடுத்த மொழியில் நம்பகமான பதிலை உருவாக்க முடியவில்லை. தயவுசெய்து மீண்டும் முயற்சிக்கவும்.",
            "historical_context": "இந்த முயற்சியில் வரலாற்று மழைப்பொழிவுடன் ஒப்பீடு வழங்கப்படவில்லை.",
            "what_to_watch_next": ["கேள்வியை மீண்டும் அனுப்பி முயற்சிக்கவும்.", "அதிகாரப்பூர்வ வானிலை எச்சரிக்கைகளைச் சரிபார்க்கவும்."],
            "recommended_actions": ["பாதுகாப்பு முடிவுகளுக்கு அதிகாரப்பூர்வ IMD மற்றும் உள்ளூர் நிர்வாக அறிவுறுத்தல்களைப் பின்பற்றவும்."],
            "confidence_and_limitations": "இந்த பதில் மொழிச் சரிபார்ப்பைத் தாண்டவில்லை; புதிய வானிலை அளவீடோ எச்சரிக்கையோ ஊகிக்கப்படவில்லை.",
        }
    return {
        "current_conditions_and_forecast": "Sorry, I could not produce a reliable answer in the selected language. Please try again.",
        "historical_context": "A historical rainfall comparison was not produced for this attempt.",
        "what_to_watch_next": ["Ask the question again to request a fresh response.", "Check official weather bulletins."],
        "recommended_actions": ["Follow official IMD and local-authority guidance for safety decisions."],
        "confidence_and_limitations": "The response did not pass the language check; no new weather measurements or warnings have been inferred.",
    }


def _format_retry_instruction(language):
    """Ask Mistral to repair JSON structure without changing evidence or the selected language."""
    language_rule = (
        "Write all user-facing values in natural Tamil; keep JSON keys in English."
        if language == "ta" else
        "Write all user-facing values in clear English; keep JSON keys in English."
    )
    return (
        "FORMAT CHECK FAILED: Your previous response was invalid, truncated, or could not be parsed as the required JSON. "
        "Rewrite it as one complete, valid JSON object with exactly the five required fields: "
        "current_conditions_and_forecast (string), historical_context (string), what_to_watch_next (array of strings), "
        "recommended_actions (array of strings), confidence_and_limitations (string). "
        "Use only facts from the evidence. Do not include Markdown fences, preamble, trailing commentary, raw newlines "
        "inside JSON strings, or unescaped quotation marks. Keep all text concise so the object is complete. "
        + language_rule
    )


def _language_retry_instruction(language):
    if language == "ta":
        return (
            "LANGUAGE CHECK FAILED: Your previous answer was not written in the user's selected language. "
            "Rewrite the complete answer in natural, clear Tamil (தமிழ்). Every user-facing JSON value must be Tamil. "
            "The question and prior turns may be English; that must not change the selected Tamil response language. "
            "Keep only the required JSON key names in English. Preserve the supplied numeric evidence exactly; "
            "do not add facts. Return only the required valid JSON object."
        )
    return (
        "LANGUAGE CHECK FAILED: Your previous answer was not written in the user's selected language. "
        "Rewrite the complete answer in clear English. Every user-facing JSON value must be English. "
        "Keep the required JSON key names in English. Preserve supplied numeric evidence exactly; "
        "do not add facts. Return only the required valid JSON object."
    )

def _build_system_prompt(now_ist, language="en"):
    """Compact language-locked evidence contract for weather answers."""
    language_instruction = (
        "LANGUAGE LOCK: The selected response language is TAMIL (தமிழ்). Keep all user-facing JSON values in natural Tamil. "
        "Keep field names in English"
        if language == "ta" else
        "LANGUAGE LOCK: The selected response language is ENGLISH. Keep all user-facing JSON values in English."
    )
    return (
        language_instruction + ". "
        f"Today is {now_ist:%A, %d %B %Y} in India Standard Time (IST). "
        "Mazhai AI explains Tamil Nadu weather using only supplied evidence. The latest user message determines the task. "
        "Use chat history only to understand conversational context, resolve follow-ups, and identify references. "
        "Never treat a previous assistant answer as evidence. Do not repeat a full general report when the user asks a narrow follow-up. "
        "Use only the current evidence JSON. Never invent rainfall measurements, observations, incidents, official warnings, "
        "citations, river levels, closures, flooding, or actions by authorities. District reference-point data cannot establish a specific ward, "
        "street, neighbourhood, river catchment, or home condition. Forecasts are estimates; historical records are reanalysis, not rain-gauge observations. "
        "Keep missing values unknown, distinguish forecast from history, and label stale evidence. Never call the app's screening indicator an official warning or flood-risk score. "
        "If requested location evidence is absent, state that and do not substitute another location. Do not imply town-level historical observations when only district history is supplied. "
        "Compare only matching time ranges and never claim that probability guarantees rain or that no forecasted rain means an area is safe. "
        "For narrow follow-ups use concise, direct sections and do not restate every number. "
        "Return exactly one valid JSON object with exactly these keys/types: "
        '{"current_conditions_and_forecast": string, "historical_context": string, '
        '"what_to_watch_next": array of 2-4 strings, "recommended_actions": array of 2-4 strings, '
        '"confidence_and_limitations": string}. '
        "Keep simple answers brief; use a full report only when requested or genuinely needed. "
        "Say what evidence supports a conclusion and its main uncertainty, and do not restate every number. "
        "Escape JSON strings correctly and return no Markdown fences or extra keys."
    )

def ask_mistral(question, district_id=None, start=None, end=None, history=None, language="en"):
    language = "ta" if language == "ta" else "en"
    now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
    intent = _classify_intent(question)

    if _is_rain_probability_definition(question):
        message = (
            "மழை நிகழ்தகவு 60% என்பது, குறிப்பிட்ட இடம் மற்றும் நேரத்திற்கான முன்னறிவிப்பு மாதிரி மழை பெய்யும் வாய்ப்பை மதிப்பிடுகிறது என்பதாகும். "
            "அது 60% நேரம் மழை பெய்யும் அல்லது 60% மழை அளவு கிடைக்கும் என்று பொருளல்ல; இது உறுதி அல்ல."
            if language == "ta" else
            "A 60% rainfall probability means the forecast model estimates a 60% chance of measurable rain for the specified place and time. "
            "It does not mean rain will fall for 60% of the time or that 60% of a rainfall amount is guaranteed; it is not a certainty."
        )
        return _direct_answer(message, language, intent="explanation")

    weather_intent = intent in ("forecast", "history", "assessment", "comparison")
    location = _resolve_location(question, None) if weather_intent else {
        "status": "missing", "kind": None, "district": None, "place": None, "name": None, "scope": None
    }
    # Short follow-ups inherit the most recent explicit user location, never an assistant's prior answer.
    is_follow_up = bool(re.match(r"\s*(?:and\b|what about\b|how about\b|there\b|same place\b|tomorrow\b|also\b|அங்கு|அங்கே|அதே இடம்)", str(question or ""), re.IGNORECASE))
    if weather_intent and location["status"] == "missing" and is_follow_up:
        for turn in reversed((history or [])[-8:]):
            if not isinstance(turn, dict) or turn.get("role") != "user" or not isinstance(turn.get("content"), str):
                continue
            previous_location = _resolve_location(turn["content"], None)
            if previous_location["status"] in ("resolved", "unsupported", "ambiguous"):
                location = previous_location
                break
    if weather_intent and location["status"] == "missing":
        location = _resolve_location(question, district_id)
    if location["status"] in ("unsupported", "ambiguous"):
        if location["status"] == "ambiguous":
            name = location.get("name") or "that town"
            choices = location.get("choices") or []
            places_text = ", ".join(choices)
            message = (
                f"“{name}” என்ற இடம் ஒன்றுக்கு மேல் பொருள் தருகிறது. எந்த மாவட்டத்தில் உள்ள இடம் என்று குறிப்பிடவும்: {places_text}."
                if language == "ta" else
                f"I found more than one supported place named {name}. Which district do you mean: {places_text}?"
            )
        else:
            name = location.get("name") or "that location"
            message = (
                f"{name} தற்போது Mazhai AI-யின் ஆதரிக்கப்படும் தமிழ்நாடு மாவட்ட/நகரத் தரவுக்குள் இல்லை. "
                "தேர்ந்தெடுத்த மாவட்டத்தின் வானிலையை மாற்றாகக் காட்டவில்லை. ஆதரிக்கப்படும் தமிழ்நாடு மாவட்டம் அல்லது பட்டியலிலுள்ள நகரத்தைத் தேர்ந்தெடுக்கவும்."
                if language == "ta" else
                f"{name} is outside Mazhai AI's supported Tamil Nadu district/town coverage. I have not substituted the selected dashboard district. "
                "Choose a supported Tamil Nadu district or a town listed in the app."
            )
        return _direct_answer(message, language, intent=intent)

    api_key = os.getenv("MISTRAL_API_KEY", "").strip()
    if not api_key:
        message = ("Mistral AI அமைக்கப்படவில்லை. ஆதார அடிப்படையிலான பகுப்பாய்வை இயக்க backend சூழலில் MISTRAL_API_KEY அமைக்கவும்."
                   if language == "ta" else
                   "Mistral AI is not configured. Set MISTRAL_API_KEY in the backend environment to enable evidence-grounded analysis.")
        return {"available": False, "language": language, "message": message}

    chosen_district = location.get("district")
    chosen_place = location.get("place") if location.get("kind") == "place" else None
    location_name = location.get("name") if location.get("status") == "resolved" else None
    history_needed = intent in ("history", "assessment", "comparison")
    forecast_needed = intent in ("forecast", "assessment", "comparison")
    evidence = []
    forecast_summary = None
    history_summary = None
    alert_history_summary = None
    requested_range = None

    # Resolve location/intent before any evidence request. General questions never hit weather providers.
    if location.get("status") == "resolved" and chosen_district and forecast_needed:
        try:
            if chosen_place:
                forecast = get_place_forecast(chosen_district["id"], chosen_place["id"])
                forecast_type = "place_forecast_summary"
            else:
                forecast = get_forecast(chosen_district["id"])
                forecast_type = "provider_forecast_summary"
            forecast_summary = _summarize_forecast(forecast)
            evidence.append({
                "type": forecast_type, "location": location_name,
                "scope": "town-point forecast estimate" if chosen_place else "district reference-point forecast estimate",
                "data": forecast_summary,
            })
        except (ValueError, ProviderError) as exc:
            evidence.append({"type": "forecast_unavailable", "location": location_name, "detail": str(exc)})

    if location.get("status") == "resolved" and chosen_district and history_needed:
        range_start, range_end = _history_range(question, start, end, now_ist.date())
        requested_range = {"start": range_start, "end": range_end}
        try:
            hist = get_history(chosen_district["id"], range_start, range_end)
            history_summary = _summarize_history(hist, range_start, range_end, now_ist.date())
            scope = (
                f"{chosen_district['name']} district-level historical reanalysis; town-specific observations for {location_name} are unavailable"
                if chosen_place else "district reference-point historical reanalysis"
            )
            evidence.append({
                "type": "historical_rainfall_summary", "location": chosen_district["name"],
                "scope": scope, "data": history_summary,
            })
            alert_history_summary = history_summary
        except (ValueError, ProviderError) as exc:
            evidence.append({"type": "history_unavailable", "location": chosen_district["name"], "detail": str(exc)})

    alert = None
    if forecast_summary and intent in ("assessment", "comparison"):
        alert = _build_rainfall_alert(forecast_summary, alert_history_summary)
        evidence.append({"type": "app_generated_rainfall_attention", "data": alert})

    model = os.getenv("MISTRAL_MODEL", "ministral-8b-2512").strip() or "ministral-8b-2512"
    location_payload = None
    if location.get("status") == "resolved":
        location_payload = {
            "name": location_name, "kind": location.get("kind"),
            "district": chosen_district["name"] if chosen_district else None,
            "scope": location.get("scope"),
        }
    full_report = bool(re.search(r"\b(full|complete|comprehensive|detailed)\s+(report|analysis|assessment)\b", str(question), re.IGNORECASE))
    answer_style = "full_report" if full_report or intent in ("assessment", "comparison") else "concise"
    system = _build_system_prompt(now_ist, language)
    messages = [{"role": "system", "content": system}]
    messages += _clean_history(history)
    messages.append({"role": "user", "content": json.dumps({
        "question": question,
        "intent": intent,
        "answer_style": answer_style,
        "resolved_location": location_payload,
        "historical_range": requested_range,
        "evidence": evidence,
    }, ensure_ascii=False)})

    max_tokens = 1400 if answer_style == "full_report" else 700
    body = {"model": model, "temperature": 0.2, "max_tokens": max_tokens, "response_format": {"type": "json_object"}, "messages": messages}
    try:
        def call_model(messages_to_send):
            request_body = {**body, "messages": messages_to_send}
            request = Request(
                MISTRAL_URL,
                data=json.dumps(request_body, ensure_ascii=False).encode(),
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            )
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode())
            return _extract_text(payload["choices"][0]["message"]["content"])

        raw_answer = call_model(messages)
        if not raw_answer:
            log.warning("Mistral returned an empty answer (model=%s)", model)
            message = ("Mistral பதில் வழங்கவில்லை. உங்கள் கேள்வியை வேறு விதமாகக் கேட்டு மீண்டும் முயற்சிக்கவும்."
                       if language == "ta" else
                       "Mistral returned an empty answer. Please try rephrasing your question.")
            return {"available": False, "language": language, "message": message}

        structured_answer = _normalize_structured_answer(raw_answer)
        format_retry_used = False
        if structured_answer is not None:
            format_retry_used = bool(structured_answer.pop("_parse_error", False))
        answer_candidate = structured_answer if structured_answer is not None else raw_answer
        language_retry_used = _answer_language_mismatch(answer_candidate, language)

        if format_retry_used or language_retry_used:
            retry_parts = []
            if format_retry_used:
                retry_parts.append(_format_retry_instruction(language))
            if language_retry_used:
                retry_parts.append(_language_retry_instruction(language))
            retry_messages = messages + [
                {"role": "assistant", "content": raw_answer[:1500]},
                {"role": "user", "content": "\n\n".join(retry_parts)},
            ]
            try:
                retry_answer = call_model(retry_messages)
                retry_structured = _normalize_structured_answer(retry_answer) if retry_answer else None
                retry_format_error = bool(retry_structured.pop("_parse_error", False)) if retry_structured is not None else True
            except (HTTPError, URLError, OSError, HTTPClientError, KeyError, IndexError, TypeError, ValueError) as retry_exc:
                log.warning("Mistral format/language retry failed: %r", retry_exc)
                retry_answer, retry_structured, retry_format_error = "", None, True

            retry_candidate = retry_structured if retry_structured is not None else retry_answer
            if (
                retry_answer
                and retry_structured is not None
                and not retry_format_error
                and not _answer_language_mismatch(retry_candidate, language)
            ):
                raw_answer = retry_answer
                structured_answer = retry_structured
            elif language_retry_used:
                structured_answer = _language_fallback(language)
            elif structured_answer is None or format_retry_used:
                if structured_answer is None or not any(
                    structured_answer.get(key)
                    for key in ("current_conditions_and_forecast", "historical_context", "what_to_watch_next", "recommended_actions")
                ):
                    structured_answer = _language_fallback(language)

        if structured_answer is not None:
            answer = _structured_answer_markdown(structured_answer)
        else:
            answer = raw_answer
        response = {
            "available": True,
            "language": language,
            "model": model,
            "answer": answer,
            "location": location_name,
            "location_scope": location.get("scope") if location.get("status") == "resolved" else None,
            "intent": intent,
            "alert": alert,
            "historical_context_available": bool(history_summary and history_summary.get("valid_daily_values", 0) > 0),
            "evidence_types": [item["type"] for item in evidence],
            "language_retry_used": language_retry_used,
            "format_retry_used": format_retry_used,
        }
        if structured_answer is not None:
            response["structured_answer"] = structured_answer
        return response
    except HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        log.error("Mistral HTTP %s (model=%s): %s", exc.code, model, detail)
        return {"available": False, "language": language, "message": _user_message(exc.code, language)}
    except (URLError, OSError, HTTPClientError) as exc:
        log.error("Mistral network error: %s", exc)
        message = ("Mistral சேவையை அணுக முடியவில்லை. வானிலை மற்றும் வரலாற்று அம்சங்கள் தொடர்ந்து கிடைக்கும்."
                   if language == "ta" else
                   "Could not reach Mistral (network or timeout). Weather and history features remain available.")
        return {"available": False, "language": language, "message": message}
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        log.error("Unexpected Mistral response: %r", exc)
        message = ("Mistral எதிர்பாராத பதிலை வழங்கியது. வானிலை மற்றும் வரலாற்று அம்சங்கள் தொடர்ந்து கிடைக்கும்."
                   if language == "ta" else
                   "Mistral returned an unexpected response. Weather and history features remain available.")
        return {"available": False, "language": language, "message": message}

