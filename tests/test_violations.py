"""
Tests for the pest-violation aggregation logic in scripts/violations.py.

Two real bugs motivated these tests; both have regression cases below.

Bug 1 (Baar Baar):
  fetch_violations() originally tracked "the latest date among rows that had
  a pest code". For Baar Baar that was June 2022 (04N — flies), even though
  the restaurant's actual current inspection was Feb 2025 with no pest codes.
  Fix: keep only citations whose date matches the restaurant's latest
  inspection_date.

Bug 2 (Oh Taisho):
  After Bug 1 was patched, an older graded inspection with pest codes could
  still be flagged when a more recent UNGRADED re-inspection (clean) existed.
  The "latest inspection_date" used was the latest *graded* one, which
  ignored the cleaner re-inspection.
  Fix: aggregate_violations() compares against the truly latest inspection
  date for that camis (computed across all inspections, graded or not), not
  against the latest graded inspection.
"""
import os
import sys

# Make scripts/ importable as a top-level package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from violations import VIOLATION_MAP, aggregate_violations, apply_flags  # noqa: E402


# Real-world camis values used in the bug reports
BAAR_BAAR  = "50071605"
OH_TAISHO  = "40971149"
CLEAN_REST = "99999999"


def row(camis, date, code):
    """Mimic a Socrata API row."""
    return {"camis": camis, "inspection_date": date, "violation_code": code}


# ───────────────────────────────────────────────────────────────────────
# aggregate_violations — happy path
# ───────────────────────────────────────────────────────────────────────

def test_violation_on_latest_inspection_is_flagged():
    rows = [row("A", "2025-02-18T00:00:00.000", "04K")]
    latest = {"A": "2025-02-18T00:00:00.000"}
    assert aggregate_violations(rows, latest) == {"A": {"rats"}}


def test_multiple_codes_on_same_latest_date_merge():
    rows = [
        row("A", "2025-02-18T00:00:00.000", "04K"),  # rats
        row("A", "2025-02-18T00:00:00.000", "04M"),  # roaches
        row("A", "2025-02-18T00:00:00.000", "04D"),  # hygiene
    ]
    latest = {"A": "2025-02-18T00:00:00.000"}
    assert aggregate_violations(rows, latest) == {"A": {"rats", "roaches", "hygiene"}}


def test_codes_in_same_bucket_collapse_to_one_flag():
    # 04K (rats) and 04L (mice) both map to "rats"
    rows = [
        row("A", "2025-02-18T00:00:00.000", "04K"),
        row("A", "2025-02-18T00:00:00.000", "04L"),
    ]
    latest = {"A": "2025-02-18T00:00:00.000"}
    assert aggregate_violations(rows, latest) == {"A": {"rats"}}


# ───────────────────────────────────────────────────────────────────────
# Bug 1 regression — Baar Baar
# ───────────────────────────────────────────────────────────────────────

def test_baar_baar_old_pest_does_not_survive_later_clean_inspection():
    """
    Baar Baar's only pest citation (04N) is from 2022-06-07. Their current
    inspection is 2025-02-18, with no pest codes. Must NOT be flagged.
    """
    rows = [
        row(BAAR_BAAR, "2022-06-07T00:00:00.000", "04N"),
    ]
    # The truly latest inspection is in 2025, with no pest codes
    latest = {BAAR_BAAR: "2025-02-18T00:00:00.000"}
    assert aggregate_violations(rows, latest) == {}


def test_old_pest_citation_dropped_even_when_no_later_pest_row_exists():
    """Generalised case of Bug 1 — every restaurant with a stale citation."""
    rows = [row("A", "2020-01-01T00:00:00.000", "04K")]
    latest = {"A": "2024-12-15T00:00:00.000"}
    assert aggregate_violations(rows, latest) == {}


# ───────────────────────────────────────────────────────────────────────
# Bug 2 regression — Oh Taisho
# ───────────────────────────────────────────────────────────────────────

def test_oh_taisho_clean_reinspection_overrides_older_graded_pest():
    """
    Oh Taisho timeline:
      2024-09-11  no grade  (re-inspection, no pest codes)  ← truly latest
      2023-01-17  grade B   (04K — rats)
      2022-03-08  no grade  (04L — mice)

    Even though the graded inspection on 2023-01-17 had 04K, the truly
    latest inspection (2024-09-11) was clean. Must NOT be flagged.
    """
    rows = [
        row(OH_TAISHO, "2023-01-17T00:00:00.000", "04K"),
        row(OH_TAISHO, "2022-03-08T00:00:00.000", "04L"),
    ]
    # `latest_dates` reflects 2024-09-11, the truly latest inspection, NOT
    # the latest *graded* date. This is the whole point of Bug 2.
    latest = {OH_TAISHO: "2024-09-11T00:00:00.000"}
    assert aggregate_violations(rows, latest) == {}


def test_pest_on_latest_graded_inspection_still_flags_when_it_is_truly_latest():
    """The Bug 2 fix must not over-correct: if the latest GRADED inspection
    is also the truly latest inspection AND it has pest codes, flag it."""
    rows = [row("A", "2025-02-18T00:00:00.000", "04K")]
    latest = {"A": "2025-02-18T00:00:00.000"}
    assert aggregate_violations(rows, latest) == {"A": {"rats"}}


# ───────────────────────────────────────────────────────────────────────
# Date-format edge cases
# ───────────────────────────────────────────────────────────────────────

def test_date_comparison_uses_yyyy_mm_dd_prefix_not_full_timestamp():
    """Socrata returns ISO timestamps with T00:00:00.000 suffix. The function
    must compare on the date prefix so trailing-zero differences don't matter."""
    rows = [row("A", "2025-02-18T00:00:00.000", "04K")]
    # Latest has a different suffix but the same date
    latest = {"A": "2025-02-18T12:34:56.789"}
    assert aggregate_violations(rows, latest) == {"A": {"rats"}}


def test_different_dates_with_same_prefix_match():
    """Same date, both suffixed differently — they match."""
    rows = [row("A", "2025-02-18", "04K")]
    latest = {"A": "2025-02-18T00:00:00.000"}
    assert aggregate_violations(rows, latest) == {"A": {"rats"}}


# ───────────────────────────────────────────────────────────────────────
# Missing / malformed inputs
# ───────────────────────────────────────────────────────────────────────

def test_camis_missing_from_latest_dates_is_skipped():
    """If we don't know the truly latest inspection date, we can't safely
    flag. The function must drop the row rather than guess."""
    rows = [row("A", "2025-02-18T00:00:00.000", "04K")]
    assert aggregate_violations(rows, latest_dates={}) == {}


def test_unknown_violation_code_is_ignored():
    rows = [row("A", "2025-02-18T00:00:00.000", "99X")]
    latest = {"A": "2025-02-18T00:00:00.000"}
    assert aggregate_violations(rows, latest) == {}


def test_row_without_camis_is_skipped():
    rows = [{"inspection_date": "2025-02-18", "violation_code": "04K"}]
    assert aggregate_violations(rows, latest_dates={}) == {}


def test_empty_input_returns_empty_dict():
    assert aggregate_violations([], {}) == {}


# ───────────────────────────────────────────────────────────────────────
# Mixed multi-restaurant scenarios (integration-style)
# ───────────────────────────────────────────────────────────────────────

def test_mixed_restaurants_some_flagged_some_not():
    rows = [
        # CLEAN_REST — pest on truly latest inspection → flag
        row(CLEAN_REST, "2025-03-01T00:00:00.000", "04M"),

        # BAAR_BAAR — pest is stale → do NOT flag
        row(BAAR_BAAR, "2022-06-07T00:00:00.000", "04N"),

        # OH_TAISHO — pest on older graded inspection, clean re-inspection later
        row(OH_TAISHO, "2023-01-17T00:00:00.000", "04K"),
    ]
    latest = {
        CLEAN_REST: "2025-03-01T00:00:00.000",
        BAAR_BAAR:  "2025-02-18T00:00:00.000",
        OH_TAISHO:  "2024-09-11T00:00:00.000",
    }
    assert aggregate_violations(rows, latest) == {CLEAN_REST: {"roaches"}}


# ───────────────────────────────────────────────────────────────────────
# apply_flags — mutates the record correctly
# ───────────────────────────────────────────────────────────────────────

def test_apply_flags_sets_all_three_keys_from_set():
    record = {"camis": "A", "dba": "Test"}
    apply_flags(record, {"rats", "hygiene"})
    assert record["rats"] is True
    assert record["roaches"] is False
    assert record["hygiene"] is True


def test_apply_flags_empty_set_clears_all_flags():
    record = {"camis": "A", "rats": True, "roaches": True, "hygiene": True}
    apply_flags(record, set())
    assert record["rats"] is False
    assert record["roaches"] is False
    assert record["hygiene"] is False


def test_apply_flags_none_clears_all_flags():
    record = {"camis": "A", "rats": True, "roaches": True, "hygiene": True}
    apply_flags(record, None)
    assert record["rats"] is False
    assert record["roaches"] is False
    assert record["hygiene"] is False


# ───────────────────────────────────────────────────────────────────────
# Sanity: the violation map is what we expect
# ───────────────────────────────────────────────────────────────────────

def test_violation_map_contains_known_codes():
    # If someone removes one of these mappings without updating the UI,
    # the tests should catch it loudly.
    assert VIOLATION_MAP["04K"] == "rats"
    assert VIOLATION_MAP["04L"] == "rats"
    assert VIOLATION_MAP["04M"] == "roaches"
    assert VIOLATION_MAP["04N"] == "roaches"
    assert VIOLATION_MAP["04B"] == "hygiene"
    assert VIOLATION_MAP["04D"] == "hygiene"
