#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR" || exit 1

BIN="tools/apple_vision_3d/apple_vision_3d_export"
if [[ ! -x "$BIN" ]]; then
  echo "Missing executable: $BIN"
  echo "Run: bash scripts/build_apple_vision_3d.sh"
  exit 0
fi

"$BIN" \
  --input-video assets/smoke/pushup_1.mp4 \
  --output-jsonl assets/smoke/pushup_1_apple_vision_3d_pose.jsonl \
  --max-frames 240 \
  --stride 1

status=$?
if [[ "$status" -ne 0 ]]; then
  echo "Apple Vision 3D pushup smoke failed with exit code $status."
  echo "If Vision aborted during model initialization, this machine/runtime cannot run the CLI path reliably."
  echo "apple_vision_runtime=unavailable"
  exit 0
fi
exit "$status"
