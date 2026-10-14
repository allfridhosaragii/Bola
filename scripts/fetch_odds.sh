#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p .cache/odds

fetch_verified() {
  local season="$1" expected="$2" target=".cache/odds/${1}_E0.csv"
  if [[ -f "$target" ]] && [[ "$(sha256sum "$target" | cut -d' ' -f1)" == "$expected" ]]; then
    return
  fi
  local temporary
  temporary=$(mktemp .cache/odds/download.XXXXXX)
  trap 'rm -f "$temporary"' RETURN
  curl --fail --silent --show-error --location --max-time 90 --output "$temporary" "https://www.football-data.co.uk/mmz4281/$season/E0.csv"
  if [[ "$(sha256sum "$temporary" | cut -d' ' -f1)" != "$expected" ]]; then
    echo "Odds CSV checksum mismatch for $season" >&2
    exit 1
  fi
  mv "$temporary" "$target"
  trap - RETURN
}

fetch_verified 2425 d0c8ce4a96d886cf60cf101f570f4a3893844226f91c7bd769eb568c49edbfa4
fetch_verified 2526 3e3a8352f9ada6789c508d6ca184424421fed56a30400904a4a327c583407e62
echo "Football-Data EPL 2024/25 and 2025/26 CSV checksums verified"
