# Minimal Apple Vision 3D iOS App Target

This directory documents the next Apple-only validation step for Apple Vision 3D. It is intentionally not a full app and does not change the repository pose pipeline.

## Goal

Validate whether `DetectHumanBodyPose3DRequest` works in an iOS 18+ physical-device Xcode app target after the macOS Swift CLI target failed at request construction.

## Requirements

- Xcode with an iOS 18+ SDK.
- Physical iPhone or iPad running iOS/iPadOS 18+.
- Prefer an A12-or-newer device, matching Apple’s 3D body-pose sample guidance.
- A bundled still image where the full body and limbs are visible.

## Minimal Test Order

1. Create a new iOS app target.
2. Add one still image to the app bundle.
3. Run request construction before camera/video code.
4. Print supported revisions and joint names.
5. Run still-image inference on `CGImage`.
6. Only after that succeeds, test `CVPixelBuffer` camera frames.

## Swift Code Outline

```swift
import SwiftUI
import Vision
import ImageIO

@MainActor
final class Vision3DDiagnosticViewModel: ObservableObject {
    @Published var log: [String] = []

    func runStillImageSmokeTest() {
        Task {
            do {
                let request = DetectHumanBodyPose3DRequest()
                log.append("supportedRevisions: \(DetectHumanBodyPose3DRequest.supportedRevisions)")
                log.append("selected revision: \(request.revision)")
                log.append("supported joints: \(request.supportedJointNames.map { $0.rawValue })")
                log.append("supported groups: \(request.supportedJointsGroupNames.map { $0.rawValue })")

                guard
                    let url = Bundle.main.url(forResource: "bodypose", withExtension: "jpg"),
                    let source = CGImageSourceCreateWithURL(url as CFURL, nil),
                    let cgImage = CGImageSourceCreateImageAtIndex(source, 0, nil)
                else {
                    log.append("Failed to load bundled image")
                    return
                }

                let observations = try await request.perform(on: cgImage, orientation: .up)
                log.append("observation count: \(observations.count)")

                guard let observation = observations.first else {
                    log.append("No body detected")
                    return
                }

                for jointName in observation.availableJointNames {
                    if let joint = observation.joint(for: jointName) {
                        let p = joint.position.columns.3
                        log.append("\(jointName.rawValue): x=\(p.x), y=\(p.y), z=\(p.z)")
                    }
                }
            } catch {
                log.append("Vision 3D failed: \(type(of: error)) \(error.localizedDescription)")
            }
        }
    }
}
```

## Interpretation

- If construction fails before image loading, the problem is platform/runtime/model initialization.
- If construction succeeds but `perform(on: CGImage)` fails, debug still-image orientation and input format.
- If still image succeeds but camera frames fail, debug `CVPixelBuffer`, orientation, and optional depth-data handling.
- If the physical-device app fails at construction like the macOS CLI, exclude Apple Vision 3D from this project.
