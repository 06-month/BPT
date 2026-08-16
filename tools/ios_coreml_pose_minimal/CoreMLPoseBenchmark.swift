import CoreML
import Foundation
import QuartzCore
import UIKit

enum CoreMLPoseBenchmarkError: Error {
    case missingModel(String)
}

struct CoreMLPoseLatencyStats {
    let mean: Double
    let median: Double
    let p90: Double
    let p95: Double
    let min: Double
    let max: Double
    let fps: Double
}

struct CoreMLPoseBenchmarkResult {
    let mode: String
    let deviceModel: String
    let systemVersion: String
    let thermalState: String
    let modelLoadMs: [String: Double]
    let firstPredictionMs: Double
    let warmupCount: Int
    let iterationCount: Int
    let stats: CoreMLPoseLatencyStats
    let aneVerified: Bool

    func printJSONLike() {
        print("""
        {
          "mode": "\(mode)",
          "device_model": "\(deviceModel)",
          "ios_version": "\(systemVersion)",
          "thermal_state": "\(thermalState)",
          "model_load_ms": \(formatDictionary(modelLoadMs)),
          "first_prediction_ms": \(firstPredictionMs),
          "warmup_count": \(warmupCount),
          "iteration_count": \(iterationCount),
          "mean_ms": \(stats.mean),
          "median_ms": \(stats.median),
          "p90_ms": \(stats.p90),
          "p95_ms": \(stats.p95),
          "min_ms": \(stats.min),
          "max_ms": \(stats.max),
          "fps": \(stats.fps),
          "ane_verified": \(aneVerified)
        }
        """)
    }

    private func formatDictionary(_ values: [String: Double]) -> String {
        let items = values.keys.sorted().map { key in
            "\"\(key)\": \(values[key] ?? 0.0)"
        }
        return "{\(items.joined(separator: ", "))}"
    }
}

final class CoreMLPoseBenchmark {
    static let warmupCount = 10
    static let iterationCount = 100

    static func runAll() {
        do {
            let rtmpose = try loadModel(named: "rtmpose_s_forward")
            let motion = try loadModel(named: "motionagformer_xs")

            try benchmarkRTMPoseOnly(rtmpose.model, modelLoadMs: rtmpose.loadMs).printJSONLike()
            try benchmarkMotionAGFormerOnly(motion.model, modelLoadMs: motion.loadMs).printJSONLike()
            try benchmarkSequential(
                rtmposeModel: rtmpose.model,
                motionModel: motion.model,
                rtmposeLoadMs: rtmpose.loadMs,
                motionLoadMs: motion.loadMs
            ).printJSONLike()
        } catch {
            print("CoreMLPoseBenchmark failed: \(type(of: error)) \(error)")
        }
    }

    static func benchmarkRTMPoseOnly(_ model: MLModel, modelLoadMs: Double) throws -> CoreMLPoseBenchmarkResult {
        let input = try makeRTMPoseInput()
        let provider = try MLDictionaryFeatureProvider(dictionary: [
            "input_image": MLFeatureValue(multiArray: input)
        ])
        return try benchmark(
            mode: "rtmpose_s_only",
            modelLoadMs: ["rtmpose_s_forward": modelLoadMs],
            predict: {
                let output = try model.prediction(from: provider)
                _ = output.featureValue(for: "simcc_x")?.multiArrayValue
                _ = output.featureValue(for: "simcc_y")?.multiArrayValue
            }
        )
    }

    static func benchmarkMotionAGFormerOnly(_ model: MLModel, modelLoadMs: Double) throws -> CoreMLPoseBenchmarkResult {
        let input = try makeMotionAGFormerInput()
        let provider = try MLDictionaryFeatureProvider(dictionary: [
            "input_2d_sequence": MLFeatureValue(multiArray: input)
        ])
        return try benchmark(
            mode: "motionagformer_xs_only",
            modelLoadMs: ["motionagformer_xs": modelLoadMs],
            predict: {
                let output = try model.prediction(from: provider)
                _ = output.featureValue(for: "pred_3d_sequence")?.multiArrayValue
            }
        )
    }

    static func benchmarkSequential(
        rtmposeModel: MLModel,
        motionModel: MLModel,
        rtmposeLoadMs: Double,
        motionLoadMs: Double
    ) throws -> CoreMLPoseBenchmarkResult {
        let rtmposeProvider = try MLDictionaryFeatureProvider(dictionary: [
            "input_image": MLFeatureValue(multiArray: try makeRTMPoseInput())
        ])
        let motionProvider = try MLDictionaryFeatureProvider(dictionary: [
            "input_2d_sequence": MLFeatureValue(multiArray: try makeMotionAGFormerInput())
        ])
        return try benchmark(
            mode: "rtmpose_s_plus_motionagformer_xs_sequential",
            modelLoadMs: [
                "rtmpose_s_forward": rtmposeLoadMs,
                "motionagformer_xs": motionLoadMs
            ],
            predict: {
                let rtmposeOutput = try rtmposeModel.prediction(from: rtmposeProvider)
                _ = rtmposeOutput.featureValue(for: "simcc_x")?.multiArrayValue
                _ = rtmposeOutput.featureValue(for: "simcc_y")?.multiArrayValue

                let motionOutput = try motionModel.prediction(from: motionProvider)
                _ = motionOutput.featureValue(for: "pred_3d_sequence")?.multiArrayValue
            }
        )
    }

    static func makeRTMPoseInput() throws -> MLMultiArray {
        try makeZeroArray(shape: [1, 3, 256, 192])
    }

    static func makeMotionAGFormerInput() throws -> MLMultiArray {
        try makeZeroArray(shape: [1, 27, 17, 3])
    }

    private static func makeZeroArray(shape: [Int]) throws -> MLMultiArray {
        let nsShape = shape.map { NSNumber(value: $0) }
        let array = try MLMultiArray(shape: nsShape, dataType: .float32)
        for index in 0..<array.count {
            array[index] = NSNumber(value: Float(0.0))
        }
        return array
    }

    private static func loadModel(named name: String) throws -> (model: MLModel, loadMs: Double) {
        let config = MLModelConfiguration()
        config.computeUnits = .all

        guard let url = modelURL(named: name) else {
            throw CoreMLPoseBenchmarkError.missingModel(name)
        }

        let start = CACurrentMediaTime()
        let model = try MLModel(contentsOf: url, configuration: config)
        let loadMs = (CACurrentMediaTime() - start) * 1000.0
        return (model, loadMs)
    }

    private static func modelURL(named name: String) -> URL? {
        Bundle.main.url(forResource: name, withExtension: "mlmodelc")
            ?? Bundle.main.url(forResource: name, withExtension: "mlpackage")
    }

    private static func benchmark(
        mode: String,
        modelLoadMs: [String: Double],
        predict: () throws -> Void
    ) throws -> CoreMLPoseBenchmarkResult {
        let firstStart = CACurrentMediaTime()
        try predict()
        let firstPredictionMs = (CACurrentMediaTime() - firstStart) * 1000.0

        for _ in 0..<warmupCount {
            try predict()
        }

        var times: [Double] = []
        times.reserveCapacity(iterationCount)
        for _ in 0..<iterationCount {
            let start = CACurrentMediaTime()
            try predict()
            times.append((CACurrentMediaTime() - start) * 1000.0)
        }

        return CoreMLPoseBenchmarkResult(
            mode: mode,
            deviceModel: UIDevice.current.model,
            systemVersion: UIDevice.current.systemVersion,
            thermalState: thermalStateString(ProcessInfo.processInfo.thermalState),
            modelLoadMs: modelLoadMs,
            firstPredictionMs: firstPredictionMs,
            warmupCount: warmupCount,
            iterationCount: iterationCount,
            stats: summarize(times),
            aneVerified: false
        )
    }

    private static func summarize(_ values: [Double]) -> CoreMLPoseLatencyStats {
        let sorted = values.sorted()
        let mean = values.reduce(0.0, +) / Double(values.count)
        return CoreMLPoseLatencyStats(
            mean: mean,
            median: percentile(sorted, 50),
            p90: percentile(sorted, 90),
            p95: percentile(sorted, 95),
            min: sorted.first ?? 0.0,
            max: sorted.last ?? 0.0,
            fps: mean > 0.0 ? 1000.0 / mean : 0.0
        )
    }

    private static func percentile(_ sorted: [Double], _ p: Double) -> Double {
        guard !sorted.isEmpty else { return 0.0 }
        let index = Double(sorted.count - 1) * p / 100.0
        let lower = Int(index)
        let upper = min(lower + 1, sorted.count - 1)
        let weight = index - Double(lower)
        return sorted[lower] * (1.0 - weight) + sorted[upper] * weight
    }

    private static func thermalStateString(_ state: ProcessInfo.ThermalState) -> String {
        switch state {
        case .nominal:
            return "nominal"
        case .fair:
            return "fair"
        case .serious:
            return "serious"
        case .critical:
            return "critical"
        @unknown default:
            return "unknown"
        }
    }
}
