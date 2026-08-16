# Minimal MotionAGFormer-XS Core ML iPhone Profiling

## Purpose

Test `assets/coreml/motionagformer_xs.mlpackage` on a physical iPhone and measure real device latency and execution placement. This is a standalone profiling target only; it does not integrate MotionAGFormer into the app feedback pipeline.

## Required File

- `assets/coreml/motionagformer_xs.mlpackage`

Optional reproducible input:

- `assets/coreml/motionagformer_xs_test_input.npy`
- `assets/coreml/motionagformer_xs_test_input.json`

## Tensor Shapes

- Input: `[1, 27, 17, 3]`
- Output: `[1, 27, 17, 3]`
- Input name: `input_2d_sequence`
- Output name: `pred_3d_sequence`

## Xcode App Setup

1. Create a minimal iOS app target in Xcode.
2. Add `motionagformer_xs.mlpackage` to the app bundle target membership.
3. Set the deployment target to match the model package target, currently iOS 16 or newer.
4. Run on a physical iPhone, not the simulator.
5. Keep the app minimal: no camera, no RTMPose, no feedback logic.

## Minimal Swift Outline

```swift
import CoreML
import Foundation
import UIKit

struct LatencyStats {
    let median: Double
    let p90: Double
    let p95: Double
}

func percentile(_ sorted: [Double], _ p: Double) -> Double {
    let index = (Double(sorted.count - 1) * p) / 100.0
    let lower = Int(index)
    let upper = min(lower + 1, sorted.count - 1)
    let weight = index - Double(lower)
    return sorted[lower] * (1.0 - weight) + sorted[upper] * weight
}

func summarize(_ values: [Double]) -> LatencyStats {
    let sorted = values.sorted()
    return LatencyStats(
        median: percentile(sorted, 50),
        p90: percentile(sorted, 90),
        p95: percentile(sorted, 95)
    )
}

func makeInput() throws -> MLMultiArray {
    let array = try MLMultiArray(shape: [1, 27, 17, 3], dataType: .float32)
    for index in 0..<array.count {
        array[index] = 0.0
    }
    return array
}

func runProfile() throws {
    let config = MLModelConfiguration()
    config.computeUnits = .all

    let loadStart = CFAbsoluteTimeGetCurrent()
    let modelURL = Bundle.main.url(forResource: "motionagformer_xs", withExtension: "mlpackage")!
    let model = try MLModel(contentsOf: modelURL, configuration: config)
    let modelLoadMs = (CFAbsoluteTimeGetCurrent() - loadStart) * 1000.0

    let inputArray = try makeInput()
    let provider = try MLDictionaryFeatureProvider(dictionary: [
        "input_2d_sequence": MLFeatureValue(multiArray: inputArray)
    ])

    let firstStart = CFAbsoluteTimeGetCurrent()
    _ = try model.prediction(from: provider)
    let firstPredictionMs = (CFAbsoluteTimeGetCurrent() - firstStart) * 1000.0

    for _ in 0..<10 {
        _ = try model.prediction(from: provider)
    }

    var times: [Double] = []
    for _ in 0..<100 {
        let start = CFAbsoluteTimeGetCurrent()
        let output = try model.prediction(from: provider)
        _ = output.featureValue(for: "pred_3d_sequence")?.multiArrayValue
        times.append((CFAbsoluteTimeGetCurrent() - start) * 1000.0)
    }

    let stats = summarize(times)
    print("device_model: \(UIDevice.current.model)")
    print("iOS_version: \(UIDevice.current.systemVersion)")
    print("model_load_ms: \(modelLoadMs)")
    print("first_prediction_ms: \(firstPredictionMs)")
    print("median_ms: \(stats.median)")
    print("p90_ms: \(stats.p90)")
    print("p95_ms: \(stats.p95)")
    print("thermal_state: \(ProcessInfo.processInfo.thermalState.rawValue)")
}
```

Use the bundled JSON or NPY export if you want the exact same input window as the macOS smoke test. Otherwise, zero input is enough for latency-only profiling.

## Instruments

1. Run the app on a physical iPhone.
2. Open Xcode Instruments and attach to the app.
3. Use relevant Core ML, CPU, GPU, and system trace instruments available in the installed Xcode version.
4. Record whether Neural Engine, GPU, or CPU executes the model.
5. Check for CPU fallback and thermal changes during repeated predictions.

Do not report Neural Engine success unless Instruments or Xcode profiling confirms it on the physical device.

## Required Logs To Copy Back

- Device model
- iOS version
- Model load time
- First prediction time
- Median, p90, and p95 prediction time
- ANE/GPU/CPU placement
- Thermal state, if available
