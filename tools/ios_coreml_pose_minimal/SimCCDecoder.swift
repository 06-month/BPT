import CoreML
import Foundation

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
        try validate(simccX, expectedShape: [1, jointCount, xBinCount], name: "simcc_x")
        try validate(simccY, expectedShape: [1, jointCount, yBinCount], name: "simcc_y")

        var coordinates: [PosePoint] = []
        var confidences: [Double] = []
        coordinates.reserveCapacity(jointCount)
        confidences.reserveCapacity(jointCount)

        for jointIndex in 0..<jointCount {
            let xResult = argmax(array: simccX, jointIndex: jointIndex, binCount: xBinCount)
            let yResult = argmax(array: simccY, jointIndex: jointIndex, binCount: yBinCount)
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

    private static func argmax(
        array: MLMultiArray,
        jointIndex: Int,
        binCount: Int
    ) -> (index: Int, value: Double) {
        var bestIndex = 0
        var bestValue = -Double.greatestFiniteMagnitude
        for binIndex in 0..<binCount {
            let value = multiArrayValue(array, indices: [0, jointIndex, binIndex])
            if value > bestValue {
                bestValue = value
                bestIndex = binIndex
            }
        }
        return (bestIndex, bestValue)
    }

    private static func validate(_ array: MLMultiArray, expectedShape: [Int], name: String) throws {
        let shape = array.shape.map { $0.intValue }
        guard shape == expectedShape else {
            throw SimCCDecoderError.invalidShape("\(name) shape \(shape) did not match \(expectedShape)")
        }
    }

    static func multiArrayValue(_ array: MLMultiArray, indices: [Int]) -> Double {
        let strides = array.strides.map { $0.intValue }
        let offset = zip(indices, strides).reduce(0) { partial, item in
            partial + item.0 * item.1
        }
        return array[offset].doubleValue
    }
}
