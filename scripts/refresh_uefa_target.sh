#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
target_date="${1:?Usage: bash scripts/refresh_uefa_target.sh YYYY-MM-DD (UTC match date)}"
if [[ ! "$target_date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "Target must be a UTC date in YYYY-MM-DD format" >&2
  exit 2
fi
stamp="$(python3 -c 'from datetime import datetime, timezone; print(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))')"
cutoff_wib="$(TZ=Asia/Jakarta date +%F)"
forecast_path="$(python3 -m bola.uefa_forecast_live --target-date-utc "$target_date")"
python3 -m bola.uefa_forecast_live --verify "$forecast_path" > /dev/null
python3 scripts/fetch_form.py > /dev/null
python3 scripts/fetch_form_extra.py > /dev/null
python3 scripts/fetch_fotmob_form.py > /dev/null
python3 -m bola.form --cutoff-date-wib "$cutoff_wib" --output "reports/form_${stamp}.json" > /dev/null
python3 -m bola.form_extra --cutoff-date-wib "$cutoff_wib" --output "reports/form_extra_${stamp}.json" > /dev/null
python3 -m bola.form_fotmob --cutoff-date-wib "$cutoff_wib" --output "reports/form_fotmob_${stamp}.json" > /dev/null
python3 -m bola.uefa_target_snapshot --forecast "$forecast_path" --output "reports/uefa_target_${stamp}.json" > /dev/null
python3 -m bola.target_form_audit --forecast "$forecast_path" \
  --form "reports/form_${stamp}.json" --extra-form "reports/form_extra_${stamp}.json" \
  --fotmob-form "reports/form_fotmob_${stamp}.json" \
  --output "reports/target_form_${stamp}.json" > /dev/null
python3 -m bola.analyst_report --forecast "$forecast_path" \
  --form "reports/target_form_${stamp}.json" --squad "reports/uefa_target_${stamp}.json" \
  --output "reports/analyst_${stamp}.json" > /dev/null
python3 - "$forecast_path" "$stamp" <<'PY'
import json
import sys
from pathlib import Path
archive = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
stamp = sys.argv[2]
squad = json.loads(Path(f"reports/uefa_target_{stamp}.json").read_text(encoding="utf-8"))
form = json.loads(Path(f"reports/target_form_{stamp}.json").read_text(encoding="utf-8"))
analyst = json.loads(Path(f"reports/analyst_{stamp}.json").read_text(encoding="utf-8"))
print("Forecast:", sys.argv[1], "| matches:", len(archive["predictions"]))
print("UEFA squad/lineup:", f"reports/uefa_target_{stamp}.json",
      "| registered pairs:", sum(bool(row["registered_players"]) for row in squad["fixtures"]),
      "| official XI:", sum(row["official_starting_xi_before_kickoff"] for row in squad["fixtures"]))
print("Domestic form:", f"reports/target_form_{stamp}.json",
      "| covered:", form["teams_covered"], "/", form["teams_requested"])
print("Analyst report:", f"reports/analyst_{stamp}.json",
      "| eligible:", analyst["summary"]["eligible_for_review"],
      "| no selection:", analyst["summary"]["no_selection"])
print("Status: exploratory baseline; market odds, validated tactics, and verified player availability are separate gates.")
PY
