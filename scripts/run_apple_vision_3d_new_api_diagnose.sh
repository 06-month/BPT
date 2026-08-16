#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR" || exit 1

BIN="tools/apple_vision_3d/apple_vision_3d_new_api_diagnose"
if [[ ! -x "$BIN" ]]; then
  echo "Missing executable: $BIN"
  echo "Run: bash scripts/build_apple_vision_3d_new_api.sh"
  exit 0
fi

"$BIN" --diagnose-only
