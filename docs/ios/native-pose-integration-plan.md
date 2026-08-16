# NATIVE_POSE_INTEGRATION_PLAN.md

This is a planning document only. It describes how to transplant the native iOS pose pipeline into the Flutter app later. No Flutter source, iOS source, Podfile, Xcode project file, model file, or resource file has been changed as part of this plan.

## 1. Current Flutter App Summary

- Flutter app root: `bpt/`
- Main entry point: `bpt/lib/main.dart`
  - Initializes Firebase through `DefaultFirebaseOptions.currentPlatform`.
  - Loads `SharedPreferences`.
  - Locks the app to portrait orientation.
  - Starts `MaterialApp.router` inside Riverpod `ProviderScope`.
- Router: `bpt/lib/core/router/app_router.dart`
  - Uses `go_router`.
  - Uses constants from `bpt/lib/core/constants/route_constants.dart`.
  - Note: `bpt/lib/core/router/route_constants.dart` was requested for inspection but does not exist; verify before modifying any path assumptions.
- Current route constants:
  - `/`
  - `/login`
  - `/home`
  - `/report`
  - `/profile`
  - `/exercise-selection`
  - `/workout`
  - `/workout-result`
- Current app shell:
  - `/home`, `/report`, and `/profile` are under `MainShell`.
  - `/exercise-selection`, `/workout`, and `/workout-result` are full-screen routes outside the tab shell.
- Current exercise ids in `bpt/lib/data/mock_data.dart`:
  - `squat`
  - `benchpress`
  - `deadlift`
  - `barbell-row`
  - `pushup`
- Current exercise selection locations:
  - `bpt/lib/features/home/screens/home_screen.dart`
    - Home exercise cards are generated from `mockExercises`.
    - `_StartButton` initializes `workoutProvider` and pushes `RouteConstants.workout`.
  - `bpt/lib/features/workout/screens/exercise_selection_screen.dart`
    - Exercise selection grid is generated from `mockExercises`.
    - `_BottomCTA` initializes `workoutProvider` and pushes `RouteConstants.workout`.
- Current workout flow:
  - `bpt/lib/features/workout/providers/workout_provider.dart` simulates workout state, countdowns, timers, reps, feedback, and scores.
  - `bpt/lib/features/workout/screens/workout_screen.dart` displays a simulated camera placeholder and simulated skeleton overlay.
  - `bpt/lib/features/workout/screens/workout_result_screen.dart` receives a result map from `/workout-result`.
- Recommended native camera insertion point:
  - Add a new route next to `/workout`, not as a replacement for `/workout`.
  - Suggested route: `/native-pose-workout`.
  - Suggested route constant: `nativePoseWorkout`.
  - Suggested Dart screen: `bpt/lib/features/workout/screens/native_pose_workout_screen.dart`.
  - Pass the selected Flutter exercise id through `state.extra`, matching the current `/workout` route style.

## 2. Native Prototype Summary

- Native prototype path inspected:
  - `/Users/6_month/Library/CloudStorage/GoogleDrive-firstn1028@gmail.com/내 드라이브/CoreMLPoseBenchmark`
- Export package found:
  - `/Users/6_month/Library/CloudStorage/GoogleDrive-firstn1028@gmail.com/내 드라이브/CoreMLPoseBenchmark/BPT_Camera_Integration_Export/`
- Export README found:
  - `BPT_Camera_Integration_Export/README_CAMERA_INTEGRATION.md`
- Export project notes found:
  - `ProjectNotes/dependency_notes.md`
  - `ProjectNotes/integration_checklist.md`
  - `ProjectNotes/required_build_settings.md`
  - `ProjectNotes/required_info_plist_keys.md`
- Native files found in the export package:
  - `Sources/AppNavigation/ExercisePreviewConfig.swift`
  - `Sources/AppNavigation/ExerciseSelectionView.swift`
  - `Sources/Camera/CameraPosePreview.swift`
  - `Sources/PosePipeline/PosePreprocess.swift`
  - `Sources/PosePipeline/SimCCDecoder.swift`
  - `Sources/PosePipeline/PoseCoordinateTransforms.swift`
  - `Sources/PosePipeline/Hands/BundledVideoHandFrameProcessor.swift`
  - `Sources/PosePipeline/Hands/HandCropBuilder.swift`
  - `Sources/PosePipeline/Hands/HandLandmarkTypes.swift`
  - `Sources/PosePipeline/Hands/MediaPipeHandLandmarkerRunner.swift`
  - `Sources/Overlays/HandOverlayRenderer.swift`
  - `Sources/Evaluators/DeadliftEvaluator.swift`
  - `Sources/Evaluators/DeadliftTypes.swift`
  - `Sources/Evaluators/BenchPressEvaluator.swift`
  - `Sources/Evaluators/BenchPressTypes.swift`
  - `Sources/Evaluators/SquatEvaluator.swift`
  - `Sources/Evaluators/SquatTypes.swift`
  - `Sources/Evaluators/BarbellRowEvaluator.swift`
  - `Sources/Evaluators/BarbellRowTypes.swift`
  - `Sources/Evaluators/PushUpEvaluator.swift`
  - `Sources/Evaluators/PushUpTypes.swift`
- Runtime model resources found in the export package:
  - `Resources/Models/rtmpose_s_forward.mlpackage`
  - `Resources/Models/hand_landmarker.task`
- Approximate runtime resource sizes:
  - `rtmpose_s_forward.mlpackage`: 11 MB
  - `hand_landmarker.task`: 7.5 MB
- Native pipeline support found:
  - AVFoundation live camera capture.
  - Front-camera preference with back-camera fallback.
  - RTMPose CoreML 2D body keypoint inference.
  - MediaPipe Hand Landmarker for cropped hand regions.
  - Body skeleton drawing inside `CameraPosePreview.swift`.
  - Hand skeleton drawing through `HandOverlayRenderer.swift`.
  - Per-exercise state-machine evaluators for Deadlift, Bench Press, Squat, Barbell Row, and Push Up.
  - Frame dropping when a frame is already being processed.
  - MainActor UI/evaluator updates after background frame processing.
- Front camera status:
  - `CameraPosePreview.swift` requests `.builtInWideAngleCamera` at `.front` first.
  - It sets `AVCaptureConnection.isVideoMirrored` for front camera output.
- Bundled-video files exist in the root prototype and must not be copied into the Flutter app:
  - `BarbellLow_04 2.mp4`
  - `BarbellLow_04.mp4`
  - `benchpress_02.mp4`
  - `deadlift_01.mp4`
  - `pushup_01.mp4`
  - `squat_03.mp4`
  - `vedio_1.mp4`
- Verify before modifying:
  - The export package README lists only the five target exercises, but `ExercisePreviewConfig.swift` still contains `.latPulldown` and bundled-video resource names. The integration should remove or ignore these prototype-only config entries.
  - The export package does not include separate `RTMPoseRunner.swift` or camera manager files; RTMPose model loading, camera capture, body overlay drawing, and evaluator dispatch are currently embedded in `CameraPosePreview.swift`.

## 3. Files to Copy

Target destination root for later implementation:

```text
bpt/ios/Runner/NativePose/
```

Suggested target structure:

```text
bpt/ios/Runner/NativePose/Camera/
bpt/ios/Runner/NativePose/PosePipeline/
bpt/ios/Runner/NativePose/Hands/
bpt/ios/Runner/NativePose/Overlays/
bpt/ios/Runner/NativePose/Evaluators/
bpt/ios/Runner/NativePose/Types/
bpt/ios/Runner/NativePose/Bridge/
bpt/ios/Runner/NativePose/Models/
```

### Required Files

Use the export package as the preferred source, not the full prototype root, because the export package already excludes most bundled-video and benchmark files.

| Source | Target |
| --- | --- |
| `BPT_Camera_Integration_Export/Sources/Camera/CameraPosePreview.swift` | `bpt/ios/Runner/NativePose/Camera/CameraPosePreview.swift` |
| `BPT_Camera_Integration_Export/Sources/PosePipeline/PosePreprocess.swift` | `bpt/ios/Runner/NativePose/PosePipeline/PosePreprocess.swift` |
| `BPT_Camera_Integration_Export/Sources/PosePipeline/SimCCDecoder.swift` | `bpt/ios/Runner/NativePose/PosePipeline/SimCCDecoder.swift` |
| `BPT_Camera_Integration_Export/Sources/PosePipeline/PoseCoordinateTransforms.swift` | `bpt/ios/Runner/NativePose/PosePipeline/PoseCoordinateTransforms.swift` |
| `BPT_Camera_Integration_Export/Sources/PosePipeline/Hands/BundledVideoHandFrameProcessor.swift` | `bpt/ios/Runner/NativePose/Hands/BundledVideoHandFrameProcessor.swift` |
| `BPT_Camera_Integration_Export/Sources/PosePipeline/Hands/HandCropBuilder.swift` | `bpt/ios/Runner/NativePose/Hands/HandCropBuilder.swift` |
| `BPT_Camera_Integration_Export/Sources/PosePipeline/Hands/HandLandmarkTypes.swift` | `bpt/ios/Runner/NativePose/Hands/HandLandmarkTypes.swift` |
| `BPT_Camera_Integration_Export/Sources/PosePipeline/Hands/MediaPipeHandLandmarkerRunner.swift` | `bpt/ios/Runner/NativePose/Hands/MediaPipeHandLandmarkerRunner.swift` |
| `BPT_Camera_Integration_Export/Sources/Overlays/HandOverlayRenderer.swift` | `bpt/ios/Runner/NativePose/Overlays/HandOverlayRenderer.swift` |
| `BPT_Camera_Integration_Export/Sources/Evaluators/DeadliftEvaluator.swift` | `bpt/ios/Runner/NativePose/Evaluators/DeadliftEvaluator.swift` |
| `BPT_Camera_Integration_Export/Sources/Evaluators/DeadliftTypes.swift` | `bpt/ios/Runner/NativePose/Evaluators/DeadliftTypes.swift` |
| `BPT_Camera_Integration_Export/Sources/Evaluators/BenchPressEvaluator.swift` | `bpt/ios/Runner/NativePose/Evaluators/BenchPressEvaluator.swift` |
| `BPT_Camera_Integration_Export/Sources/Evaluators/BenchPressTypes.swift` | `bpt/ios/Runner/NativePose/Evaluators/BenchPressTypes.swift` |
| `BPT_Camera_Integration_Export/Sources/Evaluators/SquatEvaluator.swift` | `bpt/ios/Runner/NativePose/Evaluators/SquatEvaluator.swift` |
| `BPT_Camera_Integration_Export/Sources/Evaluators/SquatTypes.swift` | `bpt/ios/Runner/NativePose/Evaluators/SquatTypes.swift` |
| `BPT_Camera_Integration_Export/Sources/Evaluators/BarbellRowEvaluator.swift` | `bpt/ios/Runner/NativePose/Evaluators/BarbellRowEvaluator.swift` |
| `BPT_Camera_Integration_Export/Sources/Evaluators/BarbellRowTypes.swift` | `bpt/ios/Runner/NativePose/Evaluators/BarbellRowTypes.swift` |
| `BPT_Camera_Integration_Export/Sources/Evaluators/PushUpEvaluator.swift` | `bpt/ios/Runner/NativePose/Evaluators/PushUpEvaluator.swift` |
| `BPT_Camera_Integration_Export/Sources/Evaluators/PushUpTypes.swift` | `bpt/ios/Runner/NativePose/Evaluators/PushUpTypes.swift` |
| `BPT_Camera_Integration_Export/Sources/AppNavigation/ExercisePreviewConfig.swift` | `bpt/ios/Runner/NativePose/Types/ActiveExercise.swift` or equivalent adapted mapping file |

Notes for required files:

- `BundledVideoHandFrameProcessor.swift` is required by the live camera file despite its bundled-video name. During implementation, verify whether it can be renamed to `LiveHandFrameProcessor.swift` without breaking references.
- `ExercisePreviewConfig.swift` should not be copied wholesale without review. The live camera needs `ActiveExercise`; Flutter does not need the native bundled-video names or native selection UI. Create or adapt a smaller type/mapping file if possible.
- `PoseCoordinateTransforms.swift` includes some MotionAGFormer-related helper functions. Keep the file if its shared `PoseKeypoint`, `PosePoint`, and transform types are needed, but do not copy MotionAGFormer models or 3D screens unless later proven required.

### Bridge Files to Create Later

These files do not exist in the prototype export and should be created during implementation:

| Target |
| --- |
| `bpt/ios/Runner/NativePose/Bridge/NativePoseCameraPlatformView.swift` |
| `bpt/ios/Runner/NativePose/Bridge/NativePoseCameraPlatformViewFactory.swift` |
| `bpt/ios/Runner/NativePose/Bridge/NativePosePlugin.swift` or `NativePoseRegistration.swift` |

### Optional Files

| Source | Use |
| --- | --- |
| `BPT_Camera_Integration_Export/Sources/AppNavigation/ExerciseSelectionView.swift` | Native-only reference for how the prototype starts `CameraPosePreview`; do not use as the production Flutter exercise selector. |
| `BPT_Camera_Integration_Export/ProjectNotes/*.md` | Reference documentation for dependencies, Info.plist keys, build settings, and checklist. |

### Files to Explicitly Exclude

Do not copy these into the Flutter app unless a later task explicitly asks for benchmark or bundled-video functionality:

- `BundledVideoPosePreview.swift`
- `BundledVideoPoseBenchmark.swift`
- `CoreMLPosePipelineBenchmark.swift`
- `CoreMLPoseBenchmark.swift`
- `CoreMLPoseBenchmarkApp.swift`
- `ContentView.swift`
- `ExerciseSelectionView.swift` as production UI
- `LatPulldownPostureEvaluator.swift`
- `MotionAGFormerInputBuilder.swift`
- `Pose3DViews.swift`
- `motionagformer_xs.mlpackage`
- Bundled videos:
  - `BarbellLow_04 2.mp4`
  - `BarbellLow_04.mp4`
  - `benchpress_02.mp4`
  - `deadlift_01.mp4`
  - `pushup_01.mp4`
  - `squat_03.mp4`
  - `vedio_1.mp4`
- Synthetic benchmark files.
- CocoaPods directories from the prototype, including `Pods/`.
- Any `.pt`, `.pth`, `.onnx`, `.mp4`, `.mov`, `.ckpt`, `.safetensors`, or training/export artifacts.

## 4. Native Resource Plan

Runtime resources to copy later:

| Source | Target |
| --- | --- |
| `BPT_Camera_Integration_Export/Resources/Models/rtmpose_s_forward.mlpackage` | `bpt/ios/Runner/NativePose/Models/rtmpose_s_forward.mlpackage` |
| `BPT_Camera_Integration_Export/Resources/Models/hand_landmarker.task` | `bpt/ios/Runner/NativePose/Models/hand_landmarker.task` |

Resource bundling requirements:

- Add both runtime resources to the Runner target.
- Verify both resources appear in Xcode under Runner target membership.
- Verify both resources appear in the Runner target **Copy Bundle Resources** build phase.
- Open and build with `bpt/ios/Runner.xcworkspace` after CocoaPods are used.

Bundle lookup plan:

- RTMPose:
  - Current prototype lookup checks:
    - `Bundle.main.url(forResource: "rtmpose_s_forward", withExtension: "mlmodelc")`
    - fallback to `Bundle.main.url(forResource: "rtmpose_s_forward", withExtension: "mlpackage")`
  - Keep this dual lookup, because Xcode may compile `.mlpackage` into `.mlmodelc`.
- MediaPipe Hand Landmarker:
  - Current prototype lookup checks:
    - `Bundle.main.path(forResource: "hand_landmarker", ofType: "task")`
  - Keep `hand_landmarker.task` in the main app bundle.

Resource extensions that should not be ignored when they are runtime resources:

- `.mlpackage`
- `.mlmodel`
- `.mlmodelc`
- `.task`

Artifacts that should remain ignored or at least not be committed without explicit approval:

- `.pt`
- `.pth`
- `.onnx`
- `.engine`
- `.tflite`
- `.ckpt`
- `.safetensors`
- `.mp4`
- `.mov`
- large datasets
- large training images or videos

Do not delete local model files without explicit instruction. If a model is needed at runtime, verify both file presence and Xcode target membership before assuming the app can load it.

## 5. Flutter PlatformView Bridge Design

Preferred PlatformView viewType:

```text
bpt/native_pose_camera
```

Suggested Dart screen:

```text
bpt/lib/features/workout/screens/native_pose_workout_screen.dart
```

Creation params:

```dart
{
  'exerciseId': exerciseId,
}
```

Supported Flutter exercise ids:

- `deadlift`
- `benchpress`
- `squat`
- `barbell-row`
- `pushup`

Dart behavior:

- Use `UiKitView` only on iOS.
- Pass `exerciseId` through `creationParams`.
- Use `StandardMessageCodec` for creation params.
- On non-iOS platforms, show a conservative fallback screen explaining that AI camera mode is iOS-only for now.
- Do not route non-iOS users into a broken native view.

Swift bridge files to create:

- `bpt/ios/Runner/NativePose/Bridge/NativePoseCameraPlatformView.swift`
- `bpt/ios/Runner/NativePose/Bridge/NativePoseCameraPlatformViewFactory.swift`
- `bpt/ios/Runner/NativePose/Bridge/NativePosePlugin.swift` or `NativePoseRegistration.swift`

Swift bridge design:

- `NativePoseCameraPlatformViewFactory` reads `creationParams`.
- It extracts `exerciseId`.
- It maps `exerciseId` to a native `ActiveExercise`.
- It creates a `NativePoseCameraPlatformView`.
- The platform view embeds `CameraPosePreview(exercise:)` using a `UIHostingController`.
- The platform view owns the hosted SwiftUI view lifecycle.
- On disposal, the hosted camera view must stop its capture session and release camera/inference resources.
- Keep UI updates on the main thread/MainActor.

Registration plan:

- Register the view factory in `bpt/ios/Runner/AppDelegate.swift`.
- Current `AppDelegate.swift` uses `FlutterImplicitEngineDelegate` and registers generated plugins in `didInitializeImplicitFlutterEngine(_:)`.
- Verify before modifying: the exact registrar call for `FlutterImplicitEngineBridge` should be checked against the local Flutter/iOS API. The standard pattern is usually `registrar(forPlugin:)`, but this app is using implicit engine registration through `engineBridge.pluginRegistry`.

## 6. Native Exercise Mapping Plan

Map Flutter ids to native evaluator/config:

| Flutter id | Native enum/config | Evaluator |
| --- | --- | --- |
| `deadlift` | `.deadlift` | `DeadliftEvaluator` |
| `benchpress` | `.benchPress` | `BenchPressEvaluator` |
| `squat` | `.squat` | `SquatEvaluator` |
| `barbell-row` | `.barbellRow` | `BarbellRowEvaluator` |
| `pushup` | `.pushUp` | `PushUpEvaluator` |

Native prototype enum names:

- `ActiveExercise.deadlift`
- `ActiveExercise.benchPress`
- `ActiveExercise.squat`
- `ActiveExercise.barbellRow`
- `ActiveExercise.pushUp`
- `ActiveExercise.none`
- `ActiveExercise.latPulldown`

Mapping adapter requirements:

- Add a small native adapter such as:
  - `ActiveExercise(flutterExerciseId:)`
  - or `NativePoseExerciseMapper.map(_:)`
- Reject unknown ids safely.
- Do not allow `latPulldown` from Flutter, because the current Flutter catalog does not support it.
- Do not route `none` from Flutter except perhaps for a native debug mode.
- If an unknown id arrives, show a clear native fallback/error view or default to no camera start. Do not silently run the wrong evaluator.

Verify before modifying:

- `CameraPosePreview.swift` currently dispatches evaluators with a `switch exercise` block. Check whether copying a reduced `ActiveExercise` enum requires updating that switch to remove `.latPulldown` and `.none`.

## 7. Flutter Routing/UI Plan

Flutter files to modify during implementation:

- `bpt/lib/core/constants/route_constants.dart`
  - Add `nativePoseWorkout = '/native-pose-workout'`.
- `bpt/lib/core/router/app_router.dart`
  - Import `NativePoseWorkoutScreen`.
  - Add a `GoRoute` for `RouteConstants.nativePoseWorkout`.
  - Pass `state.extra as String? ?? 'squat'` or reject missing ids explicitly.
- `bpt/lib/features/workout/screens/native_pose_workout_screen.dart`
  - New Dart screen hosting the iOS PlatformView.
- `bpt/lib/features/home/screens/home_screen.dart`
  - Add a separate native camera start path near the existing start flow.
- `bpt/lib/features/workout/screens/exercise_selection_screen.dart`
  - Add the same separate native camera start path or a second CTA.
- Any start bottom sheet or CTA widget that should expose camera mode.

Conservative UI behavior:

- Preserve the existing simulated workout flow.
- Keep the current `RouteConstants.workout` flow unchanged.
- Add a separate action for native camera mode, for example:
  - `실시간 카메라 시작`
  - `AI Camera Mode`
- Route the separate native-camera action to `/native-pose-workout` with the selected exercise id.
- Do not remove simulated workout unless a later task explicitly asks for replacement.
- Do not change workout provider semantics for this integration unless the native screen intentionally reports results back to Flutter in a later task.

Possible result handling for later design:

- Phase 1 can show native camera only and keep results inside the native HUD.
- Phase 2 can add an EventChannel or MethodChannel to send rep/status/done events back to Flutter.
- Phase 3 can decide whether native-computed results should reuse `WorkoutResultScreen`.

## 8. iOS Project / Podfile Plan

Current iOS state:

- `bpt/ios/Podfile`
  - Platform is `ios, '15.0'`.
  - Uses `use_frameworks!`.
  - Installs Flutter iOS pods.
  - Does not include `MediaPipeTasksVision`.
- `bpt/ios/Runner/Info.plist`
  - `NSCameraUsageDescription` was not found.
- `bpt/ios/Runner/AppDelegate.swift`
  - Registers generated Flutter plugins.
  - Does not register a native PlatformView.
- `bpt/ios/Runner.xcworkspace`
  - Present.
- `bpt/ios/Runner.xcodeproj`
  - Present.
- Visible project settings:
  - Bundle id: `com.bpt.bpt`.
  - Development team id exists locally.
  - Xcode project deployment target entries show iOS 13.0.
  - Podfile platform is iOS 15.0.

Required iOS changes during implementation:

- Add `NSCameraUsageDescription` to `bpt/ios/Runner/Info.plist`.
  - Suggested value from export notes: `We need camera access to capture pose estimation and evaluate your exercise form.`
- Add `pod 'MediaPipeTasksVision'` to the Runner target in `bpt/ios/Podfile`.
- Run `pod install` from `bpt/ios/`.
- Open `Runner.xcworkspace`, not `Runner.xcodeproj`.
- Add Swift files under `NativePose/` to the Runner target.
- Add `.mlpackage` / `.mlmodelc` and `.task` resources to Runner target membership and Copy Bundle Resources.
- Register the PlatformView factory in `AppDelegate.swift`.

Deployment target caveat:

- Prototype Podfile uses iOS 16.0.
- Export `required_build_settings.md` says iOS 17.0 or higher.
- Current Flutter app Podfile is iOS 15.0 and project settings show iOS 13.0.
- Verify before modifying: determine the minimum version required by the installed `MediaPipeTasksVision` pod, the local Xcode SDK, and the Swift features used by the copied files. The implementation may need to raise the Flutter iOS deployment target consistently across Podfile, Xcode project settings, and generated Flutter config.

Native dependencies relevant to this plan:

- Apple frameworks:
  - SwiftUI
  - UIKit
  - AVFoundation
  - CoreML
  - CoreImage
  - Combine
- Third-party:
  - `MediaPipeTasksVision` via CocoaPods

## 9. Build and Validation Plan

Commands to run during implementation from `bpt/`:

```sh
flutter analyze
flutter test
flutter build ios --debug --no-codesign
```

Commands to run during implementation from `bpt/ios/`:

```sh
pod install
xcodebuild -workspace Runner.xcworkspace -scheme Runner -configuration Debug -destination 'generic/platform=iOS' build
```

Manual validation:

- Open `bpt/ios/Runner.xcworkspace` in Xcode.
- Verify Signing & Capabilities has a valid Development Team.
- Build and run on a physical iPhone.
- Confirm the camera permission prompt appears.
- Confirm the front camera preview is visible.
- Confirm preview mirroring looks like a normal selfie camera.
- Confirm body skeleton overlay aligns with body joints.
- Confirm hand skeleton overlay aligns with hands.
- Confirm each supported exercise maps to the expected native evaluator.
- Confirm rep/status HUD updates in real time.
- Confirm memory does not grow continuously during camera use.

Important caveats:

- Simulator is insufficient for camera/CoreML/MediaPipe validation.
- `flutter build ios --debug --no-codesign` is useful for compile validation but does not prove live camera behavior.
- Xcode signing team selection may require manual setup.
- Google Drive / CloudStorage paths can cause CocoaPods or Xcode project loading issues; if Pods behave inconsistently, move or clone the repo to a local non-syncing path before deep CocoaPods debugging.

## 10. Risks and Mitigations

- PlatformView lifecycle issues:
  - Mitigation: ensure the platform view owns and releases its `UIHostingController`, stops the camera session on dispose, and does not keep stale view models alive.
- Swift concurrency / MainActor issues:
  - Mitigation: keep camera/inference work off the main thread, and keep SwiftUI state/evaluator UI updates on MainActor.
- Front camera mirroring / coordinate alignment:
  - Mitigation: preserve the prototype's mirrored front-camera connection behavior and verify overlays on a physical iPhone.
- MediaPipe timestamp monotonicity:
  - Mitigation: preserve `MediaPipeHandLandmarkerRunner` timestamp guard and use video-mode timestamps.
- Model resource target membership:
  - Mitigation: verify `.mlpackage` or compiled `.mlmodelc` and `hand_landmarker.task` are in Copy Bundle Resources.
- Deployment target mismatch:
  - Mitigation: reconcile current app iOS 13/15 settings with prototype iOS 16 Podfile and export iOS 17 note before changing project settings.
- Google Drive / CloudStorage path issues:
  - Mitigation: if CocoaPods or Xcode fails to resolve paths, test from a local non-syncing clone before making project-level changes.
- Accidentally copying bundled-video or benchmark files:
  - Mitigation: copy from `BPT_Camera_Integration_Export/` first, and explicitly exclude root prototype benchmark/video files.
- Accidentally adding large model/video artifacts:
  - Mitigation: commit only required runtime resources and avoid `.pt`, `.pth`, `.onnx`, `.mp4`, `.mov`, and training artifacts.
- Preserving memory-safe camera processing:
  - Mitigation: keep the `isProcessingFrame` frame-drop gate, avoid frame history buffers, and use autorelease pools around frame processing.
- Flutter simulated flow regression:
  - Mitigation: add native camera mode as a separate route/button and leave the existing `/workout` simulation intact.
- Native exercise id mismatch:
  - Mitigation: use a single mapping adapter from Flutter ids to native enum cases and reject unknown ids.
- Export enum still includes Lat Pulldown:
  - Mitigation: remove or ignore `.latPulldown` in the adapted integration. The Flutter app target catalog is exactly Squat, Bench Press, Deadlift, Barbell Row, and Push-up.

## 11. Step-by-Step Implementation Checklist

1. Copy required Swift files from `BPT_Camera_Integration_Export/Sources/` into `bpt/ios/Runner/NativePose/`.
2. Copy runtime model resources into `bpt/ios/Runner/NativePose/Models/`.
3. Add copied Swift files and runtime resources to the Runner Xcode target.
4. Add the PlatformView bridge files under `bpt/ios/Runner/NativePose/Bridge/`.
5. Register the PlatformView factory in `bpt/ios/Runner/AppDelegate.swift`.
6. Add `bpt/lib/features/workout/screens/native_pose_workout_screen.dart`.
7. Add the native camera route constant and GoRouter route.
8. Add a separate UI button for native camera mode while preserving the simulated workout start button.
9. Add `NSCameraUsageDescription` to `bpt/ios/Runner/Info.plist`.
10. Update `bpt/ios/Podfile` if needed, including `pod 'MediaPipeTasksVision'` and any required platform version change.
11. Run `pod install` from `bpt/ios/`.
12. Run `flutter analyze` and `flutter test` from `bpt/`.
13. Run `flutter build ios --debug --no-codesign` and an `xcodebuild` workspace build.
14. Test on a physical iPhone and verify camera preview, overlays, hand landmarks, evaluator mapping, rep/status HUD, and memory behavior.
