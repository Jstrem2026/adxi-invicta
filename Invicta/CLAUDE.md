# ADXI: Invicta (app) — working rules for Claude

This app reads the Luxuria Invicta design files and shows them as a drill-down map
(ship > deck city > district > precinct > block > building), a progress page and an
issue scan. It is game data only. The EX101 (the website ship) is a different ship and
does not belong here. Never touch C:\Studio\ArcaneDrift\Website.

## Where the truth lives

| What | Where | Who edits |
|---|---|---|
| Canon ship, decks, districts | `Docs/1_Canon_Source/Invicta/` | Read-only. Never edit. Changes go through `Game/Docs/02_Canon_Errata.md`. |
| Game numbers | `Game/Tools/InvictaGraybox/invicta_geometry.py` | Only when Jordan asks. |
| Design write-ups | `Game/Docs/*.md` (mirrored to `Docs/2_Design_Docs/`) | Yes, during design sessions. |
| Precinct, block and building data | `Invicta/data/decks/D<n>/<district>.json` | Yes, during design sessions. |
| Scanner rules and known issues | `Invicta/data/rules.json` | Yes. |

The app reads all of these every time it loads or rescans. There is no database
to keep in sync and no build step.

## Every design session

1. Run `python atlas.py --scan` first, so you know the starting issues.
2. When Jordan designs or changes a precinct, building or street, change both in the same session:
   - the data file `data/decks/D<n>/<district-slug>.json`, and
   - the design doc in `Game/Docs/` (for example `Port_of_Arrivals_Precincts.md`).
   The scanner compares them and flags any row that differs.
3. Copy every changed file in `Game/Docs/` to the same path in `Docs/2_Design_Docs/`.
   The scanner flags mirrors that differ.
4. Add new Invicta facts to `Game/Docs/Invicta_Ship_Reference.md` (and its mirror).
5. Run `python atlas.py --scan` again. Fix new errors and warnings before finishing.
   If an issue is real but accepted for now, add it to `acknowledged` in `data/rules.json`
   with a reason and date. Do not delete issues by weakening checks.
6. Tell Jordan what changed and what the scan says.

## Rules

- Never invent anything that has not been designed. Leave it out; the app shows it as
  "not designed yet". "We will address it slowly."
- Mark each building `status`: `canon` (Jordan approved), `proposed` (drafted, not approved)
  or `assumption` (filled in to make something work; must be confirmed).
- Plans are true top views: bow right, port up. Canon sheet plans are drawn mirrored.
- Ship frame: `x` km from the prow tip (0 to 34), `y` km across the beam, port negative.
  Frames F0 to F68 are 500 m apart. Lanes A to Y are 500 m bands, M on the centreline, A at port.
- Give measurements in US units first with metric alongside, for example
  `2,953 × 2,034 ft (900 × 620 m)`. Data files store metric (`_m`, `_km`, `_km2`).
- Blocks (Jordan, 26 Nov 2026): a block is a city block, the land between streets. The app
  cuts each precinct along its streets, then on 500 m frame or lane grid lines where a block
  is longer than 1 km, but never through a building: every building sits wholly inside one
  block (the scan reports an error otherwise). Block ids name the frame and lane of the
  bow-port corner (`D5-F43-F`, with a letter added when two share a corner); each block also
  gets a plain name (Block 1, Block 2 ...). When placing buildings, keep them clear of streets.
- Building shapes (Jordan, 27 Nov 2026): buildings follow their blocks, with curved edges along the
  atrium, the plaza rim and the hull, and courtyards, L and U shapes where they fit. Store the shape in
  `outline_km` / `holes_km` and keep `rect_km` as the overall box (see `data/README.md`).
- Map colours (Jordan, 27 Nov 2026): every building has a `category` (roads and transit dark grey, the
  Keelway light blue, police blue, fire red, medical white with a red edge, homes tan, shops orange,
  offices and government purple, industry, hangars and docks steel grey, utilities yellow, parks green,
  schools teal). Set it on every new building; `atlaslib/categories.py` holds the legend.
- Building purposes (Jordan, 27 Nov 2026): every building has a `purpose`, a short plain paragraph on what it is
  for, who uses it and what happens there, written for that building. Give every new building one, then run
  `python tools/purposes.py` so the design doc's "What each building is for" list matches.
- Map reading (Jordan, 27 Nov 2026): building names sit inside their own shape (shortened to the code, or left off,
  when they can't be read); the clickable next-level areas get an outline, with a red ring on hover; the colour
  legend is a "Legend" button beside "Codes", with a tick box per colour.
- Rooms (Jordan, 27 Nov 2026): every room and zone in a building's plan has `about`, one plain sentence on what it does.
  Deck 5 buildings are designed with `tools/design_rooms.py` from hand-written programs in `tools/room_programs/`
  (change the program, then `bash tools/design_district.sh D5/<district> --redo`); the district's `<District>_Rooms.md`
  doc lists every building, floor and room. Each building has a concept render from its 3D plan (`concept_render`).
- Room checks (Jordan, 27 Nov 2026: "Yes, use Shapely"): the scan checks every room plan in `data/models`
  with exact geometry (`atlaslib/rooms.py`): overlaps, shapes that cross themselves, rooms outside the
  building or in its courtyard, rooms under 5 ft (1.5 m) wide, floors with no stairs or lift, floors that
  don't stack. The plans made before this have these as warnings; the room designer is being reworked to
  fix them (plan step 4). A new or changed plan must not add any. Install Shapely once:
  `python -m pip install -r requirements.txt`. Tests: `python -m unittest discover -s tests -t .`
- Label everything. Anything without its own name gets a generic one: Street A, Warehouse 3,
  Berth 2. Real names always win.
- Keep game data separate from website data.

See `data/README.md` for the data file format.
