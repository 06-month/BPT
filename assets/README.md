# Research assets

This directory is intentionally source-only in Git. Local videos, extracted frames, benchmark logs, plots, NumPy arrays, JSONL output, and converted research models should be generated or restored here without being committed.

Common expected locations include:

```text
assets/mediapipe/
assets/coreml/
assets/coreml_pipeline/
assets/smoke/
assets/pushup/
assets/benchpress/
assets/deadlift/
assets/squat/
```

Download MediaPipe pose tasks with:

```sh
python tools/smoke/download_pose_landmarker.py --variant lite
```

The hand task and CoreML model used by the iOS application are separately versioned in `bpt/ios/Runner/NativePose/Models/` because they are runtime app resources.
