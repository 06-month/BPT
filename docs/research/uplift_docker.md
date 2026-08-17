# Uplift-Upsample Docker Smoke Runtime

## Current Status

Uplift-Upsample is now treated as an offline reference and previous experiment, not the real-time 3D lifter candidate. The current real-time candidate is MotionAGFormer with short lookahead padding, because it is PyTorch-native and can be evaluated in the same family of runtime dependencies as RTMPose.

Uplift-Upsample uses a TensorFlow/Keras `.h5` runtime, while `bpt-ai` contains the working PyTorch, MMPose, MMCV, and RTMPose stack. Keep those environments separate so TensorFlow 2.4-era dependencies do not disturb body-pose inference.

This Docker image is TensorFlow-only for Uplift-Upsample inference. It does not install PyTorch, MMPose, RTMPose, or MediaPipe.

## Required Assets

Place the official pretrained Human3.6M weight here:

```text
external/uplift-upsample-3dhpe/models/h36m_351.h5
```

The prepared RTMPose input should already exist at:

```text
assets/smoke/vedio_1_uplift_input_debug.npz
```

## Build

```bash
scripts/docker_build_uplift.sh
```

Equivalent command:

```bash
docker build --platform linux/amd64 -f docker/uplift/Dockerfile -t bpt-uplift:tf24 .
```

## Run Smoke Inference

```bash
scripts/docker_run_uplift_smoke.sh
```

Expected output:

```text
assets/smoke/vedio_1_uplift_3d_output_debug.npz
```

The script exits cleanly if TensorFlow or `h36m_351.h5` is unavailable. It should only report `inference_ran=True` after the model loads and predicts.
