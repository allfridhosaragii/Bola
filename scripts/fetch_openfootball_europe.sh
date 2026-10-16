#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
stamp="$(python3 -c 'from datetime import datetime, timezone; print(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))')"
snapshot_root=".cache/openfootball_europe/snapshots/${stamp}"
mkdir -p .cache/openfootball_europe/snapshots
git clone --depth 1 https://github.com/openfootball/europe.git "$snapshot_root" > /dev/null
git -C "$snapshot_root" rev-parse HEAD > "$snapshot_root/COMMIT_SHA"
printf '%s\n' "$snapshot_root"
