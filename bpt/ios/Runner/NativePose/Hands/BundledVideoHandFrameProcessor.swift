import QuartzCore
import UIKit

struct BundledVideoHandTiming {
    var wristCropBuildMs = 0.0
    var mediaPipeLeftHandMs = 0.0
    var mediaPipeRightHandMs = 0.0

    var mediaPipeHandCombinedMs: Double {
        mediaPipeLeftHandMs + mediaPipeRightHandMs
    }
}

struct BundledVideoHandFrameResult {
    let cropBoxes: [HandCropBox]
    let handResults: [HandLandmarkResult]
    let leftHand: HandLandmarkResult?
    let rightHand: HandLandmarkResult?
    let timing: BundledVideoHandTiming

    var bothHandsDetected: Bool {
        leftHand != nil && rightHand != nil
    }
}

enum BundledVideoHandFrameProcessor {
    static func runWristCropHands(
        image: UIImage,
        rawCoco17: [PoseKeypoint],
        imageWidth: Double,
        imageHeight: Double,
        timestampMs: Int,
        handLandmarkers: MediaPipeHandLandmarkerPair,
        cropSize: Double = HandCropBuilder.defaultCropSize,
        confidenceThreshold: Double = HandCropBuilder.defaultWristConfidenceThreshold,
        debugFrameIndex: Int? = nil,
        debugEveryNFrames: Int = 60
    ) -> BundledVideoHandFrameResult {
        guard rawCoco17.count == 17 else {
            return BundledVideoHandFrameResult(
                cropBoxes: [],
                handResults: [],
                leftHand: nil,
                rightHand: nil,
                timing: BundledVideoHandTiming()
            )
        }

        var timing = BundledVideoHandTiming()
        var cropBoxes: [HandCropBox] = []
        var handResults: [HandLandmarkResult] = []
        var leftHand: HandLandmarkResult?
        var rightHand: HandLandmarkResult?

        let candidates: [(HandSide, PoseKeypoint, MediaPipeHandLandmarkerRunner)] = [
            (.left, rawCoco17[9], handLandmarkers.left),
            (.right, rawCoco17[10], handLandmarkers.right),
        ]

        for (side, wrist, runner) in candidates {
            let cropStart = CACurrentMediaTime()
            guard let cropBox = HandCropBuilder.buildWristCrop(
                frameWidth: imageWidth,
                frameHeight: imageHeight,
                wrist: wrist,
                side: side,
                cropSize: cropSize,
                confidenceThreshold: confidenceThreshold
            ) else {
                timing.wristCropBuildMs += elapsedMs(cropStart)
                if shouldDebug(frameIndex: debugFrameIndex, every: debugEveryNFrames) {
                    let reason = wrist.confidence < confidenceThreshold ? "low_wrist_confidence" : "invalid_crop"
                    print("MediaPipe hand crop skipped frame=\(debugFrameIndex ?? -1) side=\(side.rawValue) reason=\(reason) wrist_conf=\(String(format: "%.3f", wrist.confidence)) threshold=\(confidenceThreshold)")
                }
                continue
            }
            cropBoxes.append(cropBox)

            let cropImage: UIImage
            do {
                cropImage = try HandCropBuilder.cropImage(image, cropBox: cropBox)
            } catch {
                timing.wristCropBuildMs += elapsedMs(cropStart)
                print("Failed to crop \(side.rawValue) hand: \(type(of: error)) \(error)")
                continue
            }
            timing.wristCropBuildMs += elapsedMs(cropStart)

            guard runner.isAvailable else {
                continue
            }

            let detectStart = CACurrentMediaTime()
            let result = runner.detect(
                cropImage: cropImage,
                cropBox: cropBox,
                timestampMs: timestampMs
            )
            let detectMs = elapsedMs(detectStart)
            switch side {
            case .left:
                timing.mediaPipeLeftHandMs += detectMs
                leftHand = result
            case .right:
                timing.mediaPipeRightHandMs += detectMs
                rightHand = result
            }

            if let result {
                handResults.append(result)
            }

            if shouldDebug(frameIndex: debugFrameIndex, every: debugEveryNFrames) {
                let rect = cropBox.rect
                print("MediaPipe hand crop frame=\(debugFrameIndex ?? -1) side=\(side.rawValue) rect=[\(Int(rect.minX)),\(Int(rect.minY)),\(Int(rect.width)),\(Int(rect.height))] wrist_conf=\(String(format: "%.3f", cropBox.wristConfidence)) detected=\(result != nil) applied_timestamp=\(runner.lastTimestampMs.map(String.init) ?? "-") runner_id=\(runner.debugIdentifier)")
            }
        }

        return BundledVideoHandFrameResult(
            cropBoxes: cropBoxes,
            handResults: handResults,
            leftHand: leftHand,
            rightHand: rightHand,
            timing: timing
        )
    }

    private static func shouldDebug(frameIndex: Int?, every: Int) -> Bool {
        guard let frameIndex, every > 0 else { return false }
        return frameIndex % every == 0
    }

    private static func elapsedMs(_ start: CFTimeInterval) -> Double {
        (CACurrentMediaTime() - start) * 1000.0
    }
}
