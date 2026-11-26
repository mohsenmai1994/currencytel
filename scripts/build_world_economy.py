#!/usr/bin/env python3
"""CurrencyTel: generate GitHub-hosted economic data for the existing world UI.

Run on GitHub Actions. World Bank / Frankfurter are contacted ONLY here,
never by the website or mobile clients. No invented economic observations.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import pathlib
import random
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
COUNTRIES_FILE = ROOT / "assets/data/world-countries.json"
OUTPUT_FILE = ROOT / "data/world-economy.json"
INDICATORS = {
    "inflation": "FP.CPI.TOTL.ZG",
    "gdp": "NY.GDP.MKTP.CD",
    "growth": "NY.GDP.MKTP.KD.ZG",
    "population": "SP.POP.TOTL",
    "unemployment": "SL.UEM.TOTL.ZS",
}
USER_AGENT = "CurrencyTel-EconomyFeed/1.1 (+https://github.com/mohsenmai1994/currencytel)"


def get_json(url: str):
    """Retry transient network/API failures, fail rather than write fake values."""
    failures = []
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/json", "User-Agent": USER_AGENT,
            })
            with urllib.request.urlopen(req, timeout=40) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status}")
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, ValueError,
                OSError, RuntimeError) as exc:
            failures.append(str(exc))
            if attempt < 3:
                time.sleep((2 ** attempt) + random.random())
    raise RuntimeError(f"Failed to fetch {url}: {'; '.join(failures)}")


def countries_data():
    document = json.loads(COUNTRIES_FILE.read_text(encoding="utf-8"))
    countries = document.get("countries")
    if not isinstance(countries, list) or len(countries) < 100:
        raise ValueError("The countries data file is missing or incomplete")
    allowed = set()
    for item in countries:
        code = str(item.get("code", "")).upper()
        if len(code) == 2 and code.isalpha():
            allowed.add(code)
    if len(allowed) < 100:
        raise ValueError("Too few valid ISO-2 country codes")
    return allowed


def worldbank_rows(indicator):
    """Fetch ALL pages of latest non-null observations for the given metric."""
    base = f"https://api.worldbank.org/v2/country/all/indicator/{indicator}"
    page = 1
    rows = []
    while True:
        query = urllib.parse.urlencode({
            "format": "json", "per_page": "1000", "mrnev": "1", "page": str(page)
        })
        payload = get_json(f"{base}?{query}")
        if (not isinstance(payload, list) or len(payload) < 2
                or not isinstance(payload[0], dict)
                or not isinstance(payload[1], list)):
            raise ValueError(f"Unexpected World Bank response for {indicator}, page {page}")
        rows.extend(payload[1])
        pages = int(payload[0].get("pages", 1))
        if page >= pages:
            return rows
        if pages > 25:
            raise ValueError("Unexpectedly many World Bank API pages")
        page += 1


def gather_indicators(allowed):
    result = {code: {} for code in allowed}
    for key, indicator in INDICATORS.items():
        rows = worldbank_rows(indicator)
        for row in rows:
            if not isinstance(row, dict):
                continue
            code = str((row.get("country") or {}).get("id", "")).upper()
            value = row.get("value")
            year = str(row.get("date") or "")
            if (code not in allowed or isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    or not (len(year) == 4 and year.isdigit())):
                continue
            previous = result[code].get(key)
            if previous is None or year > previous["year"]:
                result[code][key] = {"value": value, "year": year}
        covered = sum(key in data for data in result.values())
        print(f"World Bank {key} ({indicator}): {covered}/{len(allowed)} countries")
        if covered < 25:
            raise RuntimeError(f"Incomplete World Bank {key} feed ({covered} countries)")
    return result


def gather_fx():
    # Frankfurter v2 returns an array of rows with base / quote / rate / date.
    payload = get_json("https://api.frankfurter.dev/v2/rates?base=USD")
    result = {}
    if isinstance(payload, list):
        for row in payload:
            if not isinstance(row, dict) or str(row.get("base", "")).upper() != "USD":
                continue
            code = str(row.get("quote", "")).upper()
            rate = row.get("rate")
            date = row.get("date")
            if (len(code) != 3 or not code.isalpha() or isinstance(rate, bool)
                    or not isinstance(rate, (int, float)) or not math.isfinite(rate)
                    or rate <= 0):
                continue
            if code not in result or str(date) > str(result[code].get("date")):
                result[code] = {"value": float(rate), "date": date}
    elif isinstance(payload, dict) and isinstance(payload.get("rates"), dict):
        date = payload.get("date")
        for code, rate in payload["rates"].items():
            if (len(code) == 3 and isinstance(rate, (int, float))
                    and not isinstance(rate, bool) and math.isfinite(rate) and rate > 0):
                result[code.upper()] = {"value": float(rate), "date": date}
    else:
        raise ValueError("Unrecognized Frankfurter v2 response")
    result["USD"] = {"value": 1.0, "date": dt.datetime.now(dt.timezone.utc).date().isoformat()}
    if len(result) < 20:
        raise RuntimeError(f"Incomplete Frankfurter feed ({len(result)} currencies)")
    print(f"Frankfurter: {len(result)} reference currencies")
    return result


def build_payload():
    allowed = countries_data()
    indicators = gather_indicators(allowed)
    fx = gather_fx()
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return {
        "schema_version": 1,
        "fetched_at": now,
        "sources": {"indicators": "World Bank", "reference_fx": "Frankfurter"},
        "indicators": dict(sorted(indicators.items())),
        "fx": dict(sorted(fx.items())),
    }


def main():
    document = build_payload()  # Do not overwrite the old data if any provider fails.
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT_FILE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT_FILE)
    print(f"Published {OUTPUT_FILE}: {len(document['indicators'])} country records; {len(document['fx'])} FX rates")


if __name__ == "__main__":
    main()
