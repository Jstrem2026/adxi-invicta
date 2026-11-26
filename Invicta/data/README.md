# App data files

## `decks/D<n>/<district-slug>.json`: one file per district with a precinct plan

Districts without a file show as "not designed yet". Do not create a file for a
district until Jordan designs it.

```json
{
  "schema": "invicta-atlas/precincts@1",
  "deck": 5,
  "district": "Port of Arrivals",          // must match the name on the canon deck sheet
  "status": "proposed",                    // proposed | canon
  "version": "v2",
  "updated": "2026-11-26",
  "doc": "Game/Docs/Port_of_Arrivals_Precincts.md",   // the design doc this mirrors
  "overview_blueprint": "Game/Docs/art/blueprints/port-of-arrivals-precincts.png",
  "precincts": [ ... ]
}
```

### Precinct

| Field | Meaning |
|---|---|
| `id`, `name` | `P1`, `Bow Docks` |
| `frames`, `lanes` | text, for example `F33 to F38`, `A to D` |
| `bounds_km` | `[x0, x1, y0, y1]` in ship km |
| `polygon_km` | optional outline `[[x, y], ...]` when not a rectangle |
| `exclude_circles_km` | optional `[[x, y, r], ...]` cut out (for example the canon Atrium Plaza) |
| `area_km2_stated` | area given in the design doc (checked against the computed area) |
| `status`, `role`, `intro`, `build_order` | text |
| `blueprint`, `blueprint_svg` | paths from the ArcaneDrift folder |
| `buildings`, `streets` | lists, below |

### Building

| Field | Meaning |
|---|---|
| `id`, `name` | `P5-01`, `Transfer Hall` (ids are unique within the district) |
| `status` | `canon`, `proposed` or `assumption` |
| `kind` | `building`, `hangar`, `yard`, `plaza`, `park`, `transport`, ... |
| `size_text` | as written in the doc, US first: `2,953 × 2,034 ft (900 × 620 m)` |
| `size_m` | `[length, width]` in metres (checked against `rect_km`) |
| `rect_km` | `[x0, x1, y0, y1]` footprint in ship km |
| `notes` | text |
| `bays_km`, `doors_km`, `bay_count`, `bay_names` | optional detail for hangars and docks |

Architecture fields, left out until designed (the app shows "not designed yet"):
`height_m`, `floors`, `structure`, `entrances`, `look`, `capacity`, `services`, `interior`.

### Street

`{"name": "Terminal Road", "width_m": 40.0, "rect_km": [x0, x1, y0, y1]}`

## `rules.json`: scanner rules

- `revB_overrides`: district values changed by decided errata.
- `retired_terms`: words that must no longer appear, and where to look.
- `mirrors`: folder pairs that must hold identical copies.
- `tolerances`: how close numbers must be.
- `acknowledged`: known issues. Any issue whose text contains `match` is shown greyed out
  as "known" with the `reason`. Add a date to the reason.
