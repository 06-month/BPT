# Research models

Downloaded research weights are intentionally excluded from Git. Configuration files required by RTMPose scripts are retained in `models/rtmpose/`.

Use the setup scripts from the repository root to restore weights when needed:

```sh
python scripts/setup_rtmpose_s_model.py
python scripts/setup_rtmpose_model.py
```

Ultralytics YOLO pose weights should also be stored under `models/` locally. Do not commit `.pt`, `.pth`, `.onnx`, checkpoint, or engine files.

Runtime models bundled into the iOS application live under `bpt/ios/Runner/NativePose/Models/` and are intentionally tracked.
