import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from .weather import get_forecast, get_history, ProviderError

def ask_mistral(question, district_id=None, start=None, end=None):
    api_key = os.getenv("MISTRAL_API_KEY", "").strip()
    if not api_key:
        return {"available":False, "message":"Mistral AI is not configured. Set MISTRAL_API_KEY in the backend environment to enable evidence-grounded analysis."}
    evidence = []
    if district_id:
        try:
            forecast = get_forecast(district_id)
            evidence.append({"type":"provider_forecast","data":forecast})
        except (ValueError, ProviderError) as exc:
            evidence.append({"type":"forecast_unavailable","detail":str(exc)})
        if start and end:
            try:
                history = get_history(district_id, start, end)
                records = history.get("records", [])
                valid = [r["precipitation_mm"] for r in records if isinstance(r.get("precipitation_mm"), (int,float))]
                evidence.append({"type":"historical_reanalysis","source":history.get("source"),"count":len(records),"total_mm":round(sum(valid),2) if valid else None,"records":records[-60:]})
            except (ValueError, ProviderError) as exc:
                evidence.append({"type":"history_unavailable","detail":str(exc)})
    if not evidence:
        evidence.append({"type":"scope","detail":"No district was selected. Ask the user to select a district for location-specific evidence."})
    model = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
    body = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": 900,
        "messages": [
            {"role":"system","content":(
                "You are Mazhai AI, a careful rainfall data explainer for Tamil Nadu. "
                "Use only the supplied JSON evidence for factual claims. Never invent measurements, "
                "incidents, official warnings, citations, or probabilities. Explain that Open-Meteo "
                "forecast/reanalysis values are model/grid data at representative district coordinates, "
                "not official rain-gauge observations. Do not equate rainfall risk with flood prediction. "
                "If evidence is missing, say so. Distinguish source facts from interpretation. Keep the answer concise."
            )},
            {"role":"user","content":json.dumps({"question":question,"evidence":evidence}, ensure_ascii=False)}
        ]
    }
    req = Request("https://api.mistral.ai/v1/chat/completions", data=json.dumps(body).encode(), headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"})
    try:
        with urlopen(req, timeout=20) as response:
            result=json.loads(response.read().decode())
        answer=result["choices"][0]["message"]["content"]
        return {"available":True,"model":model,"answer":answer,"evidence_types":[e["type"] for e in evidence]}
    except (HTTPError, URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
        return {"available":False,"message":f"Mistral service is currently unavailable ({exc.__class__.__name__}). Weather and history features remain available."}
