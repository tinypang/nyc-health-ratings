#!/usr/bin/env python3
"""
Weekly fetch of NYC DOHMH restaurant inspection data.
Deduplicates to latest grade per restaurant, diffs against previous week,
and prunes files older than KEEP_WEEKS weeks.
"""
import json
import os
from datetime import datetime, timezone
from urllib.request import urlopen
from urllib.parse import urlencode

API_BASE = "https://data.cityofnewyork.us/resource/43nn-pn8j.json"
PAGE_SIZE = 50000
KEEP_WEEKS = 4
FIELDS = "camis,dba,boro,cuisine_description,latitude,longitude,grade,grade_date,inspection_date,score"
GRADE_ORDER = {"A": 1, "B": 2, "C": 3, "Z": 4, "P": 4, "N": 5}

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MANIFEST = os.path.join(DATA_DIR, "manifest.json")


def fetch_page(offset):
    params = urlencode({
        "$limit": PAGE_SIZE,
        "$offset": offset,
        "$where": "latitude IS NOT NULL AND grade IS NOT NULL",
        "$select": FIELDS,
        "$order": "inspection_date DESC",
    })
    with urlopen(f"{API_BASE}?{params}", timeout=60) as r:
        return json.loads(r.read())


def fetch_all():
    seen = {}
    offset = 0
    while True:
        print(f"  offset {offset}…", flush=True)
        page = fetch_page(offset)
        if not page:
            break
        for row in page:
            if row["camis"] not in seen:
                seen[row["camis"]] = row
        print(f"  {offset + len(page)} fetched, {len(seen)} unique", flush=True)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return list(seen.values())


def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            return json.load(f)
    return {"latest": None, "previous": None, "weeks": []}


def load_data_file(date_str):
    path = os.path.join(DATA_DIR, f"{date_str}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return {r["camis"]: r for r in json.load(f)}


def compute_diff(current, prev_map, today, prev_date):
    curr_map = {r["camis"]: r for r in current}
    curr_keys = set(curr_map)
    prev_keys = set(prev_map)

    def slim(r, extra=None):
        d = {k: r.get(k) for k in ("camis", "dba", "grade", "boro", "cuisine_description")}
        if extra:
            d.update(extra)
        return d

    added   = [slim(curr_map[c]) for c in sorted(curr_keys - prev_keys, key=lambda c: curr_map[c].get("dba") or "")]
    removed = [slim(prev_map[c]) for c in sorted(prev_keys - curr_keys, key=lambda c: prev_map[c].get("dba") or "")]

    improved, declined = [], []
    for camis in sorted(curr_keys & prev_keys, key=lambda c: curr_map[c].get("dba") or ""):
        cg = curr_map[camis].get("grade", "N")
        pg = prev_map[camis].get("grade", "N")
        if cg == pg:
            continue
        entry = slim(curr_map[camis], {"from": pg, "to": cg})
        if GRADE_ORDER.get(cg, 5) < GRADE_ORDER.get(pg, 5):
            improved.append(entry)
        else:
            declined.append(entry)

    return {
        "date": today,
        "previous": prev_date,
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "improved": len(improved),
            "declined": len(declined),
        },
        "added": added,
        "removed": removed,
        "improved": improved,
        "declined": declined,
    }


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"Fetching data for {today}…")

    records = fetch_all()
    print(f"Total unique restaurants: {len(records)}")

    out_path = os.path.join(DATA_DIR, f"{today}.json")
    with open(out_path, "w") as f:
        json.dump(records, f, separators=(",", ":"))
    print(f"Saved {out_path}")

    manifest = load_manifest()
    prev_date = manifest.get("latest")

    if prev_date and prev_date != today:
        prev_map = load_data_file(prev_date)
        if prev_map:
            print(f"Diffing against {prev_date}…")
            diff = compute_diff(records, prev_map, today, prev_date)
            s = diff["summary"]
            print(f"  +{s['added']} added  -{s['removed']} removed  ↑{s['improved']} improved  ↓{s['declined']} declined")
            diff_path = os.path.join(DATA_DIR, f"diff-{today}.json")
            with open(diff_path, "w") as f:
                json.dump(diff, f, separators=(",", ":"))
            print(f"Saved {diff_path}")

    weeks = manifest.get("weeks", [])
    if today not in weeks:
        weeks.append(today)
    weeks = sorted(set(weeks))

    if len(weeks) > KEEP_WEEKS:
        for old in weeks[:-KEEP_WEEKS]:
            for fname in (f"{old}.json", f"diff-{old}.json"):
                fp = os.path.join(DATA_DIR, fname)
                if os.path.exists(fp):
                    os.remove(fp)
                    print(f"Pruned {fp}")
        weeks = weeks[-KEEP_WEEKS:]

    new_manifest = {
        "latest": today,
        "previous": weeks[-2] if len(weeks) >= 2 else None,
        "weeks": weeks,
    }
    with open(MANIFEST, "w") as f:
        json.dump(new_manifest, f, indent=2)
    print(f"Done. Manifest: {new_manifest}")


if __name__ == "__main__":
    main()
