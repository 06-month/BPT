import CoreML
import Foundation
import QuartzCore
import UIKit

enum CoreMLPosePipelineBenchmarkError: Error {
    case missingModel(String)
    case missingOutput(String)
}

private struct CoreMLPosePipelineTimingSample {
    var rtmposePreprocessMs = 0.0
    var rtmposeCoreMLMs = 0.0
    var simccDecodeMs = 0.0
    var inverseAffineMs = 0.0
    var cocoToH36MMs = 0.0
    var motionInputBuildMs = 0.0
    var motionAGFormerCoreMLMs = 0.0
    var motionOutputSelectMs = 0.0
    var totalNoCameraMs = 0.0
}

private struct CoreMLPosePipelineStats {
    let mean: Double
    let median: Double
    let p90: Double
    let p95: Double
    let min: Double
    let max: Double
    let fps: Double

    var dictionary: [String: Double] {
        [
            "mean": mean,
            "median": median,
            "p90": p90,
            "p95": p95,
            "min": min,
            "max": max,
            "fps": fps,
        ]
    }
}

final class CoreMLPosePipelineBenchmark {
    static let warmupCount = 10
    static let iterationCount = 100

    static func runSyntheticEndToEnd() {
        do {
            let result = try benchmarkSyntheticEndToEnd()
            result.printJSONLike()
        } catch {
            print("CoreMLPosePipelineBenchmark failed: \(type(of: error)) \(error)")
        }
    }

    private static func benchmarkSyntheticEndToEnd() throws -> CoreMLPosePipelineBenchmarkResult {
        let rtmpose = try loadModel(named: "rtmpose_s_forward")
        let motion = try loadModel(named: "motionagformer_xs")
        let syntheticImage = PosePreprocess.makeSyntheticImage()
        let inputBuilder = MotionAGFormerInputBuilder(lookahead: 5)

        let firstSample = try runOneIteration(
            image: syntheticImage,
            rtmposeModel: rtmpose.model,
            motionModel: motion.model,
            inputBuilder: inputBuilder
        )

        for _ in 0..<warmupCount {
            _ = try runOneIteration(
                image: syntheticImage,
                rtmposeModel: rtmpose.model,
                motionModel: motion.model,
                inputBuilder: inputBuilder
            )
        }

        var samples: [CoreMLPosePipelineTimingSample] = []
        samples.reserveCapacity(iterationCount)
        for _ in 0..<iterationCount {
            let sample = try runOneIteration(
                image: syntheticImage,
                rtmposeModel: rtmpose.model,
                motionModel: motion.model,
                inputBuilder: inputBuilder
            )
            samples.append(sample)
        }

        return CoreMLPosePipelineBenchmarkResult(
            mode: "synthetic_end_to_end_no_camera",
            deviceModel: UIDevice.current.model,
            systemVersion: UIDevice.current.systemVersion,
            thermalState: thermalStateString(ProcessInfo.processInfo.thermalState),
            modelLoadMs: [
                "rtmpose_s_forward": rtmpose.loadMs,
                "motionagformer_xs": motion.loadMs,
            ],
            firstPredictionMs: firstSample.totalNoCameraMs,
            warmupCount: warmupCount,
            iterationCount: iterationCount,
            latencyMs: buildLatencyDictionary(samples),
            fps: summarize(samples.map { $0.totalNoCameraMs }).fps,
            aneVerified: false
        )
    }

    private static func runOneIteration(
        image: UIImage,
        rtmposeModel: MLModel,
        motionModel: MLModel,
        inputBuilder: MotionAGFormerInputBuilder
    ) throws -> CoreMLPosePipelineTimingSample {
        var sample = CoreMLPosePipelineTimingSample()
        let totalStart = CACurrentMediaTime()

        let preprocessResult = try timed {
            try PosePreprocess.preprocessFullImage(image)
        }
        let preprocess = preprocessResult.value
        sample.rtmposePreprocessMs = preprocessResult.ms

        let rtmposeProvider = try MLDictionaryFeatureProvider(dictionary: [
            "input_image": MLFeatureValue(multiArray: preprocess.inputTensor)
        ])
        let rtmposeOutputResult = try timed {
            try rtmposeModel.prediction(from: rtmposeProvider)
        }
        let rtmposeOutput = rtmposeOutputResult.value
        sample.rtmposeCoreMLMs = rtmposeOutputResult.ms

        guard let simccX = rtmposeOutput.featureValue(for: "simcc_x")?.multiArrayValue else {
            throw CoreMLPosePipelineBenchmarkError.missingOutput("simcc_x")
        }
        guard let simccY = rtmposeOutput.featureValue(for: "simcc_y")?.multiArrayValue else {
            throw CoreMLPosePipelineBenchmarkError.missingOutput("simcc_y")
        }

        let decodeResult = try timed {
            try SimCCDecoder.decodeToInputCoordinates(simccX: simccX, simccY: simccY)
        }
        let decoded = decodeResult.value
        sample.simccDecodeMs = decodeResult.ms

        let imageKeypointsResult = timed {
            PoseCoordinateTransforms.applyInverseAffine(
                decoded: decoded,
                inverseAffine: preprocess.inverseAffine
            )
        }
        let coco17 = imageKeypointsResult.value
        sample.inverseAffineMs = imageKeypointsResult.ms

        let normalizedFrameResult = try timed {
            try PoseCoordinateTransforms.normalizedMotionAGFormerFrame(
                fromCOCO17: coco17,
                imageWidth: preprocess.imageWidth,
                imageHeight: preprocess.imageHeight
            )
        }
        let normalizedFrame = normalizedFrameResult.value
        sample.cocoToH36MMs = normalizedFrameResult.ms

        let motionInputResult = try timed {
            try inputBuilder.appendNormalizedFrame(normalizedFrame)
            return try inputBuilder.buildLookaheadInput()
        }
        let motionInput = motionInputResult.value
        sample.motionInputBuildMs = motionInputResult.ms

        let motionProvider = try MLDictionaryFeatureProvider(dictionary: [
            "input_2d_sequence": MLFeatureValue(multiArray: motionInput)
        ])
        let motionOutputResult = try timed {
            try motionModel.prediction(from: motionProvider)
        }
        let motionOutput = motionOutputResult.value
        sample.motionAGFormerCoreMLMs = motionOutputResult.ms

        let selectedResult = try timed {
            guard let pred3D = motionOutput.featureValue(for: "pred_3d_sequence")?.multiArrayValue else {
                throw CoreMLPosePipelineBenchmarkError.missingOutput("pred_3d_sequence")
            }
            return try MotionAGFormerInputBuilder.selectTargetFrame(from: pred3D, lookahead: 5)
        }
        _ = selectedResult.value
        sample.motionOutputSelectMs = selectedResult.ms
        sample.totalNoCameraMs = (CACurrentMediaTime() - totalStart) * 1000.0
        return sample
    }

    private static func loadModel(named name: String) throws -> (model: MLModel, loadMs: Double) {
        let config = MLModelConfiguration()
        config.computeUnits = .all

        guard let url = modelURL(named: name) else {
            throw CoreMLPosePipelineBenchmarkError.missingModel(name)
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

    private static func buildLatencyDictionary(
        _ samples: [CoreMLPosePipelineTimingSample]
    ) -> [String: [String: Double]] {
        [
            "total_no_camera": summarize(samples.map { $0.totalNoCameraMs }).dictionary,
            "rtmpose_preprocess": summarize(samples.map { $0.rtmposePreprocessMs }).dictionary,
            "rtmpose_coreml": summarize(samples.map { $0.rtmposeCoreMLMs }).dictionary,
            "simcc_decode": summarize(samples.map { $0.simccDecodeMs }).dictionary,
            "inverse_affine": summarize(samples.map { $0.inverseAffineMs }).dictionary,
            "coco_to_h36m": summarize(samples.map { $0.cocoToH36MMs }).dictionary,
            "motion_input_build": summarize(samples.map { $0.motionInputBuildMs }).dictionary,
            "motionagformer_coreml": summarize(samples.map { $0.motionAGFormerCoreMLMs }).dictionary,
            "motion_output_select": summarize(samples.map { $0.motionOutputSelectMs }).dictionary,
        ]
    }

    private static func timed<T>(_ body: () throws -> T) rethrows -> (value: T, ms: Double) {
        let start = CACurrentMediaTime()
        let value = try body()
        return (value, (CACurrentMediaTime() - start) * 1000.0)
    }

    private static func summarize(_ values: [Double]) -> CoreMLPosePipelineStats {
        guard !values.isEmpty else {
            return CoreMLPosePipelineStats(mean: 0.0, median: 0.0, p90: 0.0, p95: 0.0, min: 0.0, max: 0.0, fps: 0.0)
        }
        let sorted = values.sorted()
        let mean = values.reduce(0.0, +) / Double(values.count)
        return CoreMLPosePipelineStats(
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

private struct CoreMLPosePipelineBenchmarkResult {
    let mode: String
    let deviceModel: String
    let systemVersion: String
    let thermalState: String
    let modelLoadMs: [String: Double]
    let firstPredictionMs: Double
    let warmupCount: Int
    let iterationCount: Int
    let latencyMs: [String: [String: Double]]
    let fps: Double
    let aneVerified: Bool

    func printJSONLike() {
        let payload: [String: Any] = [
            "mode": mode,
            "device_model": deviceModel,
            "ios_version": systemVersion,
            "thermal_state": thermalState,
            "model_load_ms": modelLoadMs,
            "first_prediction_ms": firstPredictionMs,
            "warmup_count": warmupCount,
            "iteration_count": iterationCount,
            "latency_ms": latencyMs,
            "mean_ms": latencyMs["total_no_camera"]?["mean"] ?? 0.0,
            "median_ms": latencyMs["total_no_camera"]?["median"] ?? 0.0,
            "p90_ms": latencyMs["total_no_camera"]?["p90"] ?? 0.0,
            "p95_ms": latencyMs["total_no_camera"]?["p95"] ?? 0.0,
            "fps": fps,
            "ane_verified": aneVerified,
        ]

        if let data = try? JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys]),
           let text = String(data: data, encoding: .utf8) {
            print(text)
        } else {
            print(payload)
        }
    }
}
