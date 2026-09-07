# Apple Vision 3D Body Pose Smoke Test

This repository includes an experimental Apple Vision 3D body-pose path for
macOS/iOS feasibility checks. It is a platform-native baseline, not a
replacement for the existing RTMPose, MediaPipe, WristEstimator, FeedbackEngine,
Uplift, or MotionAGFormer code paths.

## Requirements

- macOS 14+ or iOS 17+ SDK/runtime for `VNDetectHumanBodyPose3DRequest`.
- Xcode command-line tools with `swiftc`.
- Apple Silicon or another Apple platform supported by Vision 3D body pose.
- Runtime support can still vary by OS build and device. Some systems may fail
  inside Vision model initialization even when the SDK compiles.

The Swift helper is intentionally small and command-line oriented. If direct
`swiftc` compilation or runtime model loading fails, use an Xcode app target as
the next integration step so entitlements, deployment target, and runtime
settings can be controlled explicitly.

## What It Exports

Apple Vision 3D body pose estimates a 3D body skeleton from RGB frames. The
coordinates are useful as a platform-native real-time baseline, but they are not
guaranteed to be mocap-accurate or camera-calibrated world coordinates.

The exporter writes JSONL records with:

- `frame_idx`
- `timestamp_sec`
- `body_detected`
- `joints`
- `raw_joint_names`

Each joint contains model-relative 3D coordinates and, when available, a 2D
image projection in normalized and pixel coordinates.

## Build

```bash
bash scripts/build_apple_vision_3d.sh
```

Expected binary:

```text
tools/apple_vision_3d/apple_vision_3d_export
```

## Run

```bash
bash scripts/run_apple_vision_3d_pushup.sh
bash scripts/run_apple_vision_3d_vedio_1.sh
```

Manual form:

```bash
tools/apple_vision_3d/apple_vision_3d_export \
  --input-video assets/smoke/pushup_1.mp4 \
  --output-jsonl assets/smoke/pushup_1_apple_vision_3d_pose.jsonl \
  --max-frames 240 \
  --stride 1
```

## Visualize And Diagnose

```bash
conda run -n bpt-ai python scripts/visualize_apple_vision_3d_jsonl.py \
  --video assets/smoke/pushup_1.mp4 \
  --jsonl assets/smoke/pushup_1_apple_vision_3d_pose.jsonl \
  --output-side-by-side assets/smoke/pushup_1_apple_vision_3d_side_by_side.mp4 \
  --max-frames 240

conda run -n bpt-ai python scripts/diagnose_apple_vision_3d_jsonl.py \
  --jsonl assets/smoke/pushup_1_apple_vision_3d_pose.jsonl \
  --output-csv assets/smoke/pushup_1_apple_vision_3d_summary.csv
```

If JSONL is missing because Vision runtime failed, the Python scripts exit
cleanly and report the missing input.
