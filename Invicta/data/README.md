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
| `category` | map colour (Jordan, 27 Nov 2026): `transit`, `police`, `fire`, `medical`, `homes`, `shops`, `offices`, `industry`, `utilities`, `parks`, `schools` (`keelway` is for the Keelway itself). Missing ones are worked out from the name (`atlaslib/categories.py`) |
| `purpose` | what the building is for (Jordan, 27 Nov 2026): a short plain paragraph on what it is for, who uses it and what happens there. Every building has one. The design doc lists them in its "What each building is for" section; run `python tools/purposes.py` after changing one by hand (the scan warns when they differ) |
| `outline_km` | optional shaped footprint inside `rect_km`: a list of outer rings `[[[x, y], ...], ...]` (curves as points) |
| `holes_km` | optional courtyards inside the outline: a list of rings |
| `shape` | plain words for the shape: `courtyard`, `L-shape`, `U-shape`, `curved front`, `rounded corners`, `oval`, `follows its block`, `from its plan` |

With an outline, `rect_km` stays the building's overall box (its lot): sizes, blocks and labels use the box,
the maps and 3D draw the outline, and the scan checks the outline against the hull, the precinct and the
plaza circles. Ground area is the outline minus its courtyards. Shapes are made by `atlaslib/footprints.py`
(`tools/seed_deck5_districts.py` for the Deck 5 districts it lays out, `tools/shape_buildings.py` for others).

Room plans and concept renders (Jordan, 27 Nov 2026: "scan all buildings down to each room ... I want to know what
each room does ... build a concept image for each building"):

| Field | Meaning |
|---|---|
| `design_status` | status of the architecture and room plan (`proposed` until Jordan approves), separate from the footprint's `status` |
| `floor_area_m2` | total floor area of all rooms on all floors |
| `concept_render` | path of the building's concept render (`Invicta/data/renders/D<n>/<district>/<id>.webp`), made from its 3D plan by `tools/concepts/` |

Every room and zone in `data/models/<uid>.json` carries `about`: one plain sentence on what the room does, shown in the
room panel and in the district's `Game/Docs/<District>_Rooms.md`. Buildings are designed room by room with
`tools/design_rooms.py` from programs written per district in `tools/room_programs/`; `bash tools/design_district.sh D5/<district>`
redoes a whole district (plans, doc, renders).

Plan step 4 (Jordan, 27 Nov 2026: "go"): both room designers (`tools/design_rooms.py` and `tools/build_designs.py`) end
with `atlaslib/plan_repair.py`, which makes every plan buildable with exact maths: no two spaces share floor (stair
cores first, then corridors, then the smaller room), nothing reaches past the walls or into a courtyard, no outline
crosses itself, and slivers narrower than 5 ft (1.5 m) join their neighbour. A space cut in two keeps its id on the
bigger piece; the other piece is a new element with the same name and `about`, and `"piece_of": "<id>"`. Outlines
are stored to the centimetre. `tools/build_designs.py` also carries every stair core down to the ground floor and
gives any floor people stand on without stairs a core of its own.

### Walls, doors, windows, stairs and floors (model@2)

Jordan, 27 Nov 2026 (plan step 3): the plan files hold the rooms, zones and stair cores, plus any door that was
drawn by hand. The walls, the other doors, the windows, the stairs, the lifts and the floor slabs are **worked out
from them by fixed rules** (`atlaslib/fabric.py`), the same way every time, and never written back into the plan
file. So nothing already designed is changed, and a change to a room moves its walls and doors with it. A door
drawn in the plan always wins over the rules. Everything worked out is `"derived": true` and `proposed`.

The website and the exports get the plan with its fabric added (`"schema": "invicta-atlas/model@2"`, from
`/api/model?uid=<uid>` locally or `api/models/<uid>.json` on the site). Extra element types:

| Type | Fields |
|---|---|
| `walls` | one per floor and kind: `kind` (`exterior` 1 ft (0.30 m), `core` 10 in (0.25 m), `interior` 4-7/8 in (0.12 m)), `thickness_m`, `height_m`, `lines_m` = `[[x1, y1, x2, y2], ...]` (centre lines) |
| `door`, `opening` | `line_m` (where it sits in its wall), `width_m`, `height_m`, `name` (`Door`, `Stair door`, `Entrance`, `Outside door`, `Opening`). Doors 3 ft x 6 ft 8 in (0.91 x 2.03 m), 7 ft (2.13 m) under 9 ft ceilings; double doors 6 x 7 ft (1.83 x 2.13 m); entrances 6 x 8 ft (1.83 x 2.44 m), facing the street |
| `windows` | one per floor: `sill_m`, `head_m`, `pane_width_m`, `spacing_m`, `lines_m` = `[[x1, y1, x2, y2, panes], ...]` |
| `stair` | `level` to `to_level`, `outline_m`, `risers`, `riser_m` (at most 7 in (0.178 m)), `tread_m` 11 in (0.279 m), no flight climbing more than 12 ft (3.66 m), `turns` (half-turns within the floor: 1 normally, more for a tall floor), `flights` (2 per turn, at least 3 risers each), `flight_width_m` (3 ft 11 in (1.2 m), down to 44 in (1.12 m) in a tight core), `landing_m`, `fits`, `core` |
| `lift` | `levels`, `outline_m` (8 ft 6 in (2.6 m) square), `core` |
| `slab` | `level`, `z_m`, `outline_m`, `holes_m` (stairs and lifts), `thickness_m` 1 ft (0.30 m) |

Sizes come from `data/standards.json` (Jordan, 28 Nov 2026: US building standards from the IBC, ADA and AASHTO,
US units with metric alongside). Change a size there, not in the code. Its street, block, street furniture, civil
and drafting sections are recorded for later steps and not applied yet. Its `decks` section is canon: no stairs
between decks; people and vehicles go deck to deck by fast elevators and teleport pads in the Spine Atrium.

The 3D view's Walk mode (`web/walk.js`) walks these plans as a person: walls and windows stop you, doors and
openings let you through, gravity keeps you on the floor, stairs carry you up and down, and lifts change floors.

The plan also gets `fabric`: how many elements were worked out, the entrances, and how many spaces can't be
reached or stairs don't fit (the scan lists those by building).

Architecture fields, left out until designed (the app shows "not designed yet"):
`height_m`, `floors`, `structure`, `entrances`, `look`, `capacity`, `services`, `interior`.

### Blocks

Blocks are not stored. The app works them out from the streets and buildings each time
(see CLAUDE.md). Give every building and street a name; use a generic one (Warehouse 3,
Street A) when it has no real name yet.

### Street

`{"name": "Terminal Road", "width_m": 40.0, "rect_km": [x0, x1, y0, y1]}`

## `city_programs.json`: what each district needs (city planner)

Jordan, 28 Nov 2026: every deck is a working city built around its purpose, and every building has a purpose and a
place. `decks` holds each deck's purpose. `districts` holds a program per district (only the Port of Arrivals so far):

| Field | Meaning |
|---|---|
| `purpose`, `source` | what the district is for, in Jordan's words |
| `hull_precincts` | precincts on the hull front, where the hull doors are |
| `door_classes` | kinds of hull door (`match` finds the items that carry them by name, `doors_km` are the doors), who opens them (`control`), and how many are needed (`min`; 0 = left for Jordan). Crew airlocks are checked one per 500 m frame (pressure zone) |
| `response` | fire, police and medical: every hull door within `within_km` of a building of that `category` |
| `clearance` | every hull door within `within_km` of a passport or immigration point |
| `must_have` | things the district needs somewhere (matched in names, purposes and services) |
| `per_precinct` | things every precinct needs (a utility plant, a service shaft) |
| `fixes` | what the planner adds for each gap: names, sizes, categories and purposes |

`python tools/city_planner.py D5-port-of-arrivals` prints the check; `--report` writes `Game/Docs/<District>_Planner.md` and its
mirror; `--apply` adds the proposals to the district file and its design doc as `proposed` (each new item also gets
`"planner": "city planner, 28 Nov 2026"`), after copying both to `Invicta/backups/`. It never moves, resizes or removes an
existing item, never crosses a frame or lane line, keeps 100 ft (30 m) from buildings and streets, and never places an item
where it would change how a precinct is cut into blocks, so existing block names and codes stay the same.

## `rules.json`: scanner rules

- `revB_overrides`: district values changed by decided errata.
- `retired_terms`: words that must no longer appear, and where to look.
- `mirrors`: folder pairs that must hold identical copies.
- `tolerances`: how close numbers must be.
- `acknowledged`: known issues. Any issue whose text contains `match` is shown greyed out
  as "known" with the `reason`. Add a date to the reason.
