import CoreML
import Foundation

enum CoreMLMultiArrayIndexingError: Error {
    case invalidShape(label: String, actual: [Int], expected: [Int])
    case offsetOutOfBounds(label: String, offset: Int, count: Int, shape: [Int], strides: [Int])
}

enum CoreMLMultiArrayIndexing {
    static func validateShape(_ array: MLMultiArray, expectedShape: [Int], label: String) throws {
        let actual = shape(array)
        guard actual == expectedShape else {
            print("""
            MLMultiArray shape mismatch [\(label)]
              actual_shape=\(actual)
              expected_shape=\(expectedShape)
              strides=\(strides(array))
              count=\(array.count)
            """)
            throw CoreMLMultiArrayIndexingError.invalidShape(
                label: label,
                actual: actual,
                expected: expectedShape
            )
        }
    }

    static func logArray(_ array: MLMultiArray, label: String) {
        print("\(label): shape=\(shape(array)) strides=\(strides(array)) count=\(array.count)")
    }

    static func rtmposeImageInputOffset(channel: Int, y: Int, x: Int) -> Int {
        channel * 256 * 192 + y * 192 + x
    }

    static func simccXOffset(joint: Int, xIndex: Int) -> Int {
        joint * 384 + xIndex
    }

    static func simccYOffset(joint: Int, yIndex: Int) -> Int {
        joint * 512 + yIndex
    }

    static func motionAGFormerOffset(t: Int, joint: Int, coord: Int) -> Int {
        t * 17 * 3 + joint * 3 + coord
    }

    static func setFloat(_ array: MLMultiArray, offset: Int, value: Float, label: String) throws {
        try validateOffset(offset, in: array, label: label)
        array[offset] = NSNumber(value: value)
    }

    static func double(_ array: MLMultiArray, offset: Int, label: String) throws -> Double {
        try validateOffset(offset, in: array, label: label)
        return array[offset].doubleValue
    }

    private static func validateOffset(_ offset: Int, in array: MLMultiArray, label: String) throws {
        guard offset >= 0 && offset < array.count else {
            let actualShape = shape(array)
            let actualStrides = strides(array)
            print("""
            MLMultiArray offset out of bounds [\(label)]
              shape=\(actualShape)
              strides=\(actualStrides)
              count=\(array.count)
              requested_offset=\(offset)
            """)
            throw CoreMLMultiArrayIndexingError.offsetOutOfBounds(
                label: label,
                offset: offset,
                count: array.count,
                shape: actualShape,
                strides: actualStrides
            )
        }
    }

    private static func shape(_ array: MLMultiArray) -> [Int] {
        array.shape.map { $0.intValue }
    }

    private static func strides(_ array: MLMultiArray) -> [Int] {
        array.strides.map { $0.intValue }
    }
}

struct SimCCDecodeResult {
    let inputCoordinates: [PosePoint]
    let confidences: [Double]
}

enum SimCCDecoderError: Error {
    case invalidShape(String)
}

enum SimCCDecoder {
    static let jointCount = 17
    static let xBinCount = 384
    static let yBinCount = 512

    static func decodeToInputCoordinates(
        simccX: MLMultiArray,
        simccY: MLMultiArray,
        splitRatio: Double = PoseCoordinateTransforms.simccSplitRatio
    ) throws -> SimCCDecodeResult {
        try CoreMLMultiArrayIndexing.validateShape(
            simccX,
            expectedShape: [1, jointCount, xBinCount],
            label: "SimCCDecoder.simcc_x"
        )
        try CoreMLMultiArrayIndexing.validateShape(
            simccY,
            expectedShape: [1, jointCount, yBinCount],
            label: "SimCCDecoder.simcc_y"
        )

        var coordinates: [PosePoint] = []
        var confidences: [Double] = []
        coordinates.reserveCapacity(jointCount)
        confidences.reserveCapacity(jointCount)

        for jointIndex in 0..<jointCount {
            let xResult = try argmaxSimCCX(array: simccX, jointIndex: jointIndex)
            let yResult = try argmaxSimCCY(array: simccY, jointIndex: jointIndex)
            let confidence = min(xResult.value, yResult.value)

            if confidence <= 0.0 {
                coordinates.append(PosePoint(x: -1.0 / splitRatio, y: -1.0 / splitRatio))
            } else {
                coordinates.append(PosePoint(
                    x: Double(xResult.index) / splitRatio,
                    y: Double(yResult.index) / splitRatio
                ))
            }
            confidences.append(confidence)
        }

        return SimCCDecodeResult(inputCoordinates: coordinates, confidences: confidences)
    }

    private static func argmaxSimCCX(
        array: MLMultiArray,
        jointIndex: Int
    ) throws -> (index: Int, value: Double) {
        var bestIndex = 0
        var bestValue = -Double.greatestFiniteMagnitude
        for binIndex in 0..<xBinCount {
            let offset = CoreMLMultiArrayIndexing.simccXOffset(joint: jointIndex, xIndex: binIndex)
            let value = try CoreMLMultiArrayIndexing.double(
                array,
                offset: offset,
                label: "SimCCDecoder.simcc_x"
            )
            if value > bestValue {
                bestValue = value
                bestIndex = binIndex
            }
        }
        return (bestIndex, bestValue)
    }

    private static func argmaxSimCCY(
        array: MLMultiArray,
        jointIndex: Int
    ) throws -> (index: Int, value: Double) {
        var bestIndex = 0
        var bestValue = -Double.greatestFiniteMagnitude
        for binIndex in 0..<yBinCount {
            let offset = CoreMLMultiArrayIndexing.simccYOffset(joint: jointIndex, yIndex: binIndex)
            let value = try CoreMLMultiArrayIndexing.double(
                array,
                offset: offset,
                label: "SimCCDecoder.simcc_y"
            )
            if value > bestValue {
                bestValue = value
                bestIndex = binIndex
            }
        }
        return (bestIndex, bestValue)
    }
}
