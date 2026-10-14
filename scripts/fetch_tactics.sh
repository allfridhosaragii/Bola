#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
target=.cache/metrica
commit=e706dd506b360d69d9d123d5b8026e7294b13996
if [[ ! -d "$target/.git" ]]; then
  mkdir -p .cache
  git clone --depth 1 --filter=blob:none --sparse https://github.com/metrica-sports/sample-data.git "$target"
fi
if [[ -n "$(git -C "$target" status --porcelain)" ]]; then
  echo "Metrica checkout has local changes; inspect before refreshing: $target" >&2
  exit 1
fi
if [[ "$(git -C "$target" rev-parse HEAD)" != "$commit" ]]; then
  git -C "$target" fetch --depth 1 origin "$commit"
  git -C "$target" checkout --detach "$commit"
fi
git -C "$target" sparse-checkout set data/Sample_Game_1 data/Sample_Game_2
if [[ "$(git -C "$target" rev-parse HEAD)" != "$commit" ]]; then
  echo "Metrica commit verification failed" >&2
  exit 1
fi
echo "Metrica sample ready at $target ($commit)"
