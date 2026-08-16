# BPT Unified

BPT Unified is the consolidated source repository for the BPT exercise-coaching project. It combines the Flutter/iOS application with the Python reference and evaluation pipeline used to develop on-device pose and wrist feedback.

The product target is stable, low-latency feedback on a phone. The first wrist-feedback MVP is `pushup_side`; bimanual exercises remain a later extension.

## Repository layout

| Path | Purpose |
| --- | --- |
| `bpt/` | Flutter application and native iOS camera/CoreML/MediaPipe integration |
| `pose_feedback/` | Modular Python pose, hand, wrist, and feedback reference implementation |
| `scripts/` | Conversion, benchmarking, diagnostics, and visualization commands |
| `tests/` | Python unit and pipeline tests |
| `tools/` | Minimal Swift and Python smoke/profiling tools |
| `docs/` | iOS integration, CoreML, research, and project documents |
| `models/` | Model configuration files and local model setup guidance |
| `assets/` | Local research input/output guidance; large artifacts are not versioned |
| `external/` | Instructions for restoring optional upstream research repositories |

## Flutter and iOS app

```sh
cd bpt
flutter pub get
cd ios
pod install
open Runner.xcworkspace
```

Always open `Runner.xcworkspace`, not `Runner.xcodeproj`. Camera, CoreML, MediaPipe, performance, and signing should be validated on a physical iPhone.

The iOS runtime models required by the current native pose path are intentionally versioned under:

```text
bpt/ios/Runner/NativePose/Models/
```

## Python reference pipeline

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
pytest
```

Research models, videos, generated overlays, dependency checkouts, and build products are intentionally excluded. See [assets/README.md](assets/README.md), [models/README.md](models/README.md), and [external/README.md](external/README.md) when reproducing experiments.

## Source policy

- YOLO body keypoints own left/right identity.
- Image-space and hand-world coordinates must not be mixed.
- Exercise thresholds belong in configuration, not estimator logic.
- Temporal behavior uses seconds rather than frame counts.
- Generated dependencies and experiment outputs do not belong in Git.

See [AGENTS.md](AGENTS.md) for the detailed architecture and implementation rules. See [docs/migration.md](docs/migration.md) for the consolidation record.
