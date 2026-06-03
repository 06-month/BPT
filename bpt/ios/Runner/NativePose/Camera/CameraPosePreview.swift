import AVFoundation
internal import Combine
import CoreImage
import CoreML
import SwiftUI
import UIKit

// MARK: - Options

private enum CameraPreviewOptions {
    static let enableHandBranchForCamera = true
    static let enableMotion3DForCamera = false
    static let handCropSize = 256.0
    static let wristConfidenceThreshold = 0.3
    static let useMediaPipeWristFor2DBodyOverlay = true
    static let debugLogEveryNFrames = 60
}

// MARK: - Frame data (lightweight, no arrays)

struct CameraFrameData: Identifiable {
    let id: Int
    let frameIndex: Int
    let image: UIImage
    let imageWidth: Double
    let imageHeight: Double
    let coco17: [PoseKeypoint]
    let rawCoco17: [PoseKeypoint]
    let handResults: [HandLandmarkResult]
    let exerciseTitle: String
    let statusText: String
    let rep: Int
    let done: Bool
}

struct CameraProcessingResult {
    let frameIndex: Int
    let image: UIImage
    let imageWidth: Double
    let imageHeight: Double
    let visualCoco17: [PoseKeypoint]
    let rawCoco17: [PoseKeypoint]
    let handResults: [HandLandmarkResult]
}

// MARK: - Camera capture manager

private final class CameraCaptureManager: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate, @unchecked Sendable {

    let session = AVCaptureSession()
    private let processingQueue = DispatchQueue(label: "com.coremlpose.camera.processing", qos: .userInitiated)
    nonisolated(unsafe) private var isProcessingFrame = false
    nonisolated(unsafe) private var frameIndex = 0
    nonisolated(unsafe) var onFrame: (@Sendable (CMSampleBuffer, Int) -> Void)?

    func configure() throws {
        session.beginConfiguration()
        session.sessionPreset = .hd1280x720

        let preferredDevice = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .front)
            ?? AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back)

        guard let device = preferredDevice else {
            session.commitConfiguration()
            throw NSError(domain: "CameraCaptureManager", code: 1, userInfo: [NSLocalizedDescriptionKey: "No camera device found (neither front nor back wide angle)."])
        }

        do {
            let input = try AVCaptureDeviceInput(device: device)
            guard session.canAddInput(input) else {
                session.commitConfiguration()
                throw NSError(domain: "CameraCaptureManager", code: 2, userInfo: [NSLocalizedDescriptionKey: "Cannot add camera input to session."])
            }
            session.addInput(input)
        } catch {
            session.commitConfiguration()
            throw error
        }

        let output = AVCaptureVideoDataOutput()
        output.videoSettings = [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA
        ]
        output.setSampleBufferDelegate(self, queue: processingQueue)
        guard session.canAddOutput(output) else {
            session.commitConfiguration()
            throw NSError(domain: "CameraCaptureManager", code: 3, userInfo: [NSLocalizedDescriptionKey: "Cannot add video output to session."])
        }
        session.addOutput(output)

        if let connection = output.connection(with: .video) {
            if connection.isVideoMirroringSupported {
                connection.isVideoMirrored = (device.position == .front)
            }
            if connection.isVideoOrientationSupported {
                connection.videoOrientation = .portrait
            }
        }

        session.commitConfiguration()
    }

    func start() {
        processingQueue.async { [weak self] in
            self?.session.startRunning()
        }
    }

    func stop() {
        processingQueue.async { [weak self] in
            self?.session.stopRunning()
        }
    }

    nonisolated func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        guard !isProcessingFrame else { return }
        isProcessingFrame = true
        let idx = frameIndex
        frameIndex += 1
        onFrame?(sampleBuffer, idx)
        isProcessingFrame = false
    }
}

// MARK: - ViewModel

@MainActor
final class CameraPoseViewModel: ObservableObject {
    @Published var currentFrame: CameraFrameData?
    @Published var statusText = "Initializing..."
    @Published var cameraPermissionDenied = false
    @Published var cameraSetupError: String? = nil

    private let exercise: NativePoseExercise
    private let captureManager = CameraCaptureManager()
    private let ciContext = CIContext(options: nil)

    // Reports rep/status changes to Flutter (HUD is rendered on the Flutter side).
    private let onUpdate: ((Int, String, Bool) -> Void)?
    private var lastReportedRep: Int?
    private var lastReportedStatus: String?
    private var lastReportedDone: Bool?

    // Models (loaded once)
    private var rtmpose: MLModel?
    private var handLandmarkers: MediaPipeHandLandmarkerPair?

    // Evaluators (only one active)
    private var deadliftEvaluator: DeadliftEvaluator?
    private var benchPressEvaluator: BenchPressEvaluator?
    private var squatEvaluator: SquatEvaluator?
    private var barbellRowEvaluator: BarbellRowEvaluator?
    private var pushUpEvaluator: PushUpEvaluator?

    init(exercise: NativePoseExercise, onUpdate: ((Int, String, Bool) -> Void)? = nil) {
        self.exercise = exercise
        self.onUpdate = onUpdate
    }

    func requestCameraAndStart() {
        #if targetEnvironment(simulator)
        self.cameraSetupError = "simulator"
        return
        #endif
        AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
            Task { @MainActor in
                guard let self else { return }
                if granted {
                    self.setup()
                } else {
                    self.cameraPermissionDenied = true
                    self.statusText = "Camera permission denied"
                }
            }
        }
    }

    func stopCamera() {
        captureManager.stop()
    }

    private func setup() {
        do {
            rtmpose = try loadModel(named: "rtmpose_s_forward")
        } catch {
            statusText = "Failed to load RTMPose: \(error.localizedDescription)"
            return
        }

        switch exercise {
        case .deadlift: deadliftEvaluator = DeadliftEvaluator()
        case .benchPress: benchPressEvaluator = BenchPressEvaluator()
        case .squat: squatEvaluator = SquatEvaluator()
        case .barbellRow: barbellRowEvaluator = BarbellRowEvaluator()
        case .pushUp: pushUpEvaluator = PushUpEvaluator()
        }

        if CameraPreviewOptions.enableHandBranchForCamera {
            handLandmarkers = MediaPipeHandLandmarkerPair()
            print("CameraPosePreview hand landmarkers initialized: \(handLandmarkers?.statusDescription ?? "nil")")
        }

        do {
            try captureManager.configure()
        } catch {
            cameraSetupError = error.localizedDescription
            return
        }

        let rtmposeModel = self.rtmpose
        let handLandmarkRunner = self.handLandmarkers
        let context = self.ciContext

        captureManager.onFrame = { [weak self, context] sampleBuffer, frameIdx in
            guard let self, let rtmposeModel else { return }
            self.processFrame(
                sampleBuffer,
                frameIdx: frameIdx,
                rtmpose: rtmposeModel,
                handLandmarkers: handLandmarkRunner,
                ciContext: context
            )
        }

        captureManager.start()
        statusText = "Running"
        print("CameraPosePreview started exercise=\(exercise.rawValue) hand=\(CameraPreviewOptions.enableHandBranchForCamera) 3d=\(CameraPreviewOptions.enableMotion3DForCamera)")
    }

    private nonisolated func processFrame(
        _ sampleBuffer: CMSampleBuffer,
        frameIdx: Int,
        rtmpose: MLModel,
        handLandmarkers: MediaPipeHandLandmarkerPair?,
        ciContext: CIContext
    ) {
        autoreleasepool {
            do {
                let timestampMs = Self.timestampMs(sampleBuffer, fallback: frameIdx)
                let cgImage = try Self.cgImageFromSampleBuffer(sampleBuffer, ciContext: ciContext)
                let preprocess = try PosePreprocess.preprocessFullImage(cgImage)

                let rtmposeProvider = try MLDictionaryFeatureProvider(dictionary: [
                    "input_image": MLFeatureValue(multiArray: preprocess.inputTensor)
                ])
                let rtmposeOutput = try rtmpose.prediction(from: rtmposeProvider)

                guard let simccX = rtmposeOutput.featureValue(for: "simcc_x")?.multiArrayValue,
                      let simccY = rtmposeOutput.featureValue(for: "simcc_y")?.multiArrayValue else {
                    return
                }

                let decoded = try SimCCDecoder.decodeToInputCoordinates(simccX: simccX, simccY: simccY)
                let rawCoco17 = PoseCoordinateTransforms.applyInverseAffine(
                    decoded: decoded,
                    inverseAffine: preprocess.inverseAffine
                )

                // Hand branch
                let handResults: [HandLandmarkResult]
                let leftHand: HandLandmarkResult?
                let rightHand: HandLandmarkResult?
                if CameraPreviewOptions.enableHandBranchForCamera,
                   let handLandmarkers = handLandmarkers {
                    let handImage = UIImage(cgImage: cgImage)
                    let handFrame = BundledVideoHandFrameProcessor.runWristCropHands(
                        image: handImage,
                        rawCoco17: rawCoco17,
                        imageWidth: Double(preprocess.imageWidth),
                        imageHeight: Double(preprocess.imageHeight),
                        timestampMs: timestampMs,
                        handLandmarkers: handLandmarkers,
                        cropSize: CameraPreviewOptions.handCropSize,
                        confidenceThreshold: CameraPreviewOptions.wristConfidenceThreshold
                    )
                    handResults = handFrame.handResults
                    leftHand = handFrame.leftHand
                    rightHand = handFrame.rightHand
                } else {
                    handResults = []
                    leftHand = nil
                    rightHand = nil
                }

                let visualCoco17 = HandCropBuilder.visualBodyKeypoints(
                    rawBodyKeypoints: rawCoco17,
                    leftHand: leftHand,
                    rightHand: rightHand,
                    useMediaPipeWrist: CameraPreviewOptions.useMediaPipeWristFor2DBodyOverlay
                )

                let result = CameraProcessingResult(
                    frameIndex: frameIdx,
                    image: UIImage(cgImage: cgImage),
                    imageWidth: Double(preprocess.imageWidth),
                    imageHeight: Double(preprocess.imageHeight),
                    visualCoco17: visualCoco17,
                    rawCoco17: rawCoco17,
                    handResults: handResults
                )

                Task { @MainActor [weak self] in
                    self?.handleProcessingResult(result)
                }
            } catch {
                if frameIdx % CameraPreviewOptions.debugLogEveryNFrames == 0 {
                    print("CameraPosePreview frame processing error: \(error)")
                }
            }
        }
    }

    @MainActor
    private func handleProcessingResult(_ result: CameraProcessingResult) {
        let (statusText, rep, done) = self.runEvaluator(frameIndex: result.frameIndex, rawCoco17: result.rawCoco17)

        let frameData = CameraFrameData(
            id: result.frameIndex,
            frameIndex: result.frameIndex,
            image: result.image,
            imageWidth: result.imageWidth,
            imageHeight: result.imageHeight,
            coco17: result.visualCoco17,
            rawCoco17: result.rawCoco17,
            handResults: result.handResults,
            exerciseTitle: self.exercise.displayName,
            statusText: statusText,
            rep: rep,
            done: done
        )

        self.currentFrame = frameData

        // Only notify Flutter when the meaningful state actually changes.
        if rep != lastReportedRep || statusText != lastReportedStatus || done != lastReportedDone {
            lastReportedRep = rep
            lastReportedStatus = statusText
            lastReportedDone = done
            onUpdate?(rep, statusText, done)
        }

        if result.frameIndex % CameraPreviewOptions.debugLogEveryNFrames == 0 {
            print("CameraPosePreview frame=\(result.frameIndex) exercise=\(self.exercise.rawValue) status=\(statusText) rep=\(rep) done=\(done) hands=\(result.handResults.count)")
        }
    }

    private func runEvaluator(frameIndex: Int, rawCoco17: [PoseKeypoint]) -> (status: String, rep: Int, done: Bool) {
        switch exercise {
        case .deadlift:
            if let eval = deadliftEvaluator {
                let r = eval.evaluate(frameIndex: frameIndex, coco17: rawCoco17)
                return (r.status.rawValue, r.rep, r.done)
            }
        case .benchPress:
            if let eval = benchPressEvaluator {
                let r = eval.evaluate(frameIndex: frameIndex, coco17: rawCoco17)
                return (r.status.rawValue, r.rep, r.done)
            }
        case .squat:
            if let eval = squatEvaluator {
                let r = eval.evaluate(frameIndex: frameIndex, coco17: rawCoco17)
                return (r.status.rawValue, r.rep, r.done)
            }
        case .barbellRow:
            if let eval = barbellRowEvaluator {
                let r = eval.evaluate(frameIndex: frameIndex, coco17: rawCoco17)
                return (r.status.rawValue, r.rep, r.done)
            }
        case .pushUp:
            if let eval = pushUpEvaluator {
                let r = eval.evaluate(frameIndex: frameIndex, coco17: rawCoco17)
                return (r.status.rawValue, r.rep, r.done)
            }
        }
        return ("inactive", 0, false)
    }

    private func loadModel(named name: String) throws -> MLModel {
        let config = MLModelConfiguration()
        config.computeUnits = .all
        guard let url = Bundle.main.url(forResource: name, withExtension: "mlmodelc")
            ?? Bundle.main.url(forResource: name, withExtension: "mlpackage") else {
            throw NSError(domain: "CameraPosePreview", code: 1, userInfo: [NSLocalizedDescriptionKey: "Missing model: \(name)"])
        }
        return try MLModel(contentsOf: url, configuration: config)
    }

    private nonisolated static func cgImageFromSampleBuffer(
        _ sampleBuffer: CMSampleBuffer,
        ciContext: CIContext
    ) throws -> CGImage {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else {
            throw NSError(domain: "CameraPosePreview", code: 2, userInfo: [NSLocalizedDescriptionKey: "Missing pixel buffer"])
        }
        let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
        guard let cgImage = ciContext.createCGImage(ciImage, from: ciImage.extent) else {
            throw NSError(domain: "CameraPosePreview", code: 3, userInfo: [NSLocalizedDescriptionKey: "CGImage creation failed"])
        }
        return cgImage
    }

    private nonisolated static func timestampMs(_ sampleBuffer: CMSampleBuffer, fallback: Int) -> Int {
        let timestamp = CMSampleBufferGetPresentationTimeStamp(sampleBuffer)
        let seconds = CMTimeGetSeconds(timestamp)
        if seconds.isFinite && seconds >= 0.0 {
            return Int((seconds * 1000.0).rounded())
        }
        return fallback * 33
    }
}

// MARK: - SwiftUI View

struct CameraPosePreview: View {
    let exercise: NativePoseExercise
    @StateObject private var model: CameraPoseViewModel

    init(exercise: NativePoseExercise, onUpdate: ((Int, String, Bool) -> Void)? = nil) {
        self.exercise = exercise
        _model = StateObject(wrappedValue: CameraPoseViewModel(exercise: exercise, onUpdate: onUpdate))
    }

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            if let error = model.cameraSetupError {
                // 시뮬레이터 또는 카메라 초기화 실패
                VStack(spacing: 16) {
                    Image(systemName: error == "simulator" ? "iphone.slash" : "camera.slash.fill")
                        .font(.system(size: 52))
                        .foregroundStyle(.white.opacity(0.7))
                    Text(error == "simulator"
                         ? "시뮬레이터에서는\n카메라를 사용할 수 없습니다"
                         : "카메라를 시작할 수 없습니다")
                        .font(.title3.bold())
                        .foregroundStyle(.white)
                        .multilineTextAlignment(.center)
                    Text(error == "simulator"
                         ? "실기기에서 테스트해 주세요."
                         : error)
                        .font(.subheadline)
                        .foregroundStyle(.white.opacity(0.55))
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 32)
                }
            } else if model.cameraPermissionDenied {
                VStack(spacing: 16) {
                    Image(systemName: "camera.fill")
                        .font(.system(size: 52))
                        .foregroundStyle(.white.opacity(0.7))
                    Text("카메라 권한이 필요합니다")
                        .font(.title3.bold())
                        .foregroundStyle(.white)
                    Text("설정 앱에서 카메라 접근을 허용해주세요.")
                        .font(.subheadline)
                        .foregroundStyle(.white.opacity(0.55))
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 32)
                }
            } else if let frame = model.currentFrame {
                CameraFrameView(frame: frame)
            } else {
                VStack(spacing: 12) {
                    ProgressView()
                        .tint(.white)
                    Text(model.statusText)
                        .font(.callout)
                        .foregroundStyle(.white.opacity(0.7))
                }
            }
        }
        .navigationTitle(exercise.displayName)
        .navigationBarTitleDisplayMode(.inline)
        .onAppear {
            model.requestCameraAndStart()
        }
        .onDisappear {
            model.stopCamera()
        }
    }
}

// MARK: - Frame view with overlays

private struct CameraFrameView: View {
    let frame: CameraFrameData

    var body: some View {
        GeometryReader { proxy in
            ZStack(alignment: .topLeading) {
                Image(uiImage: frame.image)
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(width: proxy.size.width, height: proxy.size.height)

                Canvas { context, size in
                    drawSkeleton(context: &context, size: size)
                    drawHands(context: &context, size: size)
                }
                .frame(width: proxy.size.width, height: proxy.size.height)

                // HUD (rep/status) is rendered by Flutter at the bottom of the
                // screen — intentionally no native top-left overlay here.
            }
        }
    }

    private func drawSkeleton(context: inout GraphicsContext, size: CGSize) {
        let rect = aspectFitRect(imageWidth: frame.imageWidth, imageHeight: frame.imageHeight, in: size)
        for edge in coco17Edges {
            guard edge.0 < frame.coco17.count, edge.1 < frame.coco17.count else { continue }
            let a = frame.coco17[edge.0]
            let b = frame.coco17[edge.1]
            let minConfidence = min(a.confidence, b.confidence)
            let color = minConfidence >= 0.3 ? Color.green : Color.gray.opacity(0.35)
            var path = Path()
            path.move(to: viewPoint(a, rect: rect))
            path.addLine(to: viewPoint(b, rect: rect))
            context.stroke(path, with: .color(color), lineWidth: minConfidence >= 0.3 ? 4.0 : 2.0)
        }

        for keypoint in frame.coco17 {
            let point = viewPoint(keypoint, rect: rect)
            let radius = keypoint.confidence >= 0.3 ? 5.0 : 3.0
            let color = keypoint.confidence >= 0.3 ? Color.yellow : Color.gray.opacity(0.35)
            let circle = CGRect(x: point.x - radius, y: point.y - radius, width: radius * 2.0, height: radius * 2.0)
            context.fill(Path(ellipseIn: circle), with: .color(color))
        }
    }

    private func drawHands(context: inout GraphicsContext, size: CGSize) {
        let rect = aspectFitRect(imageWidth: frame.imageWidth, imageHeight: frame.imageHeight, in: size)
        HandOverlayRenderer.drawHands(
            frame.handResults,
            context: &context,
            imageWidth: frame.imageWidth,
            imageHeight: frame.imageHeight,
            rect: rect
        )
    }

    private func viewPoint(_ keypoint: PoseKeypoint, rect: CGRect) -> CGPoint {
        CGPoint(
            x: rect.minX + CGFloat(keypoint.x / frame.imageWidth) * rect.width,
            y: rect.minY + CGFloat(keypoint.y / frame.imageHeight) * rect.height
        )
    }

    private func aspectFitRect(imageWidth: Double, imageHeight: Double, in size: CGSize) -> CGRect {
        let scale = min(size.width / imageWidth, size.height / imageHeight)
        let width = imageWidth * scale
        let height = imageHeight * scale
        return CGRect(
            x: (size.width - width) * 0.5,
            y: (size.height - height) * 0.5,
            width: width,
            height: height
        )
    }

    private var coco17Edges: [(Int, Int)] {
        [
            (0, 1), (0, 2), (1, 3), (2, 4),
            (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
            (5, 11), (6, 12), (11, 12),
            (11, 13), (13, 15), (12, 14), (14, 16),
        ]
    }
}

// MARK: - HUD

private struct CameraHUD: View {
    let frame: CameraFrameData

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(frame.exerciseTitle.capitalized)
                .font(.caption.bold())
                .foregroundStyle(.white)

            Text("Status: \(frame.statusText)")
                .font(.caption2.monospacedDigit())
                .foregroundStyle(.white.opacity(0.92))

            Text("Rep: \(frame.rep)  Done: \(frame.done ? "yes" : "no")")
                .font(.caption2.monospacedDigit())
                .foregroundStyle(.white.opacity(0.92))

            Text("Hands: \(frame.handResults.count)  Frame: \(frame.frameIndex)")
                .font(.caption2.monospacedDigit())
                .foregroundStyle(.white.opacity(0.7))
        }
        .padding(8)
        .background(Color.black.opacity(0.68))
        .clipShape(RoundedRectangle(cornerRadius: 6))
    }
}
