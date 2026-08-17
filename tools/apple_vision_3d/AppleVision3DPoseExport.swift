import AVFoundation
import CoreImage
import CoreMedia
import Foundation
import simd
import Vision

struct Arguments {
    var inputVideo: String = ""
    var outputJSONL: String = ""
    var maxFrames: Int = 0
    var stride: Int = 1
    var diagnoseOnly: Bool = false
    var probe3DChild: Bool = false
    var probe2DChild: Bool = false
    var probe3DRevisionsChild: Bool = false
    var probe2DRevisionsChild: Bool = false
}

func parseArguments() -> Arguments? {
    var args = Arguments()
    var index = 1
    let values = CommandLine.arguments
    while index < values.count {
        let key = values[index]
        let next = index + 1 < values.count ? values[index + 1] : nil
        switch key {
        case "--input-video":
            guard let next else { return nil }
            args.inputVideo = next
            index += 2
        case "--output-jsonl":
            guard let next else { return nil }
            args.outputJSONL = next
            index += 2
        case "--max-frames":
            guard let next, let value = Int(next) else { return nil }
            args.maxFrames = value
            index += 2
        case "--stride":
            guard let next, let value = Int(next), value > 0 else { return nil }
            args.stride = value
            index += 2
        case "--diagnose-only":
            args.diagnoseOnly = true
            index += 1
        case "--probe-3d-child":
            args.probe3DChild = true
            index += 1
        case "--probe-2d-child":
            args.probe2DChild = true
            index += 1
        case "--probe-3d-revisions-child":
            args.probe3DRevisionsChild = true
            index += 1
        case "--probe-2d-revisions-child":
            args.probe2DRevisionsChild = true
            index += 1
        default:
            return nil
        }
    }
    if !args.diagnoseOnly && !args.probe3DChild && !args.probe2DChild && !args.probe3DRevisionsChild && !args.probe2DRevisionsChild && (args.inputVideo.isEmpty || args.outputJSONL.isEmpty) {
        return nil
    }
    return args
}

func printUsage() {
    fputs("""
    Usage:
      apple_vision_3d_export --input-video path --output-jsonl path [--max-frames N] [--stride N]
      apple_vision_3d_export --diagnose-only

    """, stderr)
}

@available(macOS 14.0, *)
func exportPose(args: Arguments) throws {
    let diagnosis = diagnoseRuntimeSupport()
    guard diagnosis.threeDWorks else {
        if diagnosis.twoDWorks {
            print("Vision framework is available; 2D pose works; 3D pose model initialization fails in current runtime.")
        }
        throw RuntimeError("Apple Vision 3D request construction failed. Video processing was not started.")
    }

    let inputURL = URL(fileURLWithPath: args.inputVideo)
    let outputURL = URL(fileURLWithPath: args.outputJSONL)
    try FileManager.default.createDirectory(
        at: outputURL.deletingLastPathComponent(),
        withIntermediateDirectories: true
    )
    FileManager.default.createFile(atPath: outputURL.path, contents: nil)
    let handle = try FileHandle(forWritingTo: outputURL)
    defer { try? handle.close() }

    let asset = AVAsset(url: inputURL)
    guard let track = asset.tracks(withMediaType: .video).first else {
        throw RuntimeError("No video track found: \(args.inputVideo)")
    }
    let naturalSize = track.naturalSize.applying(track.preferredTransform)
    let imageWidth = abs(Double(naturalSize.width))
    let imageHeight = abs(Double(naturalSize.height))

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

    let request = VNDetectHumanBodyPose3DRequest()
    var frameIndex = 0
    var processed = 0
    var detected = 0

    guard reader.startReading() else {
        throw RuntimeError("AVAssetReader failed to start")
    }

    while let sampleBuffer = output.copyNextSampleBuffer() {
        defer { frameIndex += 1 }
        if frameIndex % args.stride != 0 {
            continue
        }
        if args.maxFrames > 0 && processed >= args.maxFrames {
            break
        }
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else {
            continue
        }
        let timestamp = CMSampleBufferGetPresentationTimeStamp(sampleBuffer).seconds
        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: .up)
        var record: [String: Any] = [
            "frame_idx": frameIndex,
            "timestamp_sec": timestamp,
            "body_detected": false,
            "joints": [String: Any](),
            "raw_joint_names": [String](),
            "image_width": imageWidth,
            "image_height": imageHeight
        ]

        do {
            try handler.perform([request])
            if let observation = request.results?.first {
                detected += 1
                record = recordFromObservation(
                    observation,
                    frameIndex: frameIndex,
                    timestamp: timestamp,
                    imageWidth: imageWidth,
                    imageHeight: imageHeight
                )
            }
        } catch {
            record["error"] = "\(type(of: error)): \(error.localizedDescription)"
        }

        try writeJSONLine(record, to: handle)
        processed += 1
    }

    print([
        "input_video": args.inputVideo,
        "output_jsonl": args.outputJSONL,
        "processed_frames": processed,
        "detected_frames": detected
    ] as [String : Any])
}

struct ProbeResult {
    let works: Bool
    let terminationStatus: Int32
    let terminationReason: String
    let output: String
}

struct DiagnosisResult {
    let twoDWorks: Bool
    let threeDWorks: Bool
}

func printProcessInfo() {
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
        "diagnostic": "process_info",
        "macos_version": info.operatingSystemVersionString,
        "architecture": arch,
        "process_id": info.processIdentifier,
        "process_name": info.processName,
        "host_name": info.hostName,
        "active_processor_count": info.activeProcessorCount
    ] as [String : Any])
}

@available(macOS 14.0, *)
func printVisionRevisionInfo() {
    let threeD = runProbeChild("--probe-3d-revisions-child", captureOutput: true)
    print([
        "diagnostic": "vision_3d_revisions",
        "available": threeD.works,
        "termination_status": threeD.terminationStatus,
        "termination_reason": threeD.terminationReason,
        "output": threeD.output
    ] as [String : Any])
    let twoD = runProbeChild("--probe-2d-revisions-child", captureOutput: true)
    print([
        "diagnostic": "vision_2d_revisions",
        "available": twoD.works,
        "termination_status": twoD.terminationStatus,
        "termination_reason": twoD.terminationReason,
        "output": twoD.output
    ] as [String : Any])
}

@available(macOS 14.0, *)
func diagnoseRuntimeSupport() -> DiagnosisResult {
    printProcessInfo()
    printVisionRevisionInfo()
    let twoD = runProbeChild("--probe-2d-child", captureOutput: false)
    print([
        "diagnostic": "vision_2d_request_probe",
        "works": twoD.works,
        "termination_status": twoD.terminationStatus,
        "termination_reason": twoD.terminationReason
    ] as [String : Any])
    let threeD = runProbeChild("--probe-3d-child", captureOutput: false)
    print([
        "diagnostic": "vision_3d_request_probe",
        "works": threeD.works,
        "termination_status": threeD.terminationStatus,
        "termination_reason": threeD.terminationReason
    ] as [String : Any])
    if !threeD.works && twoD.works {
        print([
            "vision_framework_available": true,
            "vision_2d_pose_works": true,
            "vision_3d_pose_model_initialization": "failed_current_runtime"
        ] as [String : Any])
    }
    return DiagnosisResult(twoDWorks: twoD.works, threeDWorks: threeD.works)
}

func runProbeChild(_ flag: String, captureOutput: Bool) -> ProbeResult {
    guard let executableURL = Bundle.main.executableURL else {
        return ProbeResult(works: false, terminationStatus: -1, terminationReason: "missing_executable_url", output: "")
    }
    let process = Process()
    process.executableURL = executableURL
    process.arguments = [flag]
    let pipe = Pipe()
    if captureOutput {
        process.standardOutput = pipe
        process.standardError = pipe
    } else {
        process.standardOutput = FileHandle.nullDevice
        process.standardError = FileHandle.nullDevice
    }
    do {
        try process.run()
        process.waitUntilExit()
        let output: String
        if captureOutput {
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        } else {
            output = ""
        }
        let reason: String
        switch process.terminationReason {
        case .exit:
            reason = "exit"
        case .uncaughtSignal:
            reason = "uncaught_signal"
        @unknown default:
            reason = "unknown"
        }
        return ProbeResult(
            works: process.terminationReason == .exit && process.terminationStatus == 0,
            terminationStatus: process.terminationStatus,
            terminationReason: reason,
            output: output
        )
    } catch {
        return ProbeResult(works: false, terminationStatus: -1, terminationReason: "\(type(of: error)): \(error.localizedDescription)", output: "")
    }
}

@available(macOS 14.0, *)
func run2DProbeChild() {
    _ = VNDetectHumanBodyPoseRequest()
    print("vision_2d_request_constructed=true")
}

@available(macOS 14.0, *)
func run3DProbeChild() {
    let request = VNDetectHumanBodyPose3DRequest()
    print("vision_3d_request_constructed=true revision=\(request.revision)")
}

@available(macOS 14.0, *)
func run2DRevisionsProbeChild() {
    print([
        "supported_revisions": String(describing: VNDetectHumanBodyPoseRequest.supportedRevisions),
        "default_revision": VNDetectHumanBodyPoseRequest.defaultRevision
    ] as [String : Any])
}

@available(macOS 14.0, *)
func run3DRevisionsProbeChild() {
    print([
        "supported_revisions": String(describing: VNDetectHumanBodyPose3DRequest.supportedRevisions),
        "default_revision": VNDetectHumanBodyPose3DRequest.defaultRevision
    ] as [String : Any])
}

@available(macOS 14.0, *)
func recordFromObservation(
    _ observation: VNHumanBodyPose3DObservation,
    frameIndex: Int,
    timestamp: Double,
    imageWidth: Double,
    imageHeight: Double
) -> [String: Any] {
    var joints: [String: Any] = [:]
    let jointNames = observation.availableJointNames
    for jointName in jointNames {
        let name = String(describing: jointName.rawValue)
        var jointRecord: [String: Any] = [:]
        if let point = try? observation.recognizedPoint(jointName) {
            let position = point.position
            jointRecord["x"] = Double(position.columns.3.x)
            jointRecord["y"] = Double(position.columns.3.y)
            jointRecord["z"] = Double(position.columns.3.z)
            jointRecord["confidence"] = NSNull()
            let local = point.localPosition
            jointRecord["local_x"] = Double(local.columns.3.x)
            jointRecord["local_y"] = Double(local.columns.3.y)
            jointRecord["local_z"] = Double(local.columns.3.z)
        }
        if let projected = try? observation.pointInImage(jointName) {
            let normalizedX = Double(projected.x)
            let normalizedY = Double(projected.y)
            jointRecord["image_x_norm"] = normalizedX
            jointRecord["image_y_norm"] = normalizedY
            jointRecord["image_x"] = normalizedX * imageWidth
            jointRecord["image_y"] = (1.0 - normalizedY) * imageHeight
        }
        if !jointRecord.isEmpty {
            joints[name] = jointRecord
        }
    }
    return [
        "frame_idx": frameIndex,
        "timestamp_sec": timestamp,
        "body_detected": !joints.isEmpty,
        "joints": joints,
        "raw_joint_names": jointNames.map { String(describing: $0.rawValue) },
        "image_width": imageWidth,
        "image_height": imageHeight,
        "body_height_m": Double(observation.bodyHeight),
        "height_estimation": "\(observation.heightEstimation)"
    ]
}

func writeJSONLine(_ object: [String: Any], to handle: FileHandle) throws {
    let data = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
    handle.write(data)
    handle.write(Data("\n".utf8))
}

struct RuntimeError: Error, CustomStringConvertible {
    let message: String
    init(_ message: String) {
        self.message = message
    }
    var description: String { message }
}

guard let args = parseArguments() else {
    printUsage()
    exit(2)
}

if #available(macOS 14.0, *) {
    if args.probe2DChild {
        run2DProbeChild()
        exit(0)
    }
    if args.probe3DChild {
        run3DProbeChild()
        exit(0)
    }
    if args.probe2DRevisionsChild {
        run2DRevisionsProbeChild()
        exit(0)
    }
    if args.probe3DRevisionsChild {
        run3DRevisionsProbeChild()
        exit(0)
    }
    if args.diagnoseOnly {
        let diagnosis = diagnoseRuntimeSupport()
        print([
            "diagnose_only": true,
            "vision_2d_pose_works": diagnosis.twoDWorks,
            "vision_3d_pose_works": diagnosis.threeDWorks
        ] as [String : Any])
        exit(0)
    }
    do {
        try exportPose(args: args)
    } catch {
        fputs("apple_vision_3d_export failed: \(error)\n", stderr)
        exit(1)
    }
} else {
    fputs("VNDetectHumanBodyPose3DRequest requires macOS 14.0 or newer.\n", stderr)
    exit(0)
}
