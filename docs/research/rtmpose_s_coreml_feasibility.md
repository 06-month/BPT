# RTMPose-s Core ML Feasibility

## Scope

This document covers RTMPose-s forward-only Core ML feasibility as a 2D pose front-end candidate for the already-converted MotionAGFormer-XS lifter. It does not convert RTMPose preprocessing, detector logic, video I/O, app feedback logic, or the MotionAGFormer-XS package.

## Assets

- Config: `models/rtmpose/rtmpose-s_8xb256-420e_coco-256x192.py`
- Checkpoint: `models/rtmpose/rtmpose-s_coco.pth`
- Target smoke video: `assets/smoke/vedio_1.mp4`
- Forward-only Core ML target: `assets/coreml/rtmpose_s_forward.mlpackage`

## Model Boundary

The Core ML export target is only:

```text
input_image [1, 3, 256, 192]
-> RTMPose-s model.extract_feat
-> RTMPose-s model.head
-> simcc_x [1, 17, 384]
-> simcc_y [1, 17, 512]
```

This is the neural-network tensor forward. It is not a complete RTMPose pipeline.

## Current Result

- RTMPose-s PyTorch forward works on CPU.
- RTMPose-s forward-only Core ML conversion works in fp16.
- Generated Core ML package: `assets/coreml/rtmpose_s_forward.mlpackage`
- Core ML prediction works on macOS.
- Raw SimCC output comparison against the PyTorch trace:
  - `simcc_x` max abs diff: `0.026526659727096558`
  - `simcc_x` mean abs diff: `0.004829990677535534`
  - `simcc_y` max abs diff: `0.025540471076965332`
  - `simcc_y` mean abs diff: `0.004814458545297384`
- macOS Core ML forward-only steady-state benchmark:
  - mean: `1.6382437600987032 ms`
  - median: `1.633832995139528 ms`
  - p90: `1.7179205024149269 ms`
  - p95: `1.7306624889897648 ms`
  - FPS: `610.4097719497803`
- ANE placement is not verified.

## Outside Core ML

The following remain outside the Core ML graph:

- Person detector or person bbox selection.
- Full-frame bbox policy currently used by `RTMPoseRunner`.
- Bbox center/scale calculation.
- TopdownAffine crop/resize to `192x256`.
- BGR to RGB conversion.
- Mean/std normalization.
- SimCC decode from logits to COCO17 keypoints.
- Inverse affine transform from model-input coordinates to original image coordinates.
- COCO17 to H36M17 conversion.
- 2D coordinate normalization for MotionAGFormer.
- 27-frame ring buffer feeding MotionAGFormer-XS.

## Detector Status

The existing project `RTMPoseRunner` calls MMPose `inference_topdown` and passes a full-image bbox derived from the input image size. No detector is included in the RTMPose-s Core ML forward package.

## Swift/iOS Work Required

An iOS implementation would need to provide:

- A person bbox source, or a deliberate full-frame bbox policy.
- Top-down affine crop/resize matching MMPose.
- RGB conversion and ImageNet-style mean/std normalization.
- `MLMultiArray` input creation in `[1, 3, 256, 192]` order.
- Core ML forward call.
- SimCC argmax/optional DARK-style refinement policy matching the config.
- Conversion from SimCC indices to input-image coordinates using split ratio `2.0`.
- Inverse affine mapping back to original image coordinates.
- COCO17 keypoint confidence extraction.
- COCO17 to H36M17 conversion and MotionAGFormer normalization.
- A 27-frame ring buffer before calling MotionAGFormer-XS Core ML.

## Connection To MotionAGFormer-XS

Expected later flow:

```text
RTMPose-s COCO17 2D
-> COCO17 to H36M17 conversion
-> normalize_motionagformer_2d
-> 27-frame ring buffer
-> MotionAGFormer-XS Core ML lifter
```

## Current Blockers

- ANE placement is unverified until physical-device profiling.
- The forward-only package does not remove the need to reimplement RTMPose top-down preprocessing and SimCC decoding in Swift/iOS.
- End-to-end latency is still unknown because detector/bbox selection, crop/affine preprocessing, SimCC decode, COCO17 to H36M17 conversion, and MotionAGFormer buffering are not benchmarked together.

## Next Exact Step

If forward conversion and macOS Core ML smoke pass, build a minimal iPhone profiling target for `rtmpose_s_forward.mlpackage`, run fixed input latency tests, and use Instruments/Xcode profiling to verify CPU/GPU/ANE placement.
