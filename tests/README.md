# Tests

Two suites:

- **JavaScript** (Jest) — UI utilities, geo helpers, map-view logic.
- **Python** (pytest) — data-pipeline aggregation logic in `scripts/`.

## Running tests

```bash
npm test                # JavaScript (Jest)
pytest tests/           # Python (pytest)
```

Both suites run on every push and pull request via the **Tests** GitHub Actions workflow (`.github/workflows/test.yml`) as two parallel jobs: `test-js` and `test-python`. Both must pass before a PR can be merged (see "Required status checks" below).

---

## Test files

### `geo.test.js` — Geolocation polygon utilities

Tests the ray-casting functions in `scripts/geo.js` that determine whether a coordinate falls inside an NYC borough polygon.

#### `pointInRing`

The core ray-casting algorithm. Accepts a `[lng, lat]` GeoJSON ring and a point.

| Test | What it checks |
|------|----------------|
| Point clearly inside | A coordinate well within the ring returns `true` |
| Point outside (left) | A coordinate west of the ring returns `false` |
| Point outside (above) | A coordinate north of the ring returns `false` |
| Point outside (below) | A coordinate south of the ring returns `false` |

#### `pointInFeature`

Wraps `pointInRing` to handle GeoJSON `Feature` objects with `Polygon` or `MultiPolygon` geometry.

| Test | What it checks |
|------|----------------|
| Inside a Polygon | A point inside the feature's outer ring returns `true` |
| Outside a Polygon | A point outside returns `false` |
| Inside first polygon of a MultiPolygon | Returns `true` |
| Inside second polygon of a MultiPolygon | Returns `true` (all polygons are checked) |
| Outside all polygons of a MultiPolygon | Returns `false` |

#### `isInNYC`

Top-level function that checks a `[lat, lng]` coordinate against an array of GeoJSON features (the loaded NYC borough boundaries).

| Test | What it checks |
|------|----------------|
| Times Square (Manhattan) | Correctly identified as inside NYC |
| Midtown Manhattan | Correctly identified as inside NYC |
| Newark, NJ | Correctly identified as outside NYC |
| Hoboken, NJ | Correctly identified as outside NYC |
| Empty features array | Returns `false` without crashing |
| `null` features | Returns `false` — handles the state before GeoJSON has loaded |

---

### `utils.test.js` — UI utilities and location resolution

Tests the functions in `scripts/utils.js` that cover grade colours, date formatting, and all map-view decision logic.

#### `gradeColor`

Maps a health grade letter to its hex colour used by map markers and popups.

| Test | What it checks |
|------|----------------|
| Grade A | Returns `#22c55e` (green) |
| Grade B | Returns `#eab308` (yellow) |
| Grade C | Returns `#ef4444` (red) |
| Grade P | Returns `#a855f7` (purple) |
| Grade Z | Returns `#f97316` (orange) |
| Grade N | Returns `#6b7280` (grey) |
| Unknown grade | Falls back to the N colour (`#6b7280`) |

#### `formatDate`

Formats an ISO date string for display in restaurant popups.

| Test | What it checks |
|------|----------------|
| Valid ISO string | Formats to a human-readable string containing the month name and year |
| `null` | Returns an em-dash (`—`) |
| `undefined` | Returns an em-dash (`—`) |
| Empty string | Returns an em-dash (`—`) |

#### `resolveMapView` — manual locate button

Determines the map view when the user manually clicks the ◎ locate button. Always produces an actionable destination.

| Test | What it checks |
|------|----------------|
| User inside NYC | Returns the user's coordinates at zoom 18 |
| User outside NYC (NJ) | Returns Union Square (`40.7359, -73.9911`) at zoom 14 |
| User far outside NYC (London) | Returns Union Square at zoom 14 |
| Features not yet loaded | Returns Union Square at zoom 14 (safe fallback) |

#### `resolveAutoLocate` — page-load race condition (geolocation fires first)

On page load, two async operations run concurrently: fetching the NYC borough GeoJSON and calling `getCurrentPosition`. If the browser has a cached GPS fix, geolocation can resolve in milliseconds — before the GeoJSON arrives. Without handling this, `isInNYC` sees `null` features and returns `false`, leaving NYC users stuck on Union Square.

`resolveAutoLocate` is called when geolocation resolves on page load. It returns:
- `'pending'` — GeoJSON not ready yet; caller should store the position
- `{ lat, lng, zoom: 18 }` — GeoJSON loaded and user is in NYC; apply this view
- `null` — GeoJSON loaded and user is outside NYC; do nothing (stay on Union Square)

| Test | What it checks |
|------|----------------|
| GeoJSON not loaded, user in NYC | Returns `'pending'` so the position is parked for later |
| GeoJSON not loaded, user outside NYC | Returns `'pending'` (NYC check deferred until features load) |
| GeoJSON loaded, user in NYC | Returns zoom-18 view immediately |
| GeoJSON loaded, user outside NYC | Returns `null` — map stays on Union Square silently |

#### `applyPendingAutoLocate` — resolves a stored position once GeoJSON loads

Called by `loadNYCBoroughBounds` after features have been set, to action any geolocation position that was parked while the GeoJSON was in flight.

| Test | What it checks |
|------|----------------|
| Pending position inside NYC | Returns zoom-18 view — map centres on the user |
| Pending position outside NYC | Returns `null` — map stays on Union Square |
| No pending position | Returns `null` — nothing to do |
| GeoJSON failed to load | Returns `null` — any pending position is discarded, map stays on Union Square |

---

### `test_violations.py` — Pest-violation aggregation (Python)

Tests the pure aggregation logic in `scripts/violations.py` that decides which restaurants get the `rats`, `roaches`, and `hygiene` flags in our data file. Network I/O lives in `fetch_data.py` / `add_violations.py`; the date-matching rule itself is in the testable module.

Two real production bugs motivated this suite — both have dedicated regression tests:

#### Bug 1 regression — Baar Baar

The original `fetch_violations()` tracked "the latest date among rows that had a pest code". For Baar Baar that was June 2022 (04N — flies), even though the restaurant's actual current inspection was Feb 2025 with no pest codes. The fix: keep only citations whose date matches the restaurant's truly latest inspection.

| Test | What it checks |
|------|----------------|
| `test_baar_baar_old_pest_does_not_survive_later_clean_inspection` | A stale pest citation gets dropped when the camis's truly latest inspection is later and clean |
| `test_old_pest_citation_dropped_even_when_no_later_pest_row_exists` | Generalised case — any restaurant whose pest row predates its latest inspection is unflagged |

#### Bug 2 regression — Oh Taisho

After Bug 1, an older *graded* inspection with pest codes could still be flagged when a more recent *ungraded* re-inspection (clean) existed, because the comparison used the latest graded date instead of the truly latest inspection date. The fix: compare against the truly latest inspection date for that camis, computed across all inspections.

| Test | What it checks |
|------|----------------|
| `test_oh_taisho_clean_reinspection_overrides_older_graded_pest` | A pest-citing graded inspection followed by a clean ungraded re-inspection results in NO flag |
| `test_pest_on_latest_graded_inspection_still_flags_when_it_is_truly_latest` | The Bug 2 fix doesn't over-correct: pest codes on the truly latest inspection still flag |

#### Happy path

| Test | What it checks |
|------|----------------|
| `test_violation_on_latest_inspection_is_flagged` | A single pest code on the latest date produces the right flag |
| `test_multiple_codes_on_same_latest_date_merge` | Codes across different buckets on the same date all surface |
| `test_codes_in_same_bucket_collapse_to_one_flag` | 04K + 04L on the same date produce a single "rats" flag |

#### Date format edge cases

The NYC Open Data API returns timestamps like `2025-02-18T00:00:00.000`. Comparison must work on the `YYYY-MM-DD` prefix.

| Test | What it checks |
|------|----------------|
| `test_date_comparison_uses_yyyy_mm_dd_prefix_not_full_timestamp` | Different suffixes on the same date match |
| `test_different_dates_with_same_prefix_match` | Bare `2025-02-18` matches `2025-02-18T00:00:00.000` |

#### Defensive cases

| Test | What it checks |
|------|----------------|
| `test_camis_missing_from_latest_dates_is_skipped` | If we don't know the truly latest inspection date for a camis, the row is dropped (we never guess) |
| `test_unknown_violation_code_is_ignored` | Codes outside the VIOLATION_MAP are silently ignored |
| `test_row_without_camis_is_skipped` | Malformed rows without `camis` don't crash the aggregation |
| `test_empty_input_returns_empty_dict` | No rows → empty result |

#### Mixed scenarios

| Test | What it checks |
|------|----------------|
| `test_mixed_restaurants_some_flagged_some_not` | Three restaurants together (Baar Baar / Oh Taisho / clean): only the truly-flagged one comes back |

#### `apply_flags` — mutation helper

| Test | What it checks |
|------|----------------|
| `test_apply_flags_sets_all_three_keys_from_set` | The three boolean keys reflect the input set |
| `test_apply_flags_empty_set_clears_all_flags` | Existing `True` flags are reset to `False` when the input is empty |
| `test_apply_flags_none_clears_all_flags` | `None` input behaves the same as an empty set |

#### Sanity

| Test | What it checks |
|------|----------------|
| `test_violation_map_contains_known_codes` | Locks in the canonical code → bucket mapping; removing a code without updating the UI is caught here |

---

## Required status checks

To enforce these tests as merge gates on GitHub:

1. Open the repo on github.com → **Settings** → **Branches**.
2. Add a branch protection rule for `main` (or your default branch).
3. Enable **Require status checks to pass before merging**.
4. Select both `JavaScript tests (Jest)` and `Python tests (pytest)` as required checks.

After the first PR run, the two checks will appear in the list to choose from.
