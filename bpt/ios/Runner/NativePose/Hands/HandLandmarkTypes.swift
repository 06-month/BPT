import CoreGraphics
import Foundation

enum HandSide: String {
    case left
    case right
}

struct HandLandmarkPoint: Identifiable {
    let id: Int
    let x: Double
    let y: Double
    let z: Double
}

struct HandWorldLandmarkPoint: Identifiable {
    let id: Int
    let x: Double
    let y: Double
    let z: Double
}

struct HandCropBox: Identifiable {
    var id: String { side.rawValue }

    let side: HandSide
    let rect: CGRect
    let frameWidth: Double
    let frameHeight: Double
    let wristConfidence: Double

    var isEmpty: Bool {
        rect.width <= 0.0 || rect.height <= 0.0
    }
}

struct HandLandmarkResult: Identifiable {
    var id: String { side.rawValue }

    let side: HandSide
    let cropBox: HandCropBox
    let frameLandmarks: [HandLandmarkPoint]
    let worldLandmarks: [HandWorldLandmarkPoint]
    let handedness: String?
    let score: Double?

    var wristFramePoint: HandLandmarkPoint? {
        frameLandmarks.first { $0.id == 0 }
    }
}

enum HandSkeletonTopology {
    static let connections: [(Int, Int)] = [
        (0, 1), (1, 2), (2, 3), (3, 4),
        (0, 5), (5, 6), (6, 7), (7, 8),
        (5, 9), (9, 10), (10, 11), (11, 12),
        (9, 13), (13, 14), (14, 15), (15, 16),
        (13, 17), (17, 18), (18, 19), (19, 20),
        (0, 17),
    ]
}
