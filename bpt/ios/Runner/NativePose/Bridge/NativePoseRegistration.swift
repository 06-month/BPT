import Flutter

enum NativePoseRegistration {
    static let viewType = "bpt/native_pose_camera"

    static func register(with registry: FlutterPluginRegistry) {
        guard let registrar = registry.registrar(forPlugin: "NativePoseCameraPlatformView") else {
            return
        }

        registrar.register(
            NativePoseCameraPlatformViewFactory(messenger: registrar.messenger()),
            withId: viewType
        )
    }
}
