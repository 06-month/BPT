COREML.md

Purpose

This document defines the Core ML / Apple Neural Engine investigation policy for the current pose-feedback project.

Agents must use this document as the task-level reference when working on Core ML conversion, Apple Neural Engine feasibility, or iPhone on-device inference experiments.

If this document conflicts with AGENTS.md, follow the narrower task scope in this document for Core ML-related tasks only.

⸻

1. Current project context

The project is an on-device real-time exercise pose feedback system.

Current relevant components:

* Body pose candidates:
    * Apple Vision 3D Body Pose
    * RTMPose / YOLO-style 2D pose models
    * MotionAGFormer as a 2D-to-3D lifter
* Hand pose candidates:
    * MediaPipe Hands
    * Apple Vision Hand Pose
* Feedback logic:
    * Coordinate-safe feature extraction
    * Validity gate
    * ResultHolder
    * FeedbackEngine

The Core ML investigation is not meant to implement final exercise scoring. It is meant to determine whether a lightweight pose/lifter stack can run on Apple devices efficiently enough for future iOS deployment.

⸻

2. Current verified facts

2.1 Apple Vision 3D Body

Apple Vision 3D Body Pose has been verified to run end-to-end on macOS 26.5 arm64 CLI.

Verified paths:

* VNDetectHumanBodyPose3DRequest
* DetectHumanBodyPose3DRequest

Verified outputs:

* 17-joint 3D body pose
* Root-relative, meter-scale estimated pose
* Not mocap-grade absolute 3D
* No hand/finger joints

Verified smoke results:

* pushup_1.mp4: 159 / 171 frames detected, 93.0% detection
* vedio_1.mp4: 240 / 240 frames detected, 100% detection
* macOS CLI throughput: about 11 FPS end-to-end

Important limitation:

* Apple Vision 3D Body is useful as a body-frame source.
* It cannot directly compute wrist bend or palm rotation because it does not output hand/finger landmarks.

2.2 MotionAGFormer-B / Base

Previously tested configuration:

* Source 2D: RTMPose-s
* Lifter: MotionAGFormer-B / base
* Config: external/MotionAGFormer/configs/h36m/MotionAGFormer-base.yaml
* Checkpoint: external/MotionAGFormer/checkpoint/motionagformer-b-h36m.pth.tr
* Window length: 243 frames

Measured performance on Mac CPU:

* lifter only: about 1016 ms/frame, about 0.98 FPS
* full pipeline from JSONL: about 1311 ms/frame, about 0.76 FPS

Conclusion:

* MotionAGFormer-B is not real-time feasible on the tested Mac CPU.
* This does not automatically eliminate smaller MotionAGFormer variants.

2.3 MotionAGFormer-XS / S assets

Downloaded checkpoints:

* XS checkpoint: external/MotionAGFormer/checkpoint/motionagformer-xs-h36m.pth.tr
* S checkpoint: external/MotionAGFormer/checkpoint/motionagformer-s-h36m.pth.tr

Configs:

* XS config: external/MotionAGFormer/configs/h36m/MotionAGFormer-xsmall.yaml
* S config: external/MotionAGFormer/configs/h36m/MotionAGFormer-small.yaml

Expected shapes:

* XS input: [B, 27, 17, 3]
* XS output: [B, 27, 17, 3]
* S input: [B, 81, 17, 3]
* S output: [B, 81, 17, 3]

Readme-level model scale:

* MotionAGFormer-XS:
    * 27 frames
    * 2.2M parameters
    * 1.0G MACs
* MotionAGFormer-S:
    * 81 frames
    * 4.8M parameters
    * 6.6G MACs

Current status:

* Asset check passes.
* PyTorch inference and Core ML conversion still need to be verified.

⸻

3. Core ML investigation principles

3.1 Separate feasibility stages

Do not attempt to convert the entire system at once.

Use this order:

1. PyTorch smoke inference
2. PyTorch runtime benchmark
3. Fixed-shape Core ML conversion
4. macOS Core ML prediction smoke test
5. PyTorch vs Core ML numerical comparison
6. iPhone physical-device latency test
7. Instruments check for CPU / GPU / ANE execution
8. Only then consider integration with RTMPose or feedback logic

3.2 Core ML conversion does not imply ANE execution

Agents must not claim Neural Engine success just because .mlpackage generation succeeds.

The correct distinction is:

* Core ML conversion success:
    * .mlpackage or .mlmodel is produced
    * model can be loaded through Core ML
* Core ML prediction success:
    * the converted model can run inference
* ANE success:
    * Instruments / Xcode profiling confirms Neural Engine execution with minimal CPU/GPU fallback

Never write:

The model runs on the Neural Engine.

unless it has been verified on a physical Apple device or through reliable profiling.

Correct wording:

The model was converted to Core ML and runs through Core ML. ANE placement is unverified until device profiling.

3.3 Fixed shape first

For initial conversion, always use fixed input shapes.

Required first shapes:

* MotionAGFormer-XS:
    * [1, 27, 17, 3]
* MotionAGFormer-S:
    * [1, 81, 17, 3]

Do not start with dynamic shape export.

3.4 Convert XS before S

Priority order:

1. MotionAGFormer-XS
2. MotionAGFormer-S
3. MotionAGFormer-M/B only if explicitly requested
4. RTMPose Core ML only after lifter feasibility is known

Reason:

* XS is the most plausible mobile lifter candidate.
* S is a quality/speed trade-off candidate.
* B was already too slow on CPU.
* RTMPose conversion introduces image-model and postprocessing complexity, so it should not be mixed with lifter conversion debugging.

⸻

4. MotionAGFormer Core ML conversion plan

4.1 Stage A: PyTorch smoke inference

Before Core ML conversion, verify that the PyTorch model runs.

Required script behavior:

* Load official config/checkpoint.
* Load prepared input NPZ.
* Use lookahead5_windows first.
* Run a small number of windows.
* Save output NPZ.
* Print:
    * input shape
    * output shape
    * output min / max / mean
    * model load status
    * mean ms/frame
    * median ms/frame
    * FPS

Recommended output paths:

* assets/smoke/motionagformer_xs_s_test/outputs/vedio_1_motionagformer_xs_lookahead5.npz
* assets/smoke/motionagformer_xs_s_test/outputs/vedio_1_motionagformer_s_lookahead5.npz

4.2 Stage B: Export MotionAGFormer-XS to Core ML

Add script:

* scripts/export_motionagformer_xs_coreml.py

Required behavior:

* Load XS config/checkpoint.
* Set model to eval mode.
* Wrap model if needed so forward accepts one tensor only.
* Use dummy tensor:
    * torch.zeros(1, 27, 17, 3)
* Try torch.jit.trace first.
* Convert using coremltools.
* Save:
    * assets/coreml/motionagformer_xs.mlpackage

Input name:

* input_2d_sequence

Output name:

* pred_3d_sequence

Precision policy:

* Try fp16 first if supported.
* If fp16 fails, retry fp32.
* Report which precision succeeded.

Failure policy:

* If conversion fails, write exact exception and unsupported op information to:
    * assets/coreml/motionagformer_xs_coreml_conversion_failure.txt

Do not silently skip conversion failure.

4.3 Stage C: Core ML smoke test

Add script:

* scripts/smoke_motionagformer_xs_coreml.py

Required behavior:

* Load assets/coreml/motionagformer_xs.mlpackage.
* Load a real window from:
    * assets/smoke/motionagformer_xs_s_test/inputs/vedio_1_motionagformer_xs_input.npz
* Run the same input through:
    * PyTorch XS model
    * Core ML XS model
* Compare outputs.

Report:

* PyTorch output shape
* Core ML output shape
* max absolute difference
* mean absolute difference
* output min / max / mean
* prediction latency if easy to measure

4.4 Stage D: Repeat for MotionAGFormer-S

Only start S conversion if XS conversion and smoke prediction succeed.

Required shape:

* [1, 81, 17, 3]

Recommended output:

* assets/coreml/motionagformer_s.mlpackage

⸻

5. RTMPose Core ML policy

Do not start RTMPose conversion until MotionAGFormer-XS Core ML status is known.

RTMPose conversion has extra complexity:

* image input preprocessing
* detector/crop stage
* SimCC decoding
* keypoint postprocessing
* model config/checkpoint compatibility
* app-side Swift/C++ postprocess implementation

When RTMPose conversion is eventually attempted, the agent must document:

* exact model size: s / m / l / x
* input size
* output tensor shapes
* SimCC decode logic
* whether detector is included or separate
* whether Core ML output matches PyTorch output
* whether postprocess runs outside Core ML

Do not claim RTMPose is fully converted if only the model forward was converted.

⸻

6. Apple Neural Engine validation plan

Core ML models must be validated on a physical Apple device.

Required device test stages:

1. Minimal Xcode app with no camera
    * Load .mlpackage.
    * Run fixed dummy or bundled tensor input.
    * Measure repeated prediction latency.
2. Instruments / Xcode profiling
    * Determine CPU / GPU / ANE placement.
    * Check whether unsupported ops cause CPU fallback.
3. Streaming keypoint input test
    * Feed a ring buffer of [T, 17, 3] 2D keypoints.
    * Run lifter at target frequency.
4. End-to-end test
    * Camera frame input
    * 2D pose model
    * keypoint buffer
    * 3D lifter
    * feedback loop

Metrics to record:

* model load time
* first inference latency
* steady-state median latency
* p90 / p95 latency
* FPS
* memory footprint
* thermal behavior
* CPU / GPU / ANE utilization

⸻

7. Expected risk areas

7.1 Transformer conversion risk

MotionAGFormer contains transformer-like operations. Conversion or ANE placement may fail due to:

* attention blocks
* LayerNorm
* matmul/einsum variants
* dynamic reshape/transpose
* gather/scatter
* unsupported indexing
* non-static shapes

Agents must report exact failing operations when possible.

7.2 Output equivalence risk

Even if Core ML conversion succeeds, outputs may differ from PyTorch due to:

* fp16 precision
* operator implementation differences
* unsupported op replacement
* tracing path issues

Always compare PyTorch vs Core ML outputs.

7.3 Performance risk

A small model can still be slow if it falls back to CPU.

Agents must not infer iPhone performance from:

* model file size alone
* parameter count alone
* MACs alone
* macOS CPU performance alone

Physical device measurement is required.

⸻

8. File organization

Use these paths for Core ML artifacts:

assets/coreml/
├─ motionagformer_xs.mlpackage
├─ motionagformer_s.mlpackage
├─ motionagformer_xs_coreml_conversion_failure.txt
├─ motionagformer_s_coreml_conversion_failure.txt
├─ motionagformer_xs_coreml_smoke.json
└─ motionagformer_s_coreml_smoke.json

Use these paths for MotionAGFormer XS/S smoke artifacts:

assets/smoke/motionagformer_xs_s_test/
├─ inputs/
├─ outputs/
├─ videos/
├─ csv/
├─ plots/
└─ logs/

Do not overwrite prior MotionAGFormer-B, Apple Vision, RTMPose, or Uplift outputs.

⸻

9. Required report format

For any Core ML task, report in this structure:

Summary:
- what was tested
- whether PyTorch inference works
- whether Core ML conversion works
- whether Core ML prediction works
Artifacts:
- paths to generated .mlpackage files
- paths to smoke JSON/NPZ logs
- paths to failure logs if any
Shapes:
- input tensor shape
- PyTorch output shape
- Core ML output shape
Numerical equivalence:
- max_abs_diff
- mean_abs_diff
- precision used: fp16 or fp32
Runtime:
- PyTorch latency
- Core ML macOS latency if measured
- iPhone latency if measured
- ANE/GPU/CPU placement if profiled
Conclusion:
- keep / reject / needs device profiling
- next exact step
Tests:
- unittest result
- compileall result

⸻

10. Current next recommended task

The next Core ML-related task should be:

Run MotionAGFormer-XS PyTorch smoke inference on vedio_1 lookahead5 input, then convert MotionAGFormer-XS to Core ML with fixed shape [1, 27, 17, 3], run Core ML smoke prediction on macOS, and compare PyTorch vs Core ML outputs.

Do not convert RTMPose yet.

Do not integrate with feedback logic yet.

Do not claim Neural Engine success until physical-device profiling is performed.