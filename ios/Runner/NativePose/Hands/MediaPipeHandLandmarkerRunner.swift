import Foundation
import UIKit

#if canImport(MediaPipeTasksVision)
import MediaPipeTasksVision
#endif

enum MediaPipeHandLandmarkerRunnerError: Error {
    case dependencyUnavailable
    case missingTaskModel
}

final class MediaPipeHandLandmarkerRunner {
    let side: HandSide
    let runningModeDescription = "video"

    private(set) var isAvailable = false
    private(set) var unavailableReason: String?
    private(set) var lastTimestampMs: Int?

    var debugIdentifier: String {
        String(describing: ObjectIdentifier(self))
    }

    #if canImport(MediaPipeTasksVision)
    private var handLandmarker: HandLandmarker?
    #endif

    init(
        side: HandSide,
        modelResourceName: String = "hand_landmarker",
        minHandDetectionConfidence: Float = 0.5,
        minHandPresenceConfidence: Float = 0.5,
        minTrackingConfidence: Float = 0.5
    ) {
        self.side = side

        #if canImport(MediaPipeTasksVision)
        guard let modelPath = Bundle.main.path(forResource: modelResourceName, ofType: "task") else {
            isAvailable = false
            unavailableReason = "Missing \(modelResourceName).task in app bundle"
            return
        }

        do {
            let options = HandLandmarkerOptions()
            options.baseOptions.modelAssetPath = modelPath
            options.runningMode = .video
            options.numHands = 1
            options.minHandDetectionConfidence = minHandDetectionConfidence
            options.minHandPresenceConfidence = minHandPresenceConfidence
            options.minTrackingConfidence = minTrackingConfidence
            handLandmarker = try HandLandmarker(options: options)
            isAvailable = true
        } catch {
            isAvailable = false
            unavailableReason = "MediaPipe HandLandmarker init failed: \(type(of: error)) \(error)"
        }
        #else
        isAvailable = false
        unavailableReason = "MediaPipeTasksVision is not linked. Install the MediaPipeTasksVision pod and open the generated workspace."
        #endif
    }

    func detect(
        cropImage: UIImage,
        cropBox: HandCropBox,
        timestampMs: Int
    ) -> HandLandmarkResult? {
        guard isAvailable else {
            return nil
        }

        #if canImport(MediaPipeTasksVision)
        guard let handLandmarker else {
            return nil
        }

        do {
            let safeTimestamp = nextMonotonicTimestamp(timestampMs)
            let image = try MPImage(uiImage: cropImage)
            let result = try handLandmarker.detect(
                videoFrame: image,
                timestampInMilliseconds: safeTimestamp
            )
            return mapResult(result, cropBox: cropBox)
        } catch {
            print("MediaPipe \(side.rawValue) hand detection failed: \(type(of: error)) \(error)")
            return nil
        }
        #else
        return nil
        #endif
    }

    private func nextMonotonicTimestamp(_ timestampMs: Int) -> Int {
        let next: Int
        if let lastTimestampMs, timestampMs <= lastTimestampMs {
            next = lastTimestampMs + 1
        } else {
            next = timestampMs
        }
        lastTimestampMs = next
        return next
    }

    #if canImport(MediaPipeTasksVision)
    private func mapResult(
        _ result: HandLandmarkerResult,
        cropBox: HandCropBox
    ) -> HandLandmarkResult? {
        guard let landmarks = result.landmarks.first,
              landmarks.count == 21 else {
            return nil
        }

        // MediaPipe Tasks iOS returns normalized image landmarks in crop-local
        // coordinates. x/y are normalized by the crop width/height.
        let frameLandmarks = landmarks.enumerated().map { index, landmark in
            HandLandmarkPoint(
                id: index,
                x: Double(cropBox.rect.minX + CGFloat(landmark.x) * cropBox.rect.width),
                y: Double(cropBox.rect.minY + CGFloat(landmark.y) * cropBox.rect.height),
                z: Double(landmark.z)
            )
        }

        let worldLandmarks = result.worldLandmarks.first?.enumerated().map { index, landmark in
            HandWorldLandmarkPoint(
                id: index,
                x: Double(landmark.x),
                y: Double(landmark.y),
                z: Double(landmark.z)
            )
        } ?? []

        let category = result.handedness.first?.first
        return HandLandmarkResult(
            side: side,
            cropBox: cropBox,
            frameLandmarks: frameLandmarks,
            worldLandmarks: worldLandmarks,
            handedness: category?.categoryName,
            score: category.map { Double($0.score) }
        )
    }
    #endif
}

final class MediaPipeHandLandmarkerPair {
    let left: MediaPipeHandLandmarkerRunner
    let right: MediaPipeHandLandmarkerRunner

    init() {
        left = MediaPipeHandLandmarkerRunner(side: .left)
        right = MediaPipeHandLandmarkerRunner(side: .right)
    }

    var isAnyAvailable: Bool {
        left.isAvailable || right.isAvailable
    }

    var debugDescription: String {
        "left_id=\(left.debugIdentifier) right_id=\(right.debugIdentifier) mode=video"
    }

    var statusDescription: String {
        if isAnyAvailable {
            return "MediaPipe hand runners available (video mode)"
        }
        return [
            left.unavailableReason.map { "left=\($0)" },
            right.unavailableReason.map { "right=\($0)" },
        ]
        .compactMap { $0 }
        .joined(separator: "; ")
    }
}
