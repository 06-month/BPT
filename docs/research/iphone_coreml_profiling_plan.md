# iPhone Core ML Profiling Plan

## Purpose

Measure the existing Core ML pose models on a physical iPhone and verify execution placement with Xcode Instruments. This plan is synthetic-input profiling only.

Models:

- `assets/coreml/rtmpose_s_forward.mlpackage`
- `assets/coreml/motionagformer_xs.mlpackage`

## Current Scaffold

- `tools/ios_coreml_pose_minimal/README.md`
- `tools/ios_coreml_pose_minimal/CoreMLPoseBenchmark.swift`

## Benchmark Modes

Run all three modes:

- RTMPose-s only
- MotionAGFormer-XS only
- RTMPose-s + MotionAGFormer-XS sequential

Each mode should use:

- warmup: `10`
- iterations: `100`
- prediction-only timing via `CACurrentMediaTime()`
- `ane_verified=false` in logs until Instruments proves otherwise

## Values To Copy Back

For each mode, record:

- device model
- iOS version
- thermal state
- model load time
- first prediction time
- mean latency
- median latency
- p90 latency
- p95 latency
- FPS
- ANE/GPU/CPU placement from Instruments
- notes on CPU fallback or thermal throttling

## Instruments Checklist

1. Run on a physical iPhone, not simulator.
2. Profile the app from Xcode Instruments.
3. Inspect Core ML execution and system utilization.
4. Record whether the Neural Engine is used.
5. Record GPU use and CPU fallback.
6. Repeat after the device is thermally stable if results look inconsistent.

## Not Included Yet

- Camera input.
- RTMPose crop/affine preprocessing.
- RTMPose SimCC decoding.
- COCO17 to H36M17 conversion.
- 27-frame streaming ring buffer.
- Exercise feedback logic.

## Next Exact Step

Create the minimal Xcode app target, add the two `.mlpackage` files and `CoreMLPoseBenchmark.swift`, run on a physical iPhone, and copy the JSON-like console output plus Instruments placement notes back into the project logs.
