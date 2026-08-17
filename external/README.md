# Optional upstream research repositories

Large third-party repositories are not vendored into BPT Unified. Restore only the dependency needed for a specific experiment.

The previous local workspace used these upstream revisions:

| Directory | Repository | Revision |
| --- | --- | --- |
| `MotionAGFormer` | `https://github.com/TaatiTeam/MotionAGFormer.git` | `4756fd1eb7cc73f0e991f091ff2280e030ab85f3` |
| `uplift-upsample-3dhpe` | `https://github.com/goldbricklemon/uplift-upsample-3dhpe.git` | `08ef1f34d3d6a0b5601f94334ec38278fae3f90b` |
| `2DEstimatorEval` | `https://github.com/TaatiTeam/2DEstimatorEval.git` | `94c9b7ae7b16872ca63322cd9a8d08ae7ca78b67` |

Example:

```sh
git clone https://github.com/TaatiTeam/MotionAGFormer.git external/MotionAGFormer
git -C external/MotionAGFormer checkout 4756fd1eb7cc73f0e991f091ff2280e030ab85f3
```

The previous MediaPipe source checkout used `google-ai-edge/mediapipe` at revision `e0a62f57477fa568c4fb27ff2a42d1df0d41d07d`; most Python workflows should prefer the packaged dependency unless source-level work is required.
