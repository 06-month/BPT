# Core ML RTMPose-s to MotionAGFormer-XS Pipeline

## Scope

This is a macOS Python prototype for measuring an end-to-end Core ML pose stack:

```text
RTMPose-s Core ML forward
-> Python preprocessing/postprocessing
-> COCO17 2D
-> COCO17 to H36M17
-> 27-frame lookahead5 window
-> MotionAGFormer-XS Core ML
-> 3D joints
```

It is not an iOS app and does not modify Apple Vision, MediaPipe, WristEstimator, FeedbackEngine, Uplift, or exercise scoring logic.

## Inside Core ML

- RTMPose-s neural-network forward:
  - input: `input_image [1, 3, 256, 192]`
  - outputs: `simcc_x [1, 17, 384]`, `simcc_y [1, 17, 512]`
- MotionAGFormer-XS lifter:
  - input: `input_2d_sequence [1, 27, 17, 3]`
  - output: `pred_3d_sequence [1, 27, 17, 3]`

## Outside Core ML

- Video frame decode.
- Full-image bbox policy.
- Bbox center/scale and MMPose-style TopdownAffine.
- RGB conversion and mean/std normalization.
- SimCC decode.
- Inverse affine mapping to original image pixels.
- COCO17 to H36M17 conversion.
- MotionAGFormer 2D normalization.
- 27-frame lookahead window construction.
- Rendering and video writing.

## Current MacOS Benchmark

Results are written by:

```text
scripts/run_coreml_rtmpose_s_motionagformer_xs_pipeline.py
```

Primary benchmark artifacts:

- `assets/coreml_pipeline/logs/vedio_1_coreml_e2e_benchmark.json`
- `assets/coreml_pipeline/csv/vedio_1_coreml_e2e_benchmark.csv`

The realtime decision should use `total_no_render`, because rendering/video writing is not part of the inference pipeline.

Current `assets/smoke/vedio_1.mp4` run:

- Frames processed: `240`
- Bbox policy: `full_image`
- Temporal latency: `5` frames
- `total_no_render`: mean `12.7309 ms`, median `10.8531 ms`, p90 `16.4722 ms`, p95 `17.7241 ms`
- FPS without rendering: `78.5489`
- FPS with rendering: `62.5235`
- 20 FPS without rendering: yes
- 30 FPS without rendering: yes
- RTMPose-s Core ML: mean `2.5622 ms`, median `2.5583 ms`
- MotionAGFormer-XS Core ML: mean `7.9271 ms`, median `5.9937 ms`
- SimCC decode: mean `0.0487 ms`, median `0.0411 ms`

## Quality Check

The side-by-side video was generated at:

- `assets/coreml_pipeline/videos/vedio_1_coreml_2d_3d_side_by_side.mp4`

The 2D skeleton is visually coherent on sampled frames, and the 3D panel is populated. The comparison against the existing MMPose RTMPose-s JSONL shows measurable but not catastrophic drift:

- Frames compared: `240`
- Overall mean pixel error: `16.4127 px`
- Overall median pixel error: `9.375 px`
- Overall p90 pixel error: `30.0146 px`
- Upper-body valid ratio: `1.0`
- Lower-body valid ratio: `0.9917`
- Full-body valid ratio: `0.35`

Largest per-joint mean errors were on `nose` and `left_knee`, which suggests the forward-only Python decode/preprocess path is usable for throughput testing but still needs parity work before app integration.

## Limitations

- The first prototype uses a full-image bbox. This is simple and reproducible but may hurt accuracy when the person is not tightly framed.
- No detector/person bbox model is included.
- SimCC decode and affine math are Python implementations and still need Swift parity validation.
- ANE placement is not verified.
- iPhone latency is not measured.
- This does not prove the full app pipeline is complete.

## Next Exact Step

Run physical iPhone profiling for both Core ML packages and implement a minimal Swift parity target for RTMPose preprocessing and SimCC decode. Only after that should the stack be considered for app integration.
