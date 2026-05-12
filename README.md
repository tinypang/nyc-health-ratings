# NYC Food Health Ratings

An interactive map of every NYC food establishment, coloured by its most recent DOHMH health grade.

![Grades: A = green, B = yellow, C = red, P = purple, Z = orange, N = grey](https://img.shields.io/badge/data-NYC%20Open%20Data-blue)

## Features

- **All restaurants** — fetches the full DOHMH inspection dataset (~27,000+ unique establishments) on page load, deduplicated to each restaurant's latest grade
- **Colour-coded markers** — instantly see health grades across the city
  - 🟢 **A** — Excellent (score 0–13)
  - 🟡 **B** — Good (score 14–27)
  - 🔴 **C** — Needs improvement (score 28+)
  - 🟣 **P** — Grade pending (re-inspection in progress)
  - 🟠 **Z** — Grade pending (initial inspection)
  - ⚫ **N** — Not yet graded
- **Clustered markers** — dots group at low zoom levels and expand as you zoom in
- **Restaurant popups** — click any dot to see the name, grade, cuisine type, borough, inspection score, grade date, last inspection date, and a direct link to the full violation report on the DOHMH website
- **Search** — type a restaurant name to get a live dropdown; selecting a result flies the map to that marker and opens its popup
- **Grade filters** — click any grade in the legend to show/hide that tier across the whole map
- **Use my location** — the ◎ button centres the map on your current browser location at street level

## Data sources

| Source | Description |
|--------|-------------|
| [DOHMH New York City Restaurant Inspection Results](https://data.cityofnewyork.us/Health/DOHMH-New-York-City-Restaurant-Inspection-Results/43nn-pn8j) | NYC Open Data — the primary dataset. Updated daily. Contains inspection dates, violation codes, scores, and grades for every permitted food establishment in the five boroughs. |
| [NYC ABCEats Restaurant Lookup](https://a816-health.nyc.gov/ABCEatsRestaurants) | NYC Department of Health — used for the per-restaurant violation detail pages linked from each popup. |

Map tiles are provided by [CARTO](https://carto.com/) (Dark Matter style) via [OpenStreetMap](https://www.openstreetmap.org/) contributors.

## Running locally

No build step required — it's a single HTML file.

```bash
python3 -m http.server 8080
```

Then open [http://localhost:8080](http://localhost:8080).

## Live site

[tinypang.github.io/health-ratings](https://tinypang.github.io/health-ratings)
