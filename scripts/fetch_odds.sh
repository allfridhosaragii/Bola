#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p .cache/odds

fetch_verified() {
  local season="$1" league="$2" expected="$3" target=".cache/odds/${1}_${2}.csv"
  if [[ -f "$target" ]] && [[ "$(sha256sum "$target" | cut -d' ' -f1)" == "$expected" ]]; then
    return
  fi
  local temporary
  temporary=$(mktemp .cache/odds/download.XXXXXX)
  trap 'rm -f "$temporary"' RETURN
  curl --fail --silent --show-error --location --max-time 90 --output "$temporary" "https://www.football-data.co.uk/mmz4281/$season/$league.csv"
  if [[ "$(sha256sum "$temporary" | cut -d' ' -f1)" != "$expected" ]]; then
    echo "Odds CSV checksum mismatch for $season $league" >&2
    exit 1
  fi
  mv "$temporary" "$target"
  trap - RETURN
}

fetch_verified 2425 E0 d0c8ce4a96d886cf60cf101f570f4a3893844226f91c7bd769eb568c49edbfa4
fetch_verified 2526 E0 3e3a8352f9ada6789c508d6ca184424421fed56a30400904a4a327c583407e62
fetch_verified 2425 D1 a295c58033cfe6393cbbc28f7db85671839b960c5f1153fd3678e20ad2adb92e
fetch_verified 2526 D1 618301a4b39918225a8ccc57f0f839d675e1abd92fa3a3ccd9a67acd7c79dd7f
fetch_verified 2425 N1 7f97f0a7fd1f9b2cff6ac09588cdc14fd07f19950cb75e821fa58ab41e541d0a
echo "Football-Data EPL, Bundesliga, and Eredivisie historical CSV checksums verified"
