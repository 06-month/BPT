# Minimal iOS Core ML Pose Profiling

## Purpose

Profile the existing Core ML pose models on a physical iPhone with synthetic inputs only.

Models:

- `assets/coreml/rtmpose_s_forward.mlpackage`
- `assets/coreml/motionagformer_xs.mlpackage`

This scaffold does not include camera input, exercise scoring, rep phase detection, or feedback logic. Set `ane_verified=false` until Instruments confirms Neural Engine execution on a physical device.

## Xcode Setup

1. Create a new Xcode iOS app target.
2. Add both `.mlpackage` files to the app bundle target membership:
   - `rtmpose_s_forward.mlpackage`
   - `motionagformer_xs.mlpackage`
3. Set the deployment target to iOS 16 or newer, matching the ML Program packages.
4. Add these Swift files to the app target:
   - `CoreMLPoseBenchmark.swift`
   - `PosePreprocess.swift`
   - `SimCCDecoder.swift`
   - `PoseCoordinateTransforms.swift`
   - `MotionAGFormerInputBuilder.swift`
   - `CoreMLPosePipelineBenchmark.swift`
5. Call `CoreMLPoseBenchmark.runAll()` from a button action, `Task`, or temporary debug entry point for synthetic model-forward benchmarking.
6. Call `CoreMLPosePipelineBenchmark.runSyntheticEndToEnd()` for the no-camera synthetic preprocessing/postprocessing path.
7. Run on a physical iPhone, not the simulator.

## Benchmark Modes

The Swift scaffold runs:

- `rtmpose_s_only`
- `motionagformer_xs_only`
- `rtmpose_s_plus_motionagformer_xs_sequential`

Each mode uses:

- warmup: `10`
- measured iterations: `100`
- prediction-only timing via `CACurrentMediaTime()`

## Synthetic End-to-End No-Camera Mode

`CoreMLPosePipelineBenchmark.runSyntheticEndToEnd()` runs:

1. Synthetic `UIImage` creation before timing.
2. Full-image RTMPose bbox policy.
3. Top-down affine preprocessing to `[1, 3, 256, 192]`.
4. RGB mean/std normalization.
5. RTMPose-s Core ML prediction.
6. SimCC decode for `simcc_x [1, 17, 384]` and `simcc_y [1, 17, 512]`.
7. Inverse affine mapping back to source image pixels.
8. COCO17 to H36M17 conversion.
9. MotionAGFormer screen normalization with confidence in channel 3.
10. 27-frame lookahead5 input build.
11. MotionAGFormer-XS Core ML prediction.
12. Target-frame 3D output selection.

The entry point prints JSON-like timing for:

- `rtmpose_preprocess_ms`
- `rtmpose_coreml_ms`
- `simcc_decode_ms`
- `inverse_affine_ms`
- `coco_to_h36m_ms`
- `motion_input_build_ms`
- `motionagformer_coreml_ms`
- `motion_output_select_ms`
- `total_no_camera_ms`

This mode still uses synthetic still-image data and does not include camera capture, detector bbox selection, video rendering, feedback logic, or ANE verification.

## Inputs

`CoreMLPoseBenchmark.runAll()` uses synthetic zero-filled model inputs:

- RTMPose-s: `[1, 3, 256, 192]`, input name `input_image`
- MotionAGFormer-XS: `[1, 27, 17, 3]`, input name `input_2d_sequence`

`CoreMLPosePipelineBenchmark.runSyntheticEndToEnd()` uses a deterministic synthetic `UIImage` and executes the scaffolded preprocessing/postprocessing path. No camera frames are used.

## Measurements

Copy these values from the Xcode console:

- device model
- iOS version
- thermal state
- benchmark mode
- model load time in ms
- first prediction time in ms
- mean / median / p90 / p95 latency
- FPS
- `ane_verified=false`

For `CoreMLPosePipelineBenchmark.runSyntheticEndToEnd()`, also copy the per-stage latency dictionary and any console errors from the Xcode log.

## Instruments

Use Xcode Instruments on the physical iPhone to verify:

- ANE usage
- GPU usage
- CPU fallback
- thermal state during repeated predictions

Do not claim Neural Engine success unless Instruments or Xcode profiling confirms it.
