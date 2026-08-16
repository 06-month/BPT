# Repository consolidation

This repository was assembled on 2026-08-17 from three local working copies without modifying or deleting any of them.

## Sources

- Flutter/iOS app: clean `origin/dev/ai` snapshot at `4bc3865` (`Fix native pose camera preview`).
- Python pose-feedback source: local `dev/ai` work from the original BPT research checkout at `4614b63`, including the then-untracked source additions under `pose_feedback/experimental`, `scripts/`, and `tools/smoke`.
- Native prototype: `/Users/6_month/workspace/BPT_native_test` was compared with the app snapshot. Its native integration was already represented by the app snapshot; the two differing source files were older than the fixes in `4bc3865` and were not used to overwrite the newer versions.

## Intentionally excluded

- Git metadata and old large-file history
- CocoaPods, Flutter/Dart build products, generated Xcode state, and local Android configuration
- Cloned upstream repositories under `external/` and the MediaPipe source checkout
- Research model weights, converted experiment models, videos, frame dumps, plots, logs, and benchmark outputs
- Python bytecode and OS/editor metadata

The excluded material remains untouched in the original local working copies. This repository retains only maintainable source, small configuration files, project documentation, Flutter app assets, and the models required at iOS runtime.
