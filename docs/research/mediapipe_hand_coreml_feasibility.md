# MediaPipe Hand Core ML Feasibility

## Scope

This note covers the MediaPipe hand branch only. RTMPose-s Core ML and
MotionAGFormer-XS Core ML are already separate assets and are not modified here.

The current MediaPipe asset is:

- `assets/mediapipe/hand_landmarker.task`

That file packages two TFLite neural-network models:

- `hand_detector.tflite`
- `hand_landmarks_detector.tflite`

## What Core ML Could Contain

Only the neural-network forwards are plausible Core ML conversion targets:

- palm/hand detector tensor forward
- hand landmark tensor forward

This would not convert the full MediaPipe Tasks graph.

## What Remains Outside Core ML

- RTMPose wrist-based crop generation
- crop clamping, resize, and normalization
- detector output decoding and ROI tracking if the detector model is used
- landmark output decode to 21 image landmarks
- crop-local to original-frame coordinate mapping
- MediaPipe world landmark interpretation
- wrist-relative 3D hand attachment to MotionAGFormer body wrists
- left/right assignment from RTMPose side ownership

## Current Local Conversion Status

The local `bpt-coreml` environment has `coremltools 9.0`, but it does not expose
a direct TFLite conversion path. The conversion probe intentionally writes a
failure log instead of silently skipping this.

Run:

```bash
conda run -n bpt-coreml python scripts/inspect_mediapipe_hand_task_coreml_path.py
conda run -n bpt-coreml python scripts/export_mediapipe_hand_tflite_coreml.py
```

Expected failure log if direct conversion is unavailable:

- `assets/coreml/mediapipe_hand_coreml_conversion_failure.txt`

## Next Step

Use one of these routes:

1. Obtain TensorFlow SavedModel or ONNX versions of the MediaPipe hand detector
   and landmark models, then convert those fixed-shape forwards to Core ML.
2. Add a dedicated TFLite-to-CoreML bridge in an isolated conversion environment.
3. Keep MediaPipe Tasks for the hand branch on iOS while RTMPose-s and
   MotionAGFormer-XS run through Core ML.

Core ML conversion success would still not prove Neural Engine execution.
Physical-device Instruments profiling is required before claiming ANE usage.
