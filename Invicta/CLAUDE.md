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
- Label everything. Anything without its own name gets a generic one: Street A, Warehouse 3,
  Berth 2. Real names always win.
- Keep game data separate from website data.

See `data/README.md` for the data file format.
