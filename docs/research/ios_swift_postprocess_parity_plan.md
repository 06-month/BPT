# iOS Swift Postprocess Parity Plan

## Purpose

This note tracks the no-camera Swift scaffold for RTMPose-s Core ML plus MotionAGFormer-XS Core ML on a physical iPhone. It is for synthetic preprocessing/postprocessing latency and code-path validation only.

ANE placement remains unverified until Instruments confirms it on device.

## Python Parity Targets

Swift files under `tools/ios_coreml_pose_minimal/` mirror these Python pipeline pieces:

- `PosePreprocess.swift`: `preprocess_rtmpose_full_image`, `fix_aspect_ratio`, `get_warp_matrix`, RGB conversion, mean/std normalization.
- `SimCCDecoder.swift`: `decode_simcc` for `simcc_x [1, 17, 384]` and `simcc_y [1, 17, 512]`.
- `PoseCoordinateTransforms.swift`: `apply_affine_to_points`, COCO17 to H36M17 conversion, MotionAGFormer screen normalization.
- `MotionAGFormerInputBuilder.swift`: 27-frame lookahead5 input building and target output frame selection.
- `CoreMLPosePipelineBenchmark.swift`: stage-level synthetic end-to-end timing similar to the macOS Python prototype.

## Tensor Shapes

- RTMPose input: `[1, 3, 256, 192]`, input name `input_image`.
- RTMPose outputs: `simcc_x [1, 17, 384]`, `simcc_y [1, 17, 512]`.
- Decoded COCO17 keypoints: `[17, 3]` as `x, y, confidence`.
- MotionAGFormer input: `[1, 27, 17, 3]`, input name `input_2d_sequence`.
- MotionAGFormer output: `[1, 27, 17, 3]`, output name `pred_3d_sequence`.
- Selected MotionAGFormer output: `[17, 3]` from temporal index `21` for lookahead5.

## Current Limitations

- Input is a deterministic synthetic still image, not camera frames.
- Bbox policy is full image only.
- No person detector is included.
- The affine sampler is a Swift CPU scaffold, not an optimized Accelerate or Metal implementation.
- SimCC decode is argmax-only and mirrors the current Python smoke path.
- No temporal smoothing, feedback logic, scoring, or rep phase detection is included.
- No Swift vs Python numerical parity artifact has been generated yet.
- ANE, GPU, and CPU placement are not verified by this scaffold.

## Later Python vs Swift Comparison

Use a bundled still frame or exported input image and compare:

- RTMPose preprocessed tensor max and mean absolute difference.
- SimCC decoded input-coordinate keypoints.
- Inverse-affine image-coordinate COCO17 keypoints.
- H36M17 normalized MotionAGFormer input frame.
- Full `[1, 27, 17, 3]` MotionAGFormer input window.
- Selected `[17, 3]` MotionAGFormer output.

The expected comparison source is the macOS Python pipeline in `scripts/run_coreml_rtmpose_s_motionagformer_xs_pipeline.py`.

## Next Step

Run `CoreMLPosePipelineBenchmark.runSyntheticEndToEnd()` on a physical iPhone, copy the JSON-like latency output, and profile the same run in Instruments to determine CPU, GPU, and ANE placement. Camera integration should wait until the synthetic Swift path is stable and parity gaps are understood.
