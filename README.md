# ADXI: Invicta

The design workspace for the **Luxuria Invicta**, the ship city of the Arcane Drift world.
The site at **invicta.arcanedrift.net** shows the whole ship as a drill-down map
(ship > deck city > district > precinct > block > building), how much of it is designed,
and every open issue the scanner finds.

## Run it on your own computer

Needs Python 3.8 or newer and Shapely (the geometry library the scan uses). On Windows,
double-click `Invicta/Start ADXI Invicta.bat`: it installs Shapely the first time. By hand:

```
python -m pip install -r Invicta/requirements.txt    once
python Invicta/atlas.py           opens the app in your browser
python Invicta/atlas.py --scan    runs the scanner and writes Invicta/reports/scan_report.md
```

## What is here

| Folder | What | Can it change? |
|---|---|---|
| `Docs/1_Canon_Source/Invicta/` | Canon ship, deck and district sheets | No. Propose changes as errata in `Game/Docs/02_Canon_Errata.md`. |
| `Game/Docs/` | Invicta design docs, Rev B geometry, blueprints | Yes, by pull request. |
| `Docs/2_Design_Docs/` | Exact mirror of the Invicta docs in `Game/Docs/` | Keep identical to `Game/Docs/`. |
| `Game/Tools/InvictaGraybox/invicta_geometry.py` | The game's ship numbers | Only with Jordan's approval. |
| `Invicta/data/` | Precinct, block, building and street data | Yes, by pull request. |
| `Invicta/` | The app | Yes, by pull request. |

## How to help

1. Open an issue for a question or idea, or a pull request for a change.
2. Follow `Invicta/CLAUDE.md`: never invent what has not been designed, mark each building
   `canon`, `proposed` or `assumption`, give US units first with metric alongside, and change
   the data file and its design doc together.
3. Every pull request runs the scan. Errors block it. Jordan approves every change.

The game itself and the Arcane Drift website are separate projects and are not in this repo.

## The site chat

The panel on the right of invicta.arcanedrift.net lets anyone talk to Claude about the ship and
ask it to make a change. Claude reads this repo and opens a pull request for each agreed change.
Nothing goes live until Jordan merges it. It can't change canon, the site's own code or CI files.
Helpers can add an optional name, which is credited on their pull requests. There are no accounts.

Code: `functions/api/chat.js` (Cloudflare Pages Function) and `Invicta/web/chat.js`.

Cloudflare Pages settings:

| Setting | Value |
|---|---|
| Build command | `bash Invicta/tools/cloudflare_build.sh` |
| Build output folder | `Invicta/site` |
| Secret `ANTHROPIC_API_KEY` | the Anthropic API key that pays for the chat |
| Secret `GITHUB_TOKEN` | fine-grained token for this repo only: Contents and Pull requests, read and write |
| Variable `GITHUB_REPO` | `Jstrem2026/adxi-invicta` |
| Optional `CLAUDE_MODEL`, `DAILY_LIMIT_PER_VISITOR` (40), `DAILY_LIMIT_TOTAL` (600) | |
| KV binding `LIMITS` | a KV namespace for the daily message counters |
