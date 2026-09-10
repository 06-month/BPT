import AVFoundation
internal import Combine
import CoreImage
import CoreML
import SwiftUI
import UIKit

// MARK: - Camera capture manager
//
// Deliberately duplicated (not shared) from CameraPosePreview's private
// CameraCaptureManager: this file is a self-contained, isolated feature so
// the already-shipped exercise pose pipeline can never regress from changes
// made here.

private final class BodyScanCaptureManager: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate, @unchecked Sendable {

    let session = AVCaptureSession()
    private(set) var isFrontCamera = false
    private let processingQueue = DispatchQueue(label: "com.coremlpose.bodyscan.processing", qos: .userInitiated)
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
            throw NSError(domain: "BodyScanCaptureManager", code: 1, userInfo: [NSLocalizedDescriptionKey: "No camera device found (neither front nor back wide angle)."])
        }
        isFrontCamera = (device.position == .front)

        do {
            let input = try AVCaptureDeviceInput(device: device)
            guard session.canAddInput(input) else {
                session.commitConfiguration()
                throw NSError(domain: "BodyScanCaptureManager", code: 2, userInfo: [NSLocalizedDescriptionKey: "Cannot add camera input to session."])
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
            throw NSError(domain: "BodyScanCaptureManager", code: 3, userInfo: [NSLocalizedDescriptionKey: "Cannot add video output to session."])
        }
        session.addOutput(output)

        if let connection = output.connection(with: .video) {
            if connection.isVideoMirroringSupported {
                connection.isVideoMirrored = isFrontCamera
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

// MARK: - Frame data

struct BodyScanFrameData: Identifiable {
    let id: Int
    let imageWidth: Double
    let imageHeight: Double
    let coco17: [PoseKeypoint]
}

private struct BodyScanProcessingResult {
    let frameIndex: Int
    let imageWidth: Double
    let imageHeight: Double
    let coco17: [PoseKeypoint]
    let cgImage: CGImage
}

// MARK: - ViewModel

@MainActor
final class BodyScanViewModel: ObservableObject {
    @Published var currentFrame: BodyScanFrameData?
    @Published var statusText = "Initializing..."
    @Published var cameraPermissionDenied = false

    private let captureManager = BodyScanCaptureManager()
    private let ciContext = CIContext(options: nil)

    var captureSession: AVCaptureSession { captureManager.session }
    var isFrontCamera: Bool { captureManager.isFrontCamera }

    /// (status, countdown, capturedFilePath)
    private let onUpdate: ((String, Int, String?) -> Void)?

    private var rtmpose: MLModel?

    // Stillness tracking (all read/written on the main actor only).
    private var lastCenter: CGPoint?
    private var holdStartTime: CFTimeInterval?
    private var lastCaptureTime: CFTimeInterval?
    private var lastReportedStatus: String?
    private var lastReportedCountdown: Int?

    private let stillnessWindow: CFTimeInterval = 1.0
    private let countdownDuration: CFTimeInterval = 2.0
    private let movementThreshold: Double = 14.0
    private let captureCooldown: CFTimeInterval = 2.5
    private let minConfidence: Double = 0.35
    private let coreKeypointIndices = [5, 6, 11, 12] // shoulders + hips

    init(onUpdate: ((String, Int, String?) -> Void)? = nil) {
        self.onUpdate = onUpdate
    }

    func requestCameraAndStart() {
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

        do {
            try captureManager.configure()
        } catch {
            statusText = "Failed to configure camera: \(error.localizedDescription)"
            return
        }

        let rtmposeModel = self.rtmpose
        let context = self.ciContext

        captureManager.onFrame = { [weak self, context] sampleBuffer, frameIdx in
            guard let self, let rtmposeModel else { return }
            self.processFrame(sampleBuffer, frameIdx: frameIdx, rtmpose: rtmposeModel, ciContext: context)
        }

        captureManager.start()
        statusText = "Running"
    }

    private nonisolated func processFrame(
        _ sampleBuffer: CMSampleBuffer,
        frameIdx: Int,
        rtmpose: MLModel,
        ciContext: CIContext
    ) {
        autoreleasepool {
            do {
                let cgImage = try Self.cgImageFromSampleBuffer(sampleBuffer, ciContext: ciContext)
                let preprocess = try PosePreprocess.preprocessFullImage(cgImage)

                let provider = try MLDictionaryFeatureProvider(dictionary: [
                    "input_image": MLFeatureValue(multiArray: preprocess.inputTensor)
                ])
                let output = try rtmpose.prediction(from: provider)

                guard let simccX = output.featureValue(for: "simcc_x")?.multiArrayValue,
                      let simccY = output.featureValue(for: "simcc_y")?.multiArrayValue else {
                    return
                }

                let decoded = try SimCCDecoder.decodeToInputCoordinates(simccX: simccX, simccY: simccY)
                let coco17 = PoseCoordinateTransforms.applyInverseAffine(
                    decoded: decoded,
                    inverseAffine: preprocess.inverseAffine
                )

                let result = BodyScanProcessingResult(
                    frameIndex: frameIdx,
                    imageWidth: Double(preprocess.imageWidth),
                    imageHeight: Double(preprocess.imageHeight),
                    coco17: coco17,
                    cgImage: cgImage
                )

                Task { @MainActor [weak self] in
                    self?.handleProcessingResult(result)
                }
            } catch {
                // Occasional frame failures are expected (motion blur, etc.) — skip.
            }
        }
    }

    @MainActor
    private func handleProcessingResult(_ result: BodyScanProcessingResult) {
        currentFrame = BodyScanFrameData(
            id: result.frameIndex,
            imageWidth: result.imageWidth,
            imageHeight: result.imageHeight,
            coco17: result.coco17
        )

        let now = CACurrentMediaTime()

        if let lastCapture = lastCaptureTime, now - lastCapture < captureCooldown {
            report(status: "searching", countdown: 0)
            return
        }

        let corePoints: [CGPoint] = coreKeypointIndices.compactMap { idx in
            guard idx < result.coco17.count, result.coco17[idx].confidence >= minConfidence else { return nil }
            return CGPoint(x: result.coco17[idx].x, y: result.coco17[idx].y)
        }

        guard corePoints.count == coreKeypointIndices.count else {
            resetStillness()
            report(status: "searching", countdown: 0)
            return
        }

        let center = CGPoint(
            x: corePoints.map(\.x).reduce(0, +) / CGFloat(corePoints.count),
            y: corePoints.map(\.y).reduce(0, +) / CGFloat(corePoints.count)
        )

        if let last = lastCenter {
            let delta = hypot(center.x - last.x, center.y - last.y)
            if delta > movementThreshold {
                resetStillness()
                lastCenter = center
                report(status: "searching", countdown: 0)
                return
            }
        }
        lastCenter = center

        if holdStartTime == nil {
            holdStartTime = now
        }
        let heldFor = now - (holdStartTime ?? now)

        if heldFor < stillnessWindow {
            report(status: "searching", countdown: 0)
            return
        }

        let countdownElapsed = heldFor - stillnessWindow
        if countdownElapsed >= countdownDuration {
            capture(cgImage: result.cgImage)
            resetStillness()
            lastCaptureTime = now
            return
        }

        let remaining = max(0, Int(ceil(countdownDuration - countdownElapsed)))
        report(status: "holding", countdown: remaining)
    }

    private func resetStillness() {
        holdStartTime = nil
        lastCenter = nil
    }

    private func report(status: String, countdown: Int) {
        guard status != lastReportedStatus || countdown != lastReportedCountdown else { return }
        lastReportedStatus = status
        lastReportedCountdown = countdown
        onUpdate?(status, countdown, nil)
    }

    private func capture(cgImage: CGImage) {
        let uiImage = UIImage(cgImage: cgImage)
        guard let data = uiImage.jpegData(compressionQuality: 0.9) else { return }

        let fileManager = FileManager.default
        guard let documentsDir = fileManager.urls(for: .documentDirectory, in: .userDomainMask).first else { return }
        let scanDir = documentsDir.appendingPathComponent("BodyScan", isDirectory: true)

        do {
            try fileManager.createDirectory(at: scanDir, withIntermediateDirectories: true)
            let fileURL = scanDir.appendingPathComponent("scan_\(Int(Date().timeIntervalSince1970 * 1000)).jpg")
            try data.write(to: fileURL)
            lastReportedStatus = "captured"
            lastReportedCountdown = 0
            onUpdate?("captured", 0, fileURL.path)
        } catch {
            print("BodyScanCameraPreview: failed to save capture: \(error)")
        }
    }

    private func loadModel(named name: String) throws -> MLModel {
        let config = MLModelConfiguration()
        config.computeUnits = .all
        guard let url = Bundle.main.url(forResource: name, withExtension: "mlmodelc")
            ?? Bundle.main.url(forResource: name, withExtension: "mlpackage") else {
            throw NSError(domain: "BodyScanCameraPreview", code: 1, userInfo: [NSLocalizedDescriptionKey: "Missing model: \(name)"])
        }
        return try MLModel(contentsOf: url, configuration: config)
    }

    private nonisolated static func cgImageFromSampleBuffer(
        _ sampleBuffer: CMSampleBuffer,
        ciContext: CIContext
    ) throws -> CGImage {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else {
            throw NSError(domain: "BodyScanCameraPreview", code: 2, userInfo: [NSLocalizedDescriptionKey: "Missing pixel buffer"])
        }
        let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
        guard let cgImage = ciContext.createCGImage(ciImage, from: ciImage.extent) else {
            throw NSError(domain: "BodyScanCameraPreview", code: 3, userInfo: [NSLocalizedDescriptionKey: "CGImage creation failed"])
        }
        return cgImage
    }
}

// MARK: - SwiftUI View

struct BodyScanCameraPreview: View {
    @StateObject private var model: BodyScanViewModel

    init(onUpdate: ((String, Int, String?) -> Void)? = nil) {
        _model = StateObject(wrappedValue: BodyScanViewModel(onUpdate: onUpdate))
    }

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            if model.cameraPermissionDenied {
                VStack(spacing: 12) {
                    Image(systemName: "camera.fill")
                        .font(.largeTitle)
                        .foregroundStyle(.secondary)
                    Text("Camera Access Required")
                        .font(.title3.bold())
                    Text("Enable camera access in Settings to use body scan capture.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                }
            } else {
                BodyScanLiveView(
                    session: model.captureSession,
                    isMirrored: model.isFrontCamera,
                    frame: model.currentFrame,
                    statusText: model.statusText
                )
            }
        }
        .ignoresSafeArea()
        .onAppear {
            model.requestCameraAndStart()
        }
        .onDisappear {
            model.stopCamera()
        }
    }
}

// MARK: - Live camera preview with skeleton overlay

private struct BodyScanLiveView: View {
    let session: AVCaptureSession
    let isMirrored: Bool
    let frame: BodyScanFrameData?
    let statusText: String

    var body: some View {
        GeometryReader { proxy in
            ZStack {
                BodyScanCameraPreviewLayerView(session: session, isMirrored: isMirrored)
                    .frame(width: proxy.size.width, height: proxy.size.height)

                if let frame {
                    Canvas { context, size in
                        drawSkeleton(frame: frame, context: &context, size: size)
                    }
                    .frame(width: proxy.size.width, height: proxy.size.height)
                } else {
                    VStack(spacing: 12) {
                        ProgressView()
                        Text(statusText)
                            .font(.callout)
                            .foregroundStyle(.white.opacity(0.72))
                    }
                    .frame(width: proxy.size.width, height: proxy.size.height)
                }
            }
            .background(Color.black)
            .clipped()
        }
    }

    private func drawSkeleton(frame: BodyScanFrameData, context: inout GraphicsContext, size: CGSize) {
        let rect = aspectFillRect(imageWidth: frame.imageWidth, imageHeight: frame.imageHeight, in: size)
        for edge in coco17Edges {
            guard edge.0 < frame.coco17.count, edge.1 < frame.coco17.count else { continue }
            let a = frame.coco17[edge.0]
            let b = frame.coco17[edge.1]
            guard min(a.confidence, b.confidence) >= 0.3 else { continue }
            var path = Path()
            path.move(to: viewPoint(a, frame: frame, rect: rect))
            path.addLine(to: viewPoint(b, frame: frame, rect: rect))
            context.stroke(path, with: .color(.green), lineWidth: 4.0)
        }

        for keypoint in frame.coco17 where keypoint.confidence >= 0.3 {
            let point = viewPoint(keypoint, frame: frame, rect: rect)
            let radius: CGFloat = 5.0
            let circle = CGRect(x: point.x - radius, y: point.y - radius, width: radius * 2.0, height: radius * 2.0)
            context.fill(Path(ellipseIn: circle), with: .color(.white))
        }
    }

    private func viewPoint(_ keypoint: PoseKeypoint, frame: BodyScanFrameData, rect: CGRect) -> CGPoint {
        CGPoint(
            x: rect.minX + CGFloat(keypoint.x / frame.imageWidth) * rect.width,
            y: rect.minY + CGFloat(keypoint.y / frame.imageHeight) * rect.height
        )
    }

    private func aspectFillRect(imageWidth: Double, imageHeight: Double, in size: CGSize) -> CGRect {
        guard imageWidth > 0, imageHeight > 0, size.width > 0, size.height > 0 else {
            return .zero
        }
        let scale = max(size.width / CGFloat(imageWidth), size.height / CGFloat(imageHeight))
        let width = CGFloat(imageWidth) * scale
        let height = CGFloat(imageHeight) * scale
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

private struct BodyScanCameraPreviewLayerView: UIViewRepresentable {
    let session: AVCaptureSession
    let isMirrored: Bool

    func makeUIView(context: Context) -> BodyScanCameraPreviewUIView {
        let view = BodyScanCameraPreviewUIView()
        view.configure(session: session, isMirrored: isMirrored)
        return view
    }

    func updateUIView(_ uiView: BodyScanCameraPreviewUIView, context: Context) {
        uiView.configure(session: session, isMirrored: isMirrored)
    }
}

private final class BodyScanCameraPreviewUIView: UIView {
    override class var layerClass: AnyClass {
        AVCaptureVideoPreviewLayer.self
    }

    private var previewLayer: AVCaptureVideoPreviewLayer {
        layer as! AVCaptureVideoPreviewLayer
    }

    func configure(session: AVCaptureSession, isMirrored: Bool) {
        if previewLayer.session !== session {
            previewLayer.session = session
        }
        previewLayer.videoGravity = .resizeAspectFill

        guard let connection = previewLayer.connection else { return }
        if connection.isVideoOrientationSupported {
            connection.videoOrientation = .portrait
        }
        if connection.isVideoMirroringSupported {
            connection.automaticallyAdjustsVideoMirroring = false
            connection.isVideoMirrored = isMirrored
        }
    }
}
