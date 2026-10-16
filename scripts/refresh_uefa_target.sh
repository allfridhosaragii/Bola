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
extended_history=""
if [[ -d .cache/uefa_extended_history ]]; then
  extended_history="$(find .cache/uefa_extended_history -mindepth 2 -maxdepth 2 -name manifest.json -print | sort | tail -1)"
fi
if [[ -z "$extended_history" ]]; then
  python3 scripts/fetch_uefa_extended_history.py > /dev/null
  extended_history="$(find .cache/uefa_extended_history -mindepth 2 -maxdepth 2 -name manifest.json -print | sort | tail -1)"
fi
forecast_path="$(python3 -m bola.uefa_forecast_live --target-date-utc "$target_date" --extended-history-dir "$(dirname "$extended_history")")"
python3 -m bola.uefa_forecast_live --verify "$forecast_path" > /dev/null
python3 scripts/fetch_form.py > /dev/null
python3 scripts/fetch_form_extra.py > /dev/null
python3 scripts/fetch_fotmob_form.py > /dev/null
python3 scripts/fetch_fotmob_target_teams.py > /dev/null
target_recent_dir="$(python3 scripts/fetch_fotmob_target_recent.py)"
python3 -m bola.fotmob_recent_stats --data-dir "$target_recent_dir" \
  --output "reports/target_recent_stats_${stamp}.json" > /dev/null
python3 -m bola.recent_stats_coverage --report "reports/target_recent_stats_${stamp}.json" \
  --output "reports/recent_stats_coverage_${stamp}.json" > /dev/null
python3 -m bola.odds_source_audit --output "reports/odds_source_audit_${stamp}.json" > /dev/null
python3 -m bola.form --cutoff-date-wib "$cutoff_wib" --output "reports/form_${stamp}.json" > /dev/null
python3 -m bola.form_extra --cutoff-date-wib "$cutoff_wib" --output "reports/form_extra_${stamp}.json" > /dev/null
python3 -m bola.form_fotmob --cutoff-date-wib "$cutoff_wib" --output "reports/form_fotmob_${stamp}.json" > /dev/null
python3 -m bola.form_crosscheck --form "reports/form_${stamp}.json" \
  --extra-form "reports/form_extra_${stamp}.json" --fotmob-form "reports/form_fotmob_${stamp}.json" \
  --cutoff-date-wib "$cutoff_wib" --output "reports/form_crosscheck_${stamp}.json" > /dev/null
openfootball_root="$(bash scripts/fetch_openfootball_europe.sh)"
python3 -m bola.openfootball_crosscheck --source-root "$openfootball_root" \
  --primary-crosscheck "reports/form_crosscheck_${stamp}.json" --cutoff-date-wib "$cutoff_wib" \
  --output "reports/openfootball_crosscheck_${stamp}.json" > /dev/null
fotmob_team_manifest="$(find .cache/fotmob_target_teams -mindepth 2 -maxdepth 2 -name manifest.json -print | sort | tail -1)"
python3 -m bola.schedule_load --forecast "$forecast_path" --data-dir "$(dirname "$fotmob_team_manifest")" \
  --output "reports/schedule_load_${stamp}.json" > /dev/null
python3 -m bola.uefa_target_snapshot --forecast "$forecast_path" --output "reports/uefa_target_${stamp}.json" > /dev/null
python3 -m bola.target_form_audit --forecast "$forecast_path" \
  --form "reports/form_${stamp}.json" --extra-form "reports/form_extra_${stamp}.json" \
  --fotmob-form "reports/form_fotmob_${stamp}.json" \
  --output "reports/target_form_${stamp}.json" > /dev/null
python3 -m bola.analyst_report --forecast "$forecast_path" \
  --form "reports/target_form_${stamp}.json" --squad "reports/uefa_target_${stamp}.json" \
  --schedule "reports/schedule_load_${stamp}.json" \
  --recent-stats "reports/target_recent_stats_${stamp}.json" \
  --output "reports/analyst_${stamp}.json" > /dev/null
python3 -m bola.analyst_markdown "reports/analyst_${stamp}.json" \
  --output "reports/analyst_brief_${stamp}.md" > /dev/null
python3 -m bola.target_refresh_evidence --forecast "$forecast_path" \
  --squad "reports/uefa_target_${stamp}.json" --form "reports/target_form_${stamp}.json" \
  --crosscheck "reports/form_crosscheck_${stamp}.json" --openfootball "reports/openfootball_crosscheck_${stamp}.json" \
  --schedule "reports/schedule_load_${stamp}.json" \
  --recent "reports/target_recent_stats_${stamp}.json" --coverage "reports/recent_stats_coverage_${stamp}.json" \
  --odds "reports/odds_source_audit_${stamp}.json" --analyst "reports/analyst_${stamp}.json" \
  --output "reports/target_refresh_evidence_${stamp}.json" > /dev/null
python3 - "$forecast_path" "$stamp" <<'PY'
import json
import sys
from pathlib import Path
archive = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
stamp = sys.argv[2]
squad = json.loads(Path(f"reports/uefa_target_{stamp}.json").read_text(encoding="utf-8"))
form = json.loads(Path(f"reports/target_form_{stamp}.json").read_text(encoding="utf-8"))
crosscheck = json.loads(Path(f"reports/form_crosscheck_{stamp}.json").read_text(encoding="utf-8"))
openfootball = json.loads(Path(f"reports/openfootball_crosscheck_{stamp}.json").read_text(encoding="utf-8"))
analyst = json.loads(Path(f"reports/analyst_{stamp}.json").read_text(encoding="utf-8"))
schedule = json.loads(Path(f"reports/schedule_load_{stamp}.json").read_text(encoding="utf-8"))
recent = json.loads(Path(f"reports/target_recent_stats_{stamp}.json").read_text(encoding="utf-8"))
recent_coverage = json.loads(Path(f"reports/recent_stats_coverage_{stamp}.json").read_text(encoding="utf-8"))
odds = json.loads(Path(f"reports/odds_source_audit_{stamp}.json").read_text(encoding="utf-8"))
evidence = json.loads(Path(f"reports/target_refresh_evidence_{stamp}.json").read_text(encoding="utf-8"))
print("Forecast:", sys.argv[1], "| matches:", len(archive["predictions"]))
print("UEFA squad/lineup:", f"reports/uefa_target_{stamp}.json",
      "| registered pairs:", sum(bool(row["registered_players"]) for row in squad["fixtures"]),
      "| official XI:", sum(row["official_starting_xi_before_kickoff"] for row in squad["fixtures"]))
print("Domestic form:", f"reports/target_form_{stamp}.json",
      "| covered:", form["teams_covered"], "/", form["teams_requested"])
print("Independent score cross-check:", crosscheck["independent_matches_checked"], "matches across",
      crosscheck["independent_teams"], "teams")
print("OpenFootball cross-check:", openfootball["independent_score_matches"], "/",
      openfootball["requested_score_matches"], "scores | full windows:",
      openfootball["independent_full_window_teams"])
print("Schedule load:", f"reports/schedule_load_{stamp}.json",
      "| target pairs checked:", schedule["summary"]["target_pairs_agree"],
      "| teams with an intervening match:", schedule["summary"]["teams_with_scheduled_match_before_target"],
      "| minimum projected rest hours:", schedule["summary"]["minimum_projected_rest_hours"])
print("Recent match stats:", f"reports/target_recent_stats_{stamp}.json",
      "| teams:", recent["summary"]["teams"],
      "| observations with stats:", recent["summary"]["observations_with_stats"], "/",
      recent["summary"]["team_match_observations"])
print("Recent-source coverage:", f"reports/recent_stats_coverage_{stamp}.json",
      "| raw pages:", recent_coverage["raw_pages_checked"],
      "| parser anomalies:", len(recent_coverage["anomalies"]))
print("Public odds URLs:", f"reports/odds_source_audit_{stamp}.json",
      "| quotes observed:", odds["quotes_observed"], "/", len(odds["results"]))
print("Analyst report:", f"reports/analyst_{stamp}.json",
      "| eligible:", analyst["summary"]["eligible_for_review"],
      "| no selection:", analyst["summary"]["no_selection"])
brief = Path(f"reports/analyst_brief_{stamp}.md")
print("Readable analyst brief:", brief, "| bytes:", brief.stat().st_size)
print("Refresh evidence:", f"reports/target_refresh_evidence_{stamp}.json",
      "| source reports:", len(evidence["source_report_sha256"]))
print("Status: exploratory baseline; market odds, validated tactics, and verified player availability are separate gates.")
PY
