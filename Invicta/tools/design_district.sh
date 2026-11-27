#!/usr/bin/env bash
# Design every building of a district room by room, write its rooms doc and render its concept images.
#   bash tools/design_district.sh D5/atrium-plaza [--redo]
# Needs tools/concepts/node_modules (cd tools/concepts && npm i three@0.170.0 playwright) for the renders.
set -euo pipefail
cd "$(dirname "$0")/.."
F="$1"; shift || true
python3 tools/design_rooms.py "$F" "$@"
python3 tools/rooms_doc.py "$F"
S="$(mktemp -d)"; P="$(mktemp -d)"
python3 tools/concepts/scene.py "$F" "$S"
(cd tools/concepts && node render.mjs "$S" "$P")
python3 tools/concepts/convert.py "$F" "$P"
python3 atlas.py --scan | head -1
