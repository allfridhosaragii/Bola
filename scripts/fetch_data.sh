#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
target=.cache/openfootball
commit=e6744429ee395bc86f247348c6184bb08d4eb361
if [[ ! -d "$target/.git" ]]; then
  mkdir -p .cache
  git clone --depth 1 --single-branch https://github.com/openfootball/football.json.git "$target"
fi
if [[ -n "$(git -C "$target" status --porcelain)" ]]; then
  echo "Data checkout has local changes; inspect before refreshing: $target" >&2
  exit 1
fi
if [[ "$(git -C "$target" rev-parse HEAD)" != "$commit" ]]; then
  git -C "$target" fetch --depth 1 origin "$commit"
  git -C "$target" checkout --detach "$commit"
fi
if [[ "$(git -C "$target" rev-parse HEAD)" != "$commit" ]]; then
  echo "Dataset commit verification failed" >&2
  exit 1
fi
echo "OpenFootball dataset ready at $target ($commit)"
