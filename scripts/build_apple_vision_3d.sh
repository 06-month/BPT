#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR" || exit 1

mkdir -p /private/tmp/swift_module_cache tools/apple_vision_3d

echo "Building Apple Vision 3D exporter..."
if swiftc \
  -module-cache-path /private/tmp/swift_module_cache \
  tools/apple_vision_3d/AppleVision3DPoseExport.swift \
  -framework Vision \
  -framework AVFoundation \
  -framework CoreMedia \
  -framework CoreImage \
  -o tools/apple_vision_3d/apple_vision_3d_export; then
  echo "Built tools/apple_vision_3d/apple_vision_3d_export"
else
  status=$?
  echo "Apple Vision 3D Swift CLI build failed."
  echo "This can happen when the local SDK does not expose VNDetectHumanBodyPose3DRequest or swiftc cannot build Vision CLI tools."
  echo "Use an Xcode macOS/iOS app target if direct swiftc compilation is unavailable."
  exit "$status"
fi
