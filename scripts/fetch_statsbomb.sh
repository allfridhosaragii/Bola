#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p .cache/statsbomb
commit=4b73468fc5b0f1950f9f66fada70ad3a4f9327cb
base="https://raw.githubusercontent.com/statsbomb/open-data/$commit/data"

fetch_verified() {
  local remote_path="$1" target="$2" expected="$3"
  if [[ -f "$target" ]] && [[ "$(sha256sum "$target" | cut -d' ' -f1)" == "$expected" ]]; then
    return
  fi
  local temporary
  temporary=$(mktemp .cache/statsbomb/download.XXXXXX)
  trap 'rm -f "$temporary"' RETURN
  curl --fail --silent --show-error --location --max-time 90 --output "$temporary" "$base/$remote_path"
  if [[ "$(sha256sum "$temporary" | cut -d' ' -f1)" != "$expected" ]]; then
    echo "StatsBomb checksum mismatch for $remote_path" >&2
    exit 1
  fi
  mv "$temporary" "$target"
  trap - RETURN
}

fetch_verified events/3869685.json .cache/statsbomb/events_3869685.json a0b0036d50c10a4c8879d1ee9f24a7502ec2cfb264a61951c8d500dfc897ec35
fetch_verified lineups/3869685.json .cache/statsbomb/lineups_3869685.json 2b00c4cbf027b36ae2ce99f183a0943c649bb5bdcb8324683a8603785beffed5
echo "StatsBomb match 3869685 data verified ($commit)"
