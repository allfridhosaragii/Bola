#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
python3 -m bola.uefa --output reports/uefa_fixtures.json > /dev/null
python3 -m bola.uefa_squad --fixtures reports/uefa_fixtures.json --output reports/uefa_squads.json > /dev/null
python3 -m bola.uefa_lineup_api --fixtures reports/uefa_fixtures.json --output reports/uefa_lineups.json > /dev/null
python3 -m bola.dossier --fixtures reports/uefa_fixtures.json --squads reports/uefa_squads.json \
  --lineups reports/uefa_lineups.json --form reports/current_form.json \
  --output reports/prematch_dossier.json > /dev/null
python3 - <<'PY'
import json
from zoneinfo import ZoneInfo
from datetime import datetime

report = json.load(open("reports/prematch_dossier.json", encoding="utf-8"))
print("As of", datetime.fromisoformat(report["as_of"]).astimezone(ZoneInfo("Asia/Jakarta")).isoformat())
for fixture in report["fixtures"]:
    print(fixture["home"], "–", fixture["away"],
          "status:", fixture["uefa_status_at_snapshot"],
          "lineup:", fixture["uefa_lineup_status"],
          "ready:", fixture["ready_for_two_predictions"])
PY
