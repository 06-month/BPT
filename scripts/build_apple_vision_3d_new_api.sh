#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR" || exit 1

mkdir -p /private/tmp/swift_module_cache tools/apple_vision_3d

echo "Building Apple Vision 3D new Swift API diagnostic..."
if swiftc \
  -parse-as-library \
  -module-cache-path /private/tmp/swift_module_cache \
  tools/apple_vision_3d/AppleVision3DNewAPIDiagnose.swift \
  -framework Vision \
  -framework AVFoundation \
  -framework CoreMedia \
  -framework CoreImage \
  -o tools/apple_vision_3d/apple_vision_3d_new_api_diagnose; then
  echo "Built tools/apple_vision_3d/apple_vision_3d_new_api_diagnose"
else
  status=$?
  echo "Apple Vision 3D new Swift API build failed."
  echo "If swiftc cannot compile the async Vision API, use a minimal Swift Package or Xcode app target."
  exit "$status"
fi
