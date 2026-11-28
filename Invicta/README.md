# ADXI: Invicta

ADXI stands for Arcane Drift, version 11 (AD = Arcane Drift, XI = 11).

Blueprint explorer, progress dashboard and consistency scanner for the Luxuria Invicta.

## Run it

Needs Python 3.8 or newer and Shapely, the geometry library the scan uses.
The easy way: double-click **Start ADXI Invicta.bat** in this folder. The first time, it installs
Shapely for you. By hand:

```
cd C:\Studio\ArcaneDrift\Invicta\Invicta
python -m pip install -r requirements.txt     (once)
python atlas.py
```

Your browser opens at http://127.0.0.1:8765. If that port is busy it tries the next ones.
Press Ctrl+C in the window to stop it. Press **Rescan** in the app after you change any file.

```
python atlas.py --scan
```

runs only the scanner, prints a summary and writes `reports/scan_report.md`.
It exits with code 1 when it finds errors. The scan checks everything from the ship down to each
room in every building plan, with exact geometry. Room-plan results are kept in
`reports/room_check_cache.json` so a rescan only re-checks the plans that changed.

```
python -m unittest discover -s tests -t .
```

runs the tests for the geometry and the room checks.

Other options: `--port 9000`, `--no-browser`, `--root <ArcaneDrift folder>`.

## Pages

- **Progress**: how much of the ship is designed, by level and by deck, and the issue counts.
- **Explore**: click the ship, a deck city, a district, a precinct, a block, then a building.
  Wheel to zoom, drag to pan. Areas with no design show hatched and say "not designed yet".
- **Issues**: everything the scanner found, filterable. Errors, continuity warnings,
  items waiting on Jordan, and areas not designed yet.
- **Sources**: every file the app reads, whether it was found, and when it last changed.

## What it reads

Canon datasheets and geometry in `Docs/1_Canon_Source/Invicta`, the design docs in
`Game/Docs`, the game constants in `Game/Tools/InvictaGraybox/invicta_geometry.py`, and its own
`data/` folder. It never writes to any of them.

## Folders

- `atlas.py`: start here.
- `atlaslib/`: loader, geometry (exact, with Shapely), scanner, room-plan checks (`rooms.py`), walls/doors/windows/stairs worked out from the rooms (`fabric.py`), progress, server.
- `tests/`: tests for the geometry and the room checks.
- `web/`: the browser app.
- `data/`: precinct and building data, and scanner rules. See `data/README.md`.
- `tools/`: one-time import scripts (precinct SVG reader, Port of Arrivals seed).
- `reports/`: scan reports (generated).
- `docs/`: readable docs for every district, precinct and building plan, generated from the data by
  `python tools/gen_docs.py` (a few seconds). Not kept in git; the published copy is at
  invicta.arcanedrift.net/docs/README.md.

Rules for Claude design sessions are in `CLAUDE.md`.
