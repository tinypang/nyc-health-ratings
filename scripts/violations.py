"""
Pure, network-free helpers for the violation-flag pipeline.

Kept separate from fetch_data.py / add_violations.py so the date-matching
logic can be unit-tested without hitting the NYC Open Data API.
"""

# Violation codes we surface to the UI, mapped to the filter bucket.
# Only citations on a restaurant's most recent inspection are flagged.
VIOLATION_MAP = {
    "04K": "rats",     # live rats
    "04L": "rats",     # live mice
    "04M": "roaches",  # live roaches
    "04N": "roaches",  # filth flies / food-associated flies
    "04B": "hygiene",  # preparing food while ill or injured
    "04D": "hygiene",  # inadequate handwashing
}


def aggregate_violations(rows, latest_dates, violation_map=VIOLATION_MAP):
    """
    Given parsed pest-citation rows and a {camis: latest_inspection_date} map,
    return {camis: set_of_violation_types} containing ONLY citations whose
    inspection_date matches the camis's truly latest inspection date.

    This is the core "don't carry forward old pest citations" rule, isolated
    from network I/O so it can be exhaustively tested.

    Parameters
    ----------
    rows : iterable of dicts
        Each row needs `camis`, `inspection_date`, `violation_code`.
    latest_dates : dict[str, str]
        Map of camis → that restaurant's most recent inspection_date.
        Dates may include a `T...` suffix; we compare on the YYYY-MM-DD prefix.
    violation_map : dict[str, str]
        Map of violation_code → bucket. Codes not in the map are ignored.

    Returns
    -------
    dict[str, set[str]]
        {camis: {bucket, ...}} — only camis with at least one matching citation.
    """
    out = {}
    for row in rows:
        camis = row.get("camis")
        if not camis:
            continue
        vtype = violation_map.get(row.get("violation_code", ""))
        if not vtype:
            continue
        latest = latest_dates.get(camis)
        if not latest:
            continue
        idate = row.get("inspection_date", "")
        if idate[:10] != latest[:10]:
            continue
        out.setdefault(camis, set()).add(vtype)
    return out


def apply_flags(record, violations_for_camis):
    """
    Mutate a restaurant `record` in place, setting the three boolean flags
    (`rats`, `roaches`, `hygiene`) based on the set returned by
    aggregate_violations for that camis.

    Pass an empty set (or None) to clear all three.
    """
    vtypes = violations_for_camis or set()
    record["rats"]    = "rats"    in vtypes
    record["roaches"] = "roaches" in vtypes
    record["hygiene"] = "hygiene" in vtypes
    return record
