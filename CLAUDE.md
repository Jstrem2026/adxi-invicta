# ADXI: Invicta repo

This repo holds only the Luxuria Invicta design material and the ADXI: Invicta app.
Follow `Invicta/CLAUDE.md` for every design change. In short:

- Run `python Invicta/atlas.py --scan` before and after. Fix new errors and warnings.
- `Docs/1_Canon_Source/` is read-only canon. Changes go through `Game/Docs/02_Canon_Errata.md`.
- Change a precinct's data file (`Invicta/data/decks/...`) and its design doc in `Game/Docs/` together,
  then copy the doc to the same path in `Docs/2_Design_Docs/`.
- Never invent anything that has not been designed. Mark statuses. US units first, metric alongside.
- `Game/Tools/InvictaGraybox/invicta_geometry.py` changes only when Jordan asks.
- Jordan approves every change. Never merge your own pull request.
