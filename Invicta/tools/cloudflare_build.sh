#!/usr/bin/env bash
# Cloudflare Pages build for the ADXI: Invicta site.
# Pages settings: build command "bash Invicta/tools/cloudflare_build.sh", output folder "Invicta/site".
# Fails (and keeps the last good site live) when the scan finds errors.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 Invicta/tools/export_static.py --out Invicta/site
