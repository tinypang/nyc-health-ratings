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

from violations import VIOLATION_MAP, aggregate_violations, apply_flags

# macOS Python 3 ships without bundled CA certs; bypass verification for public API calls
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

API_BASE  = "https://data.cityofnewyork.us/resource/43nn-pn8j.json"
PAGE_SIZE = 50000

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MANIFEST = os.path.join(DATA_DIR, "manifest.json")


def fetch_latest_inspection_dates():
    """
    For each camis, return its most recent inspection_date across ALL
    inspections (graded or not). Uses Socrata's GROUP BY to keep this cheap.

    Why this matters: fetch_all() only returns the latest *graded* row per
    restaurant, but a more recent ungraded re-inspection can supersede an
    older pest citation. We must check against the true latest inspection.
    """
    latest = {}
    offset = 0
    while True:
        params = urlencode({
            "$limit":  PAGE_SIZE,
            "$offset": offset,
            # 1900-01-01 sentinel rows mean "no inspection conducted" — skip
            "$where":  "inspection_date > '1901-01-01'",
            "$select": "camis,max(inspection_date) AS latest",
            "$group":  "camis",
            "$order":  "camis",
        })
        print(f"  latest-date offset {offset}…", flush=True)
        with urlopen(f"{API_BASE}?{params}", timeout=60, context=_SSL_CTX) as r:
            page = json.loads(r.read())
        if not page:
            break
        for row in page:
            latest[row["camis"]] = row["latest"]
        print(f"  {offset + len(page)} rows, {len(latest)} camis", flush=True)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return latest


def fetch_violations(latest_dates):
    """
    Fetch all matching violation rows, then delegate to aggregate_violations()
    which keeps only citations from each camis's truly latest inspection.
    Returns {camis: set_of_types}.
    """
    codes_str = "','".join(VIOLATION_MAP.keys())
    all_rows = []
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
        all_rows.extend(page)
        print(f"  {offset + len(page)} rows fetched", flush=True)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return aggregate_violations(all_rows, latest_dates)


def main():
    with open(MANIFEST) as f:
        manifest = json.load(f)
    latest    = manifest["latest"]
    data_path = os.path.join(DATA_DIR, f"{latest}.json")

    print(f"Loading {data_path}…")
    with open(data_path) as f:
        records = json.load(f)
    print(f"  {len(records)} restaurants loaded")

    print("Fetching latest inspection date per restaurant…")
    latest_dates = fetch_latest_inspection_dates()
    print(f"  latest dates found for {len(latest_dates)} restaurants")

    print("Fetching violation flags from NYC Open Data…")
    violations = fetch_violations(latest_dates)
    print(f"  flags found for {len(violations)} restaurants")

    for record in records:
        apply_flags(record, violations.get(record["camis"]))

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
