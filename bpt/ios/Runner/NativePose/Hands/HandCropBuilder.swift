import CoreGraphics
import UIKit

enum HandCropBuilderError: Error {
    case missingCGImage
    case cropFailed
}

enum HandCropBuilder {
    static let defaultCropSize = 256.0
    static let defaultWristConfidenceThreshold = 0.3

    static func buildWristCrop(
        frameWidth: Double,
        frameHeight: Double,
        wrist: PoseKeypoint,
        side: HandSide,
        cropSize: Double = defaultCropSize,
        confidenceThreshold: Double = defaultWristConfidenceThreshold
    ) -> HandCropBox? {
        guard frameWidth > 0.0,
              frameHeight > 0.0,
              cropSize > 0.0,
              wrist.confidence >= confidenceThreshold else {
            return nil
        }

        let size = min(cropSize, frameWidth, frameHeight)
        guard size > 0.0 else { return nil }

        let half = size * 0.5
        let x = clamp(wrist.x - half, lower: 0.0, upper: max(frameWidth - size, 0.0))
        let y = clamp(wrist.y - half, lower: 0.0, upper: max(frameHeight - size, 0.0))
        let rect = CGRect(x: x, y: y, width: size, height: size)

        return HandCropBox(
            side: side,
            rect: rect,
            frameWidth: frameWidth,
            frameHeight: frameHeight,
            wristConfidence: wrist.confidence
        )
    }

    static func cropImage(_ image: UIImage, cropBox: HandCropBox) throws -> UIImage {
        guard !cropBox.isEmpty else {
            throw HandCropBuilderError.cropFailed
        }
        guard let cgImage = image.cgImage else {
            throw HandCropBuilderError.missingCGImage
        }

        let safeRect = CGRect(
            x: max(0.0, cropBox.rect.minX),
            y: max(0.0, cropBox.rect.minY),
            width: min(cropBox.rect.width, CGFloat(cgImage.width) - cropBox.rect.minX),
            height: min(cropBox.rect.height, CGFloat(cgImage.height) - cropBox.rect.minY)
        ).integral

        guard safeRect.width > 0.0,
              safeRect.height > 0.0,
              let cropped = cgImage.cropping(to: safeRect) else {
            throw HandCropBuilderError.cropFailed
        }

        return UIImage(cgImage: cropped, scale: image.scale, orientation: image.imageOrientation)
    }

    static func visualBodyKeypoints(
        rawBodyKeypoints: [PoseKeypoint],
        leftHand: HandLandmarkResult?,
        rightHand: HandLandmarkResult?,
        useMediaPipeWrist: Bool
    ) -> [PoseKeypoint] {
        guard useMediaPipeWrist else {
            return rawBodyKeypoints
        }

        var visual = rawBodyKeypoints
        replaceWrist(in: &visual, wristIndex: 9, hand: leftHand)
        replaceWrist(in: &visual, wristIndex: 10, hand: rightHand)
        return visual
    }

    private static func replaceWrist(
        in keypoints: inout [PoseKeypoint],
        wristIndex: Int,
        hand: HandLandmarkResult?
    ) {
        guard keypoints.indices.contains(wristIndex),
              let wrist = hand?.wristFramePoint else {
            return
        }

        let original = keypoints[wristIndex]
        keypoints[wristIndex] = PoseKeypoint(
            x: wrist.x,
            y: wrist.y,
            confidence: original.confidence
        )
    }

    private static func clamp(_ value: Double, lower: Double, upper: Double) -> Double {
        min(max(value, lower), upper)
    }
}
