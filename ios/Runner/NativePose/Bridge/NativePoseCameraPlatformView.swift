import Flutter
import SwiftUI
import UIKit

final class NativePoseCameraPlatformView: NSObject, FlutterPlatformView {
    private let hostingController: UIHostingController<AnyView>
    private let channel: FlutterMethodChannel

    init(
        frame: CGRect,
        viewId: Int64,
        messenger: FlutterBinaryMessenger,
        exercise: NativePoseExercise?,
        exerciseId: String?
    ) {
        let channel = FlutterMethodChannel(
            name: "bpt/native_pose_camera/\(viewId)",
            binaryMessenger: messenger
        )
        self.channel = channel

        let rootView: AnyView
        if let exercise {
            rootView = AnyView(
                CameraPosePreview(exercise: exercise) { rep, status, done in
                    channel.invokeMethod(
                        "onPoseUpdate",
                        arguments: ["rep": rep, "status": status, "done": done]
                    )
                }
            )
        } else {
            rootView = AnyView(UnsupportedNativePoseExerciseView(exerciseId: exerciseId))
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

private struct UnsupportedNativePoseExerciseView: View {
    let exerciseId: String?

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            VStack(spacing: 12) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .font(.largeTitle)
                    .foregroundStyle(.yellow)
                Text("Unsupported Exercise")
                    .font(.title3.bold())
                    .foregroundStyle(.white)
                Text("Native AI coaching does not support exercise id: \(exerciseId ?? "nil")")
                    .font(.subheadline)
                    .foregroundStyle(.white.opacity(0.72))
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 24)
            }
        }
    }
}
