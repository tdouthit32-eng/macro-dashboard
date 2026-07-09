"""Fetch the latest observation for each FRED series used by the dashboard and write data.json."""
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone

FRED_API_KEY = os.environ.get("FRED_API_KEY")
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

SERIES_IDS = [
    "T10Y2Y",
    "T10Y3M",
    "T10YIE",
    "T5YIFR",
    "DFII10",
    "BAMLH0A0HYM2",
    "BAMLC0A0CM",
    "M2SL",
    "DRCRELEXFACBS",
    "WRESBAL",
    "RRPONTSYD",
    "MORTGAGE30US",
    "HOUST",
    "CSUSHPINSA",
    "CREACBM027NBOG",
]


def fetch_latest(series_id, errors):
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1,
    }
    url = FRED_BASE + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            payload = json.load(resp)
    except Exception as exc:
        errors.append(f"{series_id}: request failed ({exc})")
        return None

    observations = payload.get("observations") or []
    if not observations:
        errors.append(f"{series_id}: no observations returned")
        return None

    obs = observations[0]
    if obs.get("value") == ".":
        errors.append(f"{series_id}: latest observation is missing ('.')")
        return None

    try:
        value = float(obs["value"])
    except (KeyError, ValueError):
        errors.append(f"{series_id}: could not parse value '{obs.get('value')}'")
        return None

    return {"value": value, "date": obs["date"]}


def main():
    if not FRED_API_KEY:
        print("FRED_API_KEY environment variable is not set", file=sys.stderr)
        sys.exit(1)

    errors = []
    series = {}
    for series_id in SERIES_IDS:
        result = fetch_latest(series_id, errors)
        if result is not None:
            series[series_id] = result

    derived = {}
    hy = series.get("BAMLH0A0HYM2")
    ig = series.get("BAMLC0A0CM")
    if hy is not None and ig is not None:
        derived["HY_IG_SPREAD_BP"] = {
            "value": round((hy["value"] - ig["value"]) * 100, 1),
            "formula": "(BAMLH0A0HYM2 - BAMLC0A0CM) * 100",
        }

    data = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "FRED (api.stlouisfed.org)",
        "series": series,
        "derived": derived,
        "errors": errors,
    }

    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    if errors:
        print("Completed with errors:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)

    if not series:
        print("No series were fetched successfully; aborting.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
