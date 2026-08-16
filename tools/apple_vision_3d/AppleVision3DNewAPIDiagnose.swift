import AVFoundation
import CoreGraphics
import CoreImage
import CoreMedia
import Foundation
import ImageIO
import simd
import Vision

@available(macOS 15.0, *)
struct Arguments {
    var diagnoseOnly = false
    var inputVideo: String?
    var inputImage: String?
    var maxFrames = 1
    var stride = 1
    var outputJSONL: String?
    var probeConstructChild = false
    var probeRevisionsChild = false
    var probeVideoFirstFrameChild = false
    var probeImageChild = false
}

@available(macOS 15.0, *)
@main
struct AppleVision3DNewAPIDiagnose {
    static func main() async {
        guard #available(macOS 15.0, *) else {
            fputs("DetectHumanBodyPose3DRequest requires macOS 15.0 or newer.\n", stderr)
            exit(0)
        }
        guard let args = parseArguments() else {
            printUsage()
            exit(2)
        }

        do {
            if args.probeRevisionsChild {
                try probeRevisionsChild()
                return
            }
            if args.probeConstructChild {
                try probeConstructChild()
                return
            }
            if args.probeImageChild {
                try await probeImageChild(args: args)
                return
            }
            if args.probeVideoFirstFrameChild {
                try await probeVideoFirstFrameChild(args: args)
                return
            }

            printEnvironment()
            print([
                "diagnostic": "new_api_compile_time",
                "detect_human_body_pose_3d_request_type_available": true,
                "api": "DetectHumanBodyPose3DRequest"
            ] as [String: Any])

            let revisions = runChild(["--probe-revisions-child"])
            print([
                "diagnostic": "new_api_revisions",
                "works": revisions.works,
                "termination_status": revisions.terminationStatus,
                "termination_reason": revisions.terminationReason,
                "output": revisions.output
            ] as [String: Any])

            let construction = runChild(["--probe-construct-child"])
            print([
                "diagnostic": "new_api_request_construction",
                "works": construction.works,
                "termination_status": construction.terminationStatus,
                "termination_reason": construction.terminationReason,
                "output": construction.output
            ] as [String: Any])

            if args.diagnoseOnly {
                print([
                    "diagnose_only": true,
                    "request_construction_succeeded": construction.works
                ] as [String: Any])
                return
            }

            guard construction.works else {
                print([
                    "inference_ran": false,
                    "failure_stage": "construction",
                    "reason": "DetectHumanBodyPose3DRequest construction failed"
                ] as [String: Any])
                return
            }

            if args.inputImage != nil {
                let result = runChild(buildChildArgs(args, flag: "--probe-image-child"))
                print([
                    "diagnostic": "new_api_image_perform",
                    "works": result.works,
                    "termination_status": result.terminationStatus,
                    "termination_reason": result.terminationReason,
                    "output": result.output
                ] as [String: Any])
                return
            }

            if args.inputVideo != nil {
                let result = runChild(buildChildArgs(args, flag: "--probe-video-first-frame-child"))
                print([
                    "diagnostic": "new_api_video_first_frame_perform",
                    "works": result.works,
                    "termination_status": result.terminationStatus,
                    "termination_reason": result.terminationReason,
                    "output": result.output
                ] as [String: Any])
                return
            }

            print(["inference_ran": false, "reason": "pass --input-image or --input-video"] as [String: Any])
        } catch {
            print([
                "error_type": String(describing: type(of: error)),
                "localizedDescription": error.localizedDescription
            ] as [String: Any])
            exit(1)
        }
    }
}

@available(macOS 15.0, *)
func parseArguments() -> Arguments? {
    var args = Arguments()
    let values = CommandLine.arguments
    var index = 1
    while index < values.count {
        let key = values[index]
        let next = index + 1 < values.count ? values[index + 1] : nil
        switch key {
        case "--diagnose-only":
            args.diagnoseOnly = true
            index += 1
        case "--input-video":
            guard let next else { return nil }
            args.inputVideo = next
            index += 2
        case "--input-image":
            guard let next else { return nil }
            args.inputImage = next
            index += 2
        case "--max-frames":
            guard let next, let value = Int(next) else { return nil }
            args.maxFrames = value
            index += 2
        case "--stride":
            guard let next, let value = Int(next), value > 0 else { return nil }
            args.stride = value
            index += 2
        case "--output-jsonl":
            guard let next else { return nil }
            args.outputJSONL = next
            index += 2
        case "--probe-construct-child":
            args.probeConstructChild = true
            index += 1
        case "--probe-revisions-child":
            args.probeRevisionsChild = true
            index += 1
        case "--probe-video-first-frame-child":
            args.probeVideoFirstFrameChild = true
            index += 1
        case "--probe-image-child":
            args.probeImageChild = true
            index += 1
        default:
            return nil
        }
    }
    return args
}

func printUsage() {
    fputs("""
    Usage:
      apple_vision_3d_new_api_diagnose --diagnose-only
      apple_vision_3d_new_api_diagnose --input-video path [--max-frames 1] [--stride 1] [--output-jsonl path]
      apple_vision_3d_new_api_diagnose --input-image path [--output-jsonl path]

    """, stderr)
}

func printEnvironment() {
    let info = ProcessInfo.processInfo
    let arch: String
    #if arch(arm64)
    arch = "arm64"
    #elseif arch(x86_64)
    arch = "x86_64"
    #else
    arch = "unknown"
    #endif
    print([
        "diagnostic": "environment",
        "macos_version": info.operatingSystemVersionString,
        "architecture": arch,
        "process_id": info.processIdentifier,
        "process_name": info.processName,
        "host_name": info.hostName,
        "swift_version": swiftVersion()
    ] as [String: Any])
}

func swiftVersion() -> String {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/xcrun")
    process.arguments = ["swiftc", "--version"]
    let pipe = Pipe()
    process.standardOutput = pipe
    process.standardError = pipe
    do {
        try process.run()
        process.waitUntilExit()
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        return String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? "unknown"
    } catch {
        return "unavailable: \(error.localizedDescription)"
    }
}

struct ChildResult {
    let works: Bool
    let terminationStatus: Int32
    let terminationReason: String
    let output: String
}

func runChild(_ arguments: [String]) -> ChildResult {
    guard let executableURL = Bundle.main.executableURL else {
        return ChildResult(works: false, terminationStatus: -1, terminationReason: "missing_executable_url", output: "")
    }
    let process = Process()
    process.executableURL = executableURL
    process.arguments = arguments
    let pipe = Pipe()
    process.standardOutput = pipe
    process.standardError = pipe
    do {
        try process.run()
        process.waitUntilExit()
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        let output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let reason: String
        switch process.terminationReason {
        case .exit:
            reason = "exit"
        case .uncaughtSignal:
            reason = "uncaught_signal"
        @unknown default:
            reason = "unknown"
        }
        return ChildResult(
            works: process.terminationReason == .exit && process.terminationStatus == 0,
            terminationStatus: process.terminationStatus,
            terminationReason: reason,
            output: output
        )
    } catch {
        return ChildResult(works: false, terminationStatus: -1, terminationReason: "\(type(of: error)): \(error.localizedDescription)", output: "")
    }
}

@available(macOS 15.0, *)
func probeRevisionsChild() throws {
    let request = DetectHumanBodyPose3DRequest()
    print([
        "supported_revisions": String(describing: DetectHumanBodyPose3DRequest.supportedRevisions),
        "selected_revision": String(describing: request.revision),
        "supported_joint_names": request.supportedJointNames.map { $0.rawValue },
        "supported_joints_group_names": request.supportedJointsGroupNames.map { $0.rawValue },
        "minimum_latency_frame_count": request.minimumLatencyFrameCount
    ] as [String: Any])
}

@available(macOS 15.0, *)
func probeConstructChild() throws {
    let request = DetectHumanBodyPose3DRequest()
    print([
        "request_constructed": true,
        "selected_revision": String(describing: request.revision),
        "supported_joint_names": request.supportedJointNames.map { $0.rawValue },
        "supported_joints_group_names": request.supportedJointsGroupNames.map { $0.rawValue }
    ] as [String: Any])
}

@available(macOS 15.0, *)
func probeImageChild(args: Arguments) async throws {
    guard let inputImage = args.inputImage else {
        throw RuntimeError("missing --input-image")
    }
    let request = DetectHumanBodyPose3DRequest()
    let observations = try await request.perform(on: URL(fileURLWithPath: inputImage), orientation: .up)
    try writeOptionalJSONL(args.outputJSONL, frameIndex: 0, timestamp: 0.0, observations: observations)
    printObservationSummary(observations, outputJSONL: args.outputJSONL)
}

@available(macOS 15.0, *)
func probeVideoFirstFrameChild(args: Arguments) async throws {
    guard let inputVideo = args.inputVideo else {
        throw RuntimeError("missing --input-video")
    }
    let sample = try firstVideoSample(inputVideo: inputVideo, stride: args.stride)
    let request = DetectHumanBodyPose3DRequest()
    let observations = try await request.perform(on: sample.buffer, orientation: .up)
    try writeOptionalJSONL(args.outputJSONL, frameIndex: sample.frameIndex, timestamp: sample.timestamp, observations: observations)
    printObservationSummary(observations, outputJSONL: args.outputJSONL)
}

struct VideoSample {
    let buffer: CMSampleBuffer
    let frameIndex: Int
    let timestamp: Double
}

func firstVideoSample(inputVideo: String, stride: Int) throws -> VideoSample {
    let asset = AVAsset(url: URL(fileURLWithPath: inputVideo))
    guard let track = asset.tracks(withMediaType: .video).first else {
        throw RuntimeError("No video track found: \(inputVideo)")
    }
    let reader = try AVAssetReader(asset: asset)
    let output = AVAssetReaderTrackOutput(
        track: track,
        outputSettings: [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA
        ]
    )
    output.alwaysCopiesSampleData = false
    guard reader.canAdd(output) else {
        throw RuntimeError("Could not add AVAssetReaderTrackOutput")
    }
    reader.add(output)
    guard reader.startReading() else {
        throw RuntimeError("AVAssetReader failed to start")
    }
    var frameIndex = 0
    while let sample = output.copyNextSampleBuffer() {
        defer { frameIndex += 1 }
        if frameIndex % stride != 0 {
            continue
        }
        let timestamp = CMSampleBufferGetPresentationTimeStamp(sample).seconds
        return VideoSample(buffer: sample, frameIndex: frameIndex, timestamp: timestamp)
    }
    throw RuntimeError("No sample buffer read from video")
}

@available(macOS 15.0, *)
func writeOptionalJSONL(_ path: String?, frameIndex: Int, timestamp: Double, observations: [HumanBodyPose3DObservation]) throws {
    guard let path else { return }
    let outputURL = URL(fileURLWithPath: path)
    try FileManager.default.createDirectory(at: outputURL.deletingLastPathComponent(), withIntermediateDirectories: true)
    FileManager.default.createFile(atPath: outputURL.path, contents: nil)
    let handle = try FileHandle(forWritingTo: outputURL)
    defer { try? handle.close() }
    let record = recordFromObservations(frameIndex: frameIndex, timestamp: timestamp, observations: observations)
    let data = try JSONSerialization.data(withJSONObject: record, options: [.sortedKeys])
    handle.write(data)
    handle.write(Data("\n".utf8))
}

@available(macOS 15.0, *)
func recordFromObservations(frameIndex: Int, timestamp: Double, observations: [HumanBodyPose3DObservation]) -> [String: Any] {
    guard let observation = observations.first else {
        return [
            "frame_idx": frameIndex,
            "timestamp_sec": timestamp,
            "body_detected": false,
            "joints": [String: Any](),
            "api": "DetectHumanBodyPose3DRequest"
        ]
    }
    var joints: [String: Any] = [:]
    for name in observation.availableJointNames {
        if let joint = observation.joint(for: name) {
            let position = joint.position
            joints[name.rawValue] = [
                "x": Double(position.columns.3.x),
                "y": Double(position.columns.3.y),
                "z": Double(position.columns.3.z),
                "confidence": NSNull()
            ]
        }
    }
    return [
        "frame_idx": frameIndex,
        "timestamp_sec": timestamp,
        "body_detected": !joints.isEmpty,
        "joints": joints,
        "raw_joint_names": observation.availableJointNames.map { $0.rawValue },
        "api": "DetectHumanBodyPose3DRequest"
    ]
}

@available(macOS 15.0, *)
func printObservationSummary(_ observations: [HumanBodyPose3DObservation], outputJSONL: String?) {
    let first = observations.first
    var sampleJoint: [String: Any] = [:]
    if let first, let name = first.availableJointNames.first, let joint = first.joint(for: name) {
        sampleJoint = [
            "name": name.rawValue,
            "x": Double(joint.position.columns.3.x),
            "y": Double(joint.position.columns.3.y),
            "z": Double(joint.position.columns.3.z)
        ]
    }
    print([
        "inference_ran": true,
        "api": "DetectHumanBodyPose3DRequest",
        "observation_count": observations.count,
        "joint_names": first?.availableJointNames.map { $0.rawValue } ?? [],
        "first_joint": sampleJoint,
        "output_jsonl": outputJSONL ?? NSNull()
    ] as [String: Any])
}

@available(macOS 15.0, *)
func buildChildArgs(_ args: Arguments, flag: String) -> [String] {
    var result = [flag]
    if let inputVideo = args.inputVideo {
        result += ["--input-video", inputVideo]
    }
    if let inputImage = args.inputImage {
        result += ["--input-image", inputImage]
    }
    if let outputJSONL = args.outputJSONL {
        result += ["--output-jsonl", outputJSONL]
    }
    result += ["--max-frames", String(args.maxFrames), "--stride", String(args.stride)]
    return result
}

struct RuntimeError: Error, LocalizedError {
    let message: String
    init(_ message: String) {
        self.message = message
    }
    var errorDescription: String? { message }
}
