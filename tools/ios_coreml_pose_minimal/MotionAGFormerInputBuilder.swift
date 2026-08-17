import CoreML
import Foundation

enum MotionAGFormerInputBuilderError: Error {
    case emptyBuffer
    case invalidFrameShape
    case invalidOutputShape(String)
}

final class MotionAGFormerInputBuilder {
    static let windowSize = 27
    static let jointCount = 17
    static let channelCount = 3

    private let lookahead: Int
    private var frames: [[[Float]]] = []

    init(lookahead: Int = 5) {
        self.lookahead = lookahead
    }

    func reset() {
        frames.removeAll(keepingCapacity: true)
    }

    func appendCOCO17(
        _ coco17: [PoseKeypoint],
        imageWidth: Int,
        imageHeight: Int
    ) throws {
        let normalized = try PoseCoordinateTransforms.normalizedMotionAGFormerFrame(
            fromCOCO17: coco17,
            imageWidth: imageWidth,
            imageHeight: imageHeight
        )
        try appendNormalizedFrame(normalized)
    }

    func appendNormalizedFrame(_ frame: [[Float]]) throws {
        guard frame.count == Self.jointCount,
              frame.allSatisfy({ $0.count == Self.channelCount }) else {
            throw MotionAGFormerInputBuilderError.invalidFrameShape
        }
        frames.append(frame)
        if frames.count > Self.windowSize {
            frames.removeFirst(frames.count - Self.windowSize)
        }
    }

    func buildLookaheadInput() throws -> MLMultiArray {
        guard !frames.isEmpty else {
            throw MotionAGFormerInputBuilderError.emptyBuffer
        }

        let input = try MLMultiArray(
            shape: [
                NSNumber(value: 1),
                NSNumber(value: Self.windowSize),
                NSNumber(value: Self.jointCount),
                NSNumber(value: Self.channelCount),
            ],
            dataType: .float32
        )

        let indices = lookaheadIndices(sequenceLength: frames.count, latestIndex: frames.count - 1)
        for windowIndex in 0..<Self.windowSize {
            let frame = frames[indices[windowIndex]]
            for jointIndex in 0..<Self.jointCount {
                for channelIndex in 0..<Self.channelCount {
                    let offset = ((windowIndex * Self.jointCount + jointIndex) * Self.channelCount) + channelIndex
                    input[offset] = NSNumber(value: frame[jointIndex][channelIndex])
                }
            }
        }
        return input
    }

    func lookaheadIndices(sequenceLength: Int, latestIndex: Int) -> [Int] {
        let targetIndex = max(0, latestIndex - lookahead)
        let end = targetIndex + lookahead
        let start = end - Self.windowSize + 1
        return (start...end).map { index in
            min(max(index, 0), sequenceLength - 1)
        }
    }

    static func selectTargetFrame(
        from output: MLMultiArray,
        lookahead: Int = 5
    ) throws -> [[Float]] {
        let expectedShape = [1, windowSize, jointCount, channelCount]
        let shape = output.shape.map { $0.intValue }
        guard shape == expectedShape else {
            throw MotionAGFormerInputBuilderError.invalidOutputShape("\(shape) did not match \(expectedShape)")
        }

        let targetIndex = windowSize - 1 - lookahead
        var selected = Array(
            repeating: Array(repeating: Float(0.0), count: channelCount),
            count: jointCount
        )
        for jointIndex in 0..<jointCount {
            for channelIndex in 0..<channelCount {
                selected[jointIndex][channelIndex] = Float(multiArrayValue(
                    output,
                    indices: [0, targetIndex, jointIndex, channelIndex]
                ))
            }
        }
        return selected
    }

    private static func multiArrayValue(_ array: MLMultiArray, indices: [Int]) -> Double {
        let strides = array.strides.map { $0.intValue }
        let offset = zip(indices, strides).reduce(0) { partial, item in
            partial + item.0 * item.1
        }
        return array[offset].doubleValue
    }
}
