import Flutter
import SwiftUI
import UIKit

/// Hosts `BodyScanCameraPreview` (live camera + RTMPose skeleton + stillness
/// auto-capture) as a Flutter platform view. Reports status/countdown/capture
/// events to Dart over `bpt/body_scan_camera/<viewId>` via `onScanUpdate`.
final class BodyScanCameraPlatformView: NSObject, FlutterPlatformView {
    private let hostingController: UIHostingController<BodyScanCameraPreview>
    private let channel: FlutterMethodChannel

    init(frame: CGRect, viewId: Int64, messenger: FlutterBinaryMessenger) {
        let channel = FlutterMethodChannel(
            name: "bpt/body_scan_camera/\(viewId)",
            binaryMessenger: messenger
        )
        self.channel = channel

        let rootView = BodyScanCameraPreview { status, countdown, path in
            channel.invokeMethod(
                "onScanUpdate",
                arguments: ["status": status, "countdown": countdown, "path": path as Any]
            )
        }

        hostingController = UIHostingController(rootView: rootView)
        super.init()

        hostingController.view.frame = frame
        hostingController.view.backgroundColor = .black
        hostingController.view.autoresizingMask = [.flexibleWidth, .flexibleHeight]
    }

    func view() -> UIView {
        hostingController.view
    }
}
