import Flutter

enum NativePoseRegistration {
    static let viewType = "bpt/native_pose_camera"
    static let bodyScanViewType = "bpt/body_scan_camera"

    static func register(with registry: FlutterPluginRegistry) {
        if let registrar = registry.registrar(forPlugin: "NativePoseCameraPlatformView") {
            registrar.register(
                NativePoseCameraPlatformViewFactory(messenger: registrar.messenger()),
                withId: viewType
            )
        }

        if let registrar = registry.registrar(forPlugin: "BodyScanCameraPlatformView") {
            registrar.register(
                BodyScanCameraPlatformViewFactory(messenger: registrar.messenger()),
                withId: bodyScanViewType
            )
        }
    }
}
