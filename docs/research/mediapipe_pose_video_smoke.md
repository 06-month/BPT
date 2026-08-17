# MediaPipe Pose Landmarker — VIDEO-mode smoke test

Qualitative tool to visually compare **MediaPipe Pose** body keypoint stability
against the current **RTMPose-s** body pipeline on the bundled clip
`assets/smoke/vedio_1.mp4`.

It uses the MediaPipe **Tasks API** `PoseLandmarker` (not the deprecated
`mp.solutions.pose`) in `RunningMode.VIDEO` with `detect_for_video()`.

This is presentation/evidence tooling only. It does not modify RTMPose,
MotionAGFormer, the iOS app, or any model-conversion code.

## 1. Get the model

The Pose Landmarker `.task` model is not committed. Three official variants are
available — `lite` (fastest), `full`, and `heavy` (most accurate). Download with:

```bash
python tools/smoke/download_pose_landmarker.py                 # lite (default)
python tools/smoke/download_pose_landmarker.py --variant full
python tools/smoke/download_pose_landmarker.py --variant heavy
```

Each writes `assets/mediapipe/pose_landmarker_<variant>.task`.

If automatic download fails, download manually:

1. Download `pose_landmarker_<variant>.task` from the official MediaPipe Pose
   Landmarker model page:
   <https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker#models>
2. Place it at `assets/mediapipe/pose_landmarker_<variant>.task`.

Observed runtime on `vedio_1.mp4` (240 frames, 1080×1920, Apple M4, CPU
delegate), all variants 100% detection rate:

| Variant | Model size | Runtime FPS |
| --- | --- | --- |
| lite | ~5.8 MB | ~50 |
| full | ~9.4 MB | ~43 |
| heavy | ~30.7 MB | ~16 |

## 2. Run the smoke test

```bash
python tools/smoke/mediapipe_pose_video_smoke.py \
  --video assets/smoke/vedio_1.mp4 \
  --model assets/mediapipe/pose_landmarker_lite.task \
  --out outputs/mediapipe_pose_video_smoke.mp4
```

Heavy model (most accurate, slowest):

```bash
python tools/smoke/mediapipe_pose_video_smoke.py \
  --video assets/smoke/vedio_1.mp4 \
  --model assets/mediapipe/pose_landmarker_heavy.task \
  --out outputs/mediapipe_pose_video_smoke_heavy.mp4
```

Low-confidence variant (more lenient detection/tracking):

```bash
python tools/smoke/mediapipe_pose_video_smoke.py \
  --video assets/smoke/vedio_1.mp4 \
  --model assets/mediapipe/pose_landmarker_lite.task \
  --out outputs/mediapipe_pose_video_smoke_lowconf.mp4 \
  --min-pose-detection-confidence 0.3 \
  --min-pose-presence-confidence 0.3 \
  --min-tracking-confidence 0.3
```

## Arguments

| Arg | Default | Meaning |
| --- | --- | --- |
| `--video` | `assets/smoke/vedio_1.mp4` | input video |
| `--model` | `assets/mediapipe/pose_landmarker_lite.task` | Pose Landmarker `.task` model |
| `--out` | `outputs/mediapipe_pose_video_smoke.mp4` | annotated output video |
| `--max-frames` | `0` (full video) | cap processed frames |
| `--min-pose-detection-confidence` | `0.5` | detection confidence |
| `--min-pose-presence-confidence` | `0.5` | presence confidence |
| `--min-tracking-confidence` | `0.5` | tracking confidence |

The script prints the video/model/output paths, processed frames, detected
frames, detection rate, and runtime FPS.
