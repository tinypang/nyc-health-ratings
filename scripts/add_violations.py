#!/usr/bin/env python3
"""
One-shot script: patch the latest data file with violation flags
(rats / roaches / hygiene) without re-fetching the full restaurant dataset.

Run once after deploying the violation-filter feature to backfill flags
on an already-generated data file.  Future full runs of fetch_data.py
will include violation flags automatically.

Usage:
    python3 scripts/add_violations.py
"""
import json
import os
import ssl
from urllib.request import urlopen
from urllib.parse import urlencode

# macOS Python 3 ships without bundled CA certs; bypass verification for public API calls
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

API_BASE  = "https://data.cityofnewyork.us/resource/43nn-pn8j.json"
PAGE_SIZE = 50000

VIOLATION_MAP = {
    "04K": "rats",     # live rats
    "04L": "rats",     # live mice
    "04M": "roaches",  # live roaches
    "04N": "roaches",  # filth flies / food-associated flies
    "04B": "hygiene",  # preparing food while ill or injured
    "04D": "hygiene",  # inadequate handwashing
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MANIFEST = os.path.join(DATA_DIR, "manifest.json")


def fetch_violations():
    """
    Fetch all matching violation rows and return {camis: set_of_types},
    where each set reflects only citations from the restaurant's most
    recent inspection date.
    """
    codes_str = "','".join(VIOLATION_MAP.keys())
    violations = {}   # camis -> {"latest_date": str, "types": set}
    offset = 0
    while True:
        params = urlencode({
            "$limit":  PAGE_SIZE,
            "$offset": offset,
            "$where":  f"violation_code IN ('{codes_str}')",
            "$select": "camis,inspection_date,violation_code",
            "$order":  "camis,inspection_date DESC",
        })
        print(f"  fetching offset {offset}…", flush=True)
        with urlopen(f"{API_BASE}?{params}", timeout=60, context=_SSL_CTX) as r:
            page = json.loads(r.read())
        if not page:
            break
        for row in page:
            camis = row["camis"]
            idate = row.get("inspection_date", "")
            vtype = VIOLATION_MAP.get(row.get("violation_code", ""))
            if not vtype:
                continue
            if camis not in violations:
                violations[camis] = {"latest_date": idate, "types": set()}
            entry = violations[camis]
            if idate > entry["latest_date"]:
                entry["latest_date"] = idate
                entry["types"] = {vtype}
            elif idate == entry["latest_date"]:
                entry["types"].add(vtype)
        print(f"  {offset + len(page)} rows, {len(violations)} unique camis", flush=True)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return {camis: {"date": data["latest_date"], "types": data["types"]}
            for camis, data in violations.items()}


def main():
    with open(MANIFEST) as f:
        manifest = json.load(f)
    latest    = manifest["latest"]
    data_path = os.path.join(DATA_DIR, f"{latest}.json")

    print(f"Loading {data_path}…")
    with open(data_path) as f:
        records = json.load(f)
    print(f"  {len(records)} restaurants loaded")

    print("Fetching violation flags from NYC Open Data…")
    violations = fetch_violations()
    print(f"  flags found for {len(violations)} restaurants")

    for record in records:
        v = violations.get(record["camis"])
        # Only apply flags when the violation comes from the restaurant's current
        # inspection. An old pest citation must not carry forward to a later
        # clean inspection (date prefix comparison handles T00:00:00.000 suffix).
        if v and v["date"][:10] == (record.get("inspection_date") or "")[:10]:
            vtypes = v["types"]
        else:
            vtypes = set()
        record["rats"]    = "rats"    in vtypes
        record["roaches"] = "roaches" in vtypes
        record["hygiene"] = "hygiene" in vtypes

    with open(data_path, "w") as f:
        json.dump(records, f, separators=(",", ":"))
    print(f"Saved {data_path}")

    rats    = sum(1 for r in records if r["rats"])
    roaches = sum(1 for r in records if r["roaches"])
    hygiene = sum(1 for r in records if r["hygiene"])
    print(f"  Rats / Mice:                        {rats:,}")
    print(f"  Roaches / Flying Insects:            {roaches:,}")
    print(f"  Inadequate Hand Washing / Food Ill:  {hygiene:,}")


if __name__ == "__main__":
    main()
