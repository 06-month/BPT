# Apple Vision 3D Body Pose — Documentation Review

Scope: Apple Vision / Vision framework only. This document does **not** cover
RTMPose, MediaPipe, MotionAGFormer, PoseMamba, Uplift, or SAM 3D, and does not
change WristEstimator, FeedbackEngine, or any app feedback logic. It is a
documentation + local-diagnostic review to decide whether our Apple Vision 3D
testing approach is correct and what the next Apple-only validation step is.

## How this review was produced

- Apple Developer Documentation symbol pages are JavaScript-rendered. A direct
  `WebFetch` of each page returned only the page `<title>` (no body), so exact
  prose could not be scraped programmatically. The accessible signal was:
  1. Apple symbol-page URLs (recorded below — open manually in a browser / Xcode
     Quick Help for the full availability badges).
  2. Web-search snippets that quote those Apple pages and the WWDC23 session.
  3. **Local runtime probes** on this machine, which are the strongest evidence
     and are quoted verbatim below.
- Local machine: macOS **26.5 (Build 25F71)**, arm64 (Apple Silicon),
  `swiftc` Apple Swift 6.3.1, target `arm64-apple-macosx26.0`.

### Apple source pages reviewed (open manually for full prose)

- Vision framework: https://developer.apple.com/documentation/vision
- Legacy request: https://developer.apple.com/documentation/vision/vndetecthumanbodypose3drequest
- Legacy observation: https://developer.apple.com/documentation/vision/vnhumanbodypose3dobservation
- Legacy joint names: https://developer.apple.com/documentation/vision/vnhumanbodypose3dobservation/jointname
- Legacy camera-relative position: https://developer.apple.com/documentation/vision/vnhumanbodypose3dobservation/4210411-getcamerarelativeposition
- New Swift request: https://developer.apple.com/documentation/vision/detecthumanbodypose3drequest
- New Swift observation: https://developer.apple.com/documentation/vision/humanbodypose3dobservation
- 2D body pose (legacy): https://developer.apple.com/documentation/vision/vndetecthumanbodyposerequest
- Hand pose (legacy): https://developer.apple.com/documentation/vision/vndetecthumanhandposerequest
- Sample (video): https://developer.apple.com/documentation/vision/detecting-human-body-poses-in-3d-with-vision
- Sample (still image): https://developer.apple.com/documentation/vision/identifying-3d-human-body-poses-in-images
- WWDC23 session 111241 "Explore 3D body pose and person segmentation in Vision":
  https://developer.apple.com/videos/play/wwdc2023/111241/

---

## 0. Headline result (read this first)

Our **prior** repository note said both API paths fail during 3D model
initialization (EspressoPlanFailure / ANE load in AltruisticBodyPoseKit), and
that even `supportedRevisions` / request construction trigger the failure.

**On macOS 26.5 this is fully resolved. Apple Vision 3D now works end-to-end on
the macOS CLI for BOTH API paths**, including real `perform()` inference:

- Request **construction** + `supportedRevisions` + joint/group enumeration:
  succeed (legacy `VN…` and new Swift `Detect…`).
- Real **`perform()` inference** on a real frame: **succeeds** and returns a
  valid 1-person, 17-joint 3D skeleton:
  - New API, **still image** (`assets/smoke/pushup.jpg`): `observation_count: 1`,
    17 joints.
  - New API, **video first frame** (`assets/smoke/vedio_1.mp4`):
    `observation_count: 1`, 17 joints.
  - Legacy API, **video first frame**: `processed_frames: 1`,
    `detected_frames: 1`, `body_detected: true`, full joint coordinates written
    to JSONL, `body_height_m ≈ 1.8` (reference height — no depth on this input).

So the earlier "macOS CLI fails" premise no longer holds. Precise current
status:

> On macOS 26.5 (arm64) CLI, Apple Vision 3D **builds, constructs, reads
> `supportedRevisions`, and runs real `perform()` inference successfully** for
> both the legacy `VNDetectHumanBodyPose3DRequest` and the new
> `DetectHumanBodyPose3DRequest`, returning a valid 17-joint 3D skeleton on both
> a still image and a video first frame. The earlier EspressoPlanFailure was an
> **OS/runtime-version artifact that is no longer reproducible.** The remaining
> work is **not** "does it run" but on-target validation: an **iOS
> physical-device app target** to confirm camera + (optional LiDAR) depth +
> latency on the real deployment hardware, plus an accuracy assessment for our
> side-/front-view exercise framing.

We do **not** claim it works on iPhone yet (only macOS was tested), and we do
**not** conclude it is globally impossible — the opposite: on macOS it now
works.

---

## 1. API families

| | Legacy `VNDetectHumanBodyPose3DRequest` / `VNHumanBodyPose3DObservation` | New `DetectHumanBodyPose3DRequest` / `HumanBodyPose3DObservation` |
|---|---|---|
| Style | Classic `VNRequest` + `VNImageRequestHandler.perform([request])`, results read from `request.results` | New Swift-structured Vision API: value-type request, `async` `try await request.perform(on:…)` returns `[Observation]` |
| Era | WWDC23 | WWDC24 (Vision Swift API redesign) |
| Threading | Synchronous `perform` | Swift concurrency (`async`/`await`) |
| In this repo | `tools/apple_vision_3d/AppleVision3DPoseExport.swift` (`@available(macOS 14.0, *)`) | `tools/apple_vision_3d/AppleVision3DNewAPIDiagnose.swift` (`@available(macOS 15.0, *)`) |

- **Legacy / `VNRequest`-style:** `VNDetectHumanBodyPose3DRequest`.
- **Newer Swift Vision API style:** `DetectHumanBodyPose3DRequest`.
- Both wrap the same underlying 3D body-pose model and produce the same
  17-joint skeleton (verified below). The new API is forward-looking; the legacy
  API remains for back-deployment to iOS 17 / macOS 14.

### OS requirements

| API | iOS | iPadOS | macOS | Mac Catalyst | visionOS |
|---|---|---|---|---|---|
| Legacy `VN…3DRequest` | 17.0+ | 17.0+ | 14.0+ | 17.0+ | 1.0+ |
| New `Detect…3DRequest` | 18.0+ | 18.0+ | 15.0+ | 18.0+ | 2.0+ |

macOS minimums are corroborated locally by the `@available` annotations the code
compiles against (legacy gated on `macOS 14.0`, new API on `macOS 15.0`). The
iOS/iPadOS/Catalyst/visionOS numbers follow Apple's WWDC23 (Vision 3D body pose)
and WWDC24 (Swift Vision API) release lines; confirm the exact availability
badges on the symbol pages above (those pages are JS-rendered and could not be
scraped).

---

## 2. Platform availability

- Minimum **iOS**: 17.0 (legacy), 18.0 (new Swift API).
- Minimum **iPadOS**: 17.0 (legacy), 18.0 (new Swift API).
- Minimum **macOS**: 14.0 (legacy), 15.0 (new Swift API).
- Minimum **Mac Catalyst**: 17.0 (legacy), 18.0 (new Swift API).
- Minimum **visionOS**: 1.0 (legacy), 2.0 (new Swift API).
- **Device / chip requirement (from Apple's sample docs + WWDC23):**
  - The "Detecting human body poses in 3D with Vision" sample states it needs an
    **iOS device with an A12 chip or later**.
  - For **metric (meters), depth-anchored** output a **LiDAR** device is
    recommended (iPhone 12 Pro / Pro Max and later Pro models, recent iPad Pro).
    Without depth, the model still returns a full 3D skeleton but anchored to a
    **reference ~1.8 m** body height (confirmed locally: our CLI run had no depth
    and reported `body_height_m ≈ 1.8`, `height_estimation` = reference).
- **Simulator vs physical device:** Vision pose models run on ANE/GPU. The iOS
  **Simulator has no camera/LiDAR and is not a representative target**. Use a
  **physical device** for meaningful on-target validation. The macOS CLI is a
  valid dev host (and now demonstrably runs the model), not the deployment
  target.

---

## 3. Request inputs

For the legacy API, inputs go through `VNImageRequestHandler`; for the new API
through `request.perform(on:…)`.

| Input type | Supported | Notes |
|---|---|---|
| `URL` | Yes | File URL to image. Used by the new-API still-image probe here. |
| `Data` | Yes | Encoded image bytes. |
| `CGImage` | Yes | Still images. |
| `CVPixelBuffer` | Yes | Camera / decoded video frames. Used by the legacy exporter here. |
| `CMSampleBuffer` | Yes | Camera capture / `AVAssetReader` output. Used by the new-API video probe here. Required to attach `AVDepthData`. |
| `CIImage` | Yes | Core Image pipelines. |

Recommended input per scenario:

- **Still-image smoke test:** `CGImage` / file `URL` — simplest, isolates model
  load from video decoding. (Proven working on CLI.)
- **Video-frame smoke test:** `CVPixelBuffer` / `CMSampleBuffer` from
  `AVAssetReader` (what both repo tools do). (Proven working on CLI.)
- **Real-time camera app:** `CMSampleBuffer` from `AVCaptureVideoDataOutput`
  (plus `AVCaptureDepthDataOutput` when available) so depth can be attached.

**AVDepthData:** `VNImageRequestHandler` has initializers for `cvPixelBuffer`
and `cmSampleBuffer` taking an `AVDepthData` parameter. The 3D request **uses
depth when present** to produce metric, better-anchored positions and a measured
`bodyHeight`. If the file already carries depth metadata, Vision reads it
automatically. Depth is **optional** — RGB-only still yields a 3D skeleton,
reference-anchored rather than measured.

---

## 4. Outputs

- **Observation type:** `VNHumanBodyPose3DObservation` (legacy) /
  `HumanBodyPose3DObservation` (new).
- **Joints — verified locally (new API `supportedJointNames`, 17 joints):**
  `topHead, centerHead, centerShoulder, leftShoulder, rightShoulder, spine,
  leftElbow, rightElbow, leftWrist, rightWrist, root, leftHip, rightHip,
  leftKnee, rightKnee, leftAnkle, rightAnkle`.
  (Legacy raw keys are the same joints, e.g. `human_center_head_3D`,
  `human_left_ankle_3D`.)
- **Joint groups — verified locally (6 groups):**
  `head, leftArm, rightArm, torso, leftLeg, rightLeg`.
- **Coordinate space:**
  - Positions are **3D in meters**, **origin at the `root` joint** (center of
    the hip) — i.e. **root-relative model space**.
  - A **camera-relative** position is also available
    (`getCameraRelativePosition(forJointName:)` on legacy; per-joint
    `position`/local transforms on the new API). The legacy exporter records the
    joint `position` (4×4 transform, translation in `.columns.3`), a
    `localPosition`, and a 2D image projection via `pointInImage`.
- **Estimated, not mocap-grade:** `bodyHeight` is an *estimate* — measured only
  when depth metadata is present, otherwise a **reference 1.8 m** (our CLI run
  reported exactly this). The output is a learned monocular(+optional depth) 3D
  estimate, **not** calibrated motion capture. App wording must not claim exact
  anatomical angles (consistent with project policy that the body 3D lifter must
  not be used for wrist pronation/supination).
- **Accessing joints:**
  - Legacy: `recognizedPoint(_:)` (one joint), `recognizedPoints(_:)` (a group),
    `getCameraRelativePosition(forJointName:)` (camera space).
  - New: `availableJointNames`, `joint(for:)` per joint; group access by joint
    group name.

---

## 5. Current failure interpretation

Mapping the docs + the prior note + this session's verified evidence:

- **Bad input video?** No. The same `AVAssetReader → CVPixelBuffer` path that 2D
  pose uses now also produces a valid 3D detection (`detected_frames: 1`).
- **AVFoundation video decoding?** No. Decoding works; both still-image and
  video paths succeed.
- **Request init / internal Apple model loading?** This was the prior diagnosis,
  but it **no longer reproduces** on macOS 26.5 — construction *and*
  `perform()`-time ANE model load both succeed.
- **Does `supportedRevisions` failing imply runtime fails before input?** That
  was the earlier signal; it is now moot because `supportedRevisions`,
  construction, and inference all succeed.
- **macOS-CLI-specific limitation or globally unusable?** Neither. On this
  machine the macOS CLI runs Apple Vision 3D end-to-end. The earlier failure is
  best explained as an **OS/runtime-version artifact** that a macOS update
  resolved.

### Verified local probes (quoted)

`--diagnose-only` (construction + metadata):

```
legacy : {"diagnose_only":true,"vision_3d_pose_works":true,"vision_2d_pose_works":true}
new    : {"diagnose_only":true,"request_construction_succeeded":true}
new    : supported_joint_names=[topHead..rightAnkle] (17); groups=[head,leftArm,rightArm,torso,leftLeg,rightLeg]; minimum_latency_frame_count=1; supported_revisions=[revision1]
```

Real `perform()` inference:

```
new  (still image pushup.jpg): {"inference_ran":true,"observation_count":1, first_joint rightKnee (x=-0.2736,y=-0.4554,z=0.0153), 17 joint_names}
new  (video vedio_1.mp4 f0)  : {"inference_ran":true,"observation_count":1, first_joint rightAnkle (x=-0.3935,y=-0.5887,z=0.0913), 17 joint_names}
legacy (video vedio_1.mp4 f0): {"processed_frames":1,"detected_frames":1}
  jsonl: body_detected=true, body_height_m=1.7999..., height_estimation=reference(rawValue 0),
         joints carry x/y/z (meters, root-relative), local_x/y/z, and image_x/image_y projection.
```

---

## 6. Correct next validation path (Apple-only)

1. **macOS CLI — proven end-to-end:** builds; 2D + 3D construction;
   `supportedRevisions`; joint/group enumeration; **and real `perform()` on both
   a still image and a video first frame**, returning a valid 17-joint skeleton.
   Nothing further to prove here for basic feasibility.
2. **macOS CLI — extend:** run a longer multi-frame sequence (the existing
   `run_apple_vision_3d_*` scripts) and the JSONL diagnose/visualize scripts to
   measure per-joint stability/jitter and detection rate on our exercise clips.
3. **macOS app target — optional:** only needed if you want an interactive Mac
   demo; not required for feasibility since the CLI already runs the model.
4. **iOS physical-device app target — the on-target validation:** the real
   deployment target. Validate camera `CMSampleBuffer` input, optional LiDAR
   depth (metric output + measured `bodyHeight`), and **latency** on device.
   This is now about *deployment fitness*, not about whether the API works.
5. **Simulator — avoid relying on it:** no camera/LiDAR; ML behavior
   unrepresentative.

Confidence order for any new environment: still-image `perform()` → video
first-frame → live camera.

---

## 7. Minimal iOS physical-device test plan

Goal: smallest app that confirms Apple Vision 3D `perform()` on a real iPhone
(camera + optional depth + latency). No real UI needed.

1. Xcode → new **iOS App** target (SwiftUI lifecycle is fine).
2. **Deployment target iOS 18.0+** (new `DetectHumanBodyPose3DRequest`). For the
   legacy path, a second build at iOS 17.0+.
3. Run on a **physical iPhone with A12 or later** (LiDAR Pro for metric depth).
   **Not** the Simulator.
4. Bundle **one full-body test image** (Add to target, Copy items if needed) or
   capture one `CVPixelBuffer` frame from `AVCaptureSession`.
5. In an `async` task:
   - `var request = DetectHumanBodyPose3DRequest()`.
   - Print `DetectHumanBodyPose3DRequest.supportedRevisions`,
     `request.supportedJointNames`, `request.supportedJointsGroupNames`.
   - `let observations = try await request.perform(on: cgImage, orientation: .up)`
     (or `.perform(on: pixelBuffer, orientation:)`).
   - Print `observations.count`; for the first observation print
     `availableJointNames` and each `joint(for:)?.position` (translation
     `.columns.3`), and `bodyHeight` + whether it is measured vs reference.
   - `do/catch` → print `error.localizedDescription` **and**
     `String(describing: error)`.
6. Copy console output back into the repo (see the tools README) so on-device
   results sit next to the macOS CLI results.

Minimal Swift outline:

```swift
import Vision
import UIKit

@MainActor
func runBodyPose3D(on image: CGImage) async {
    var request = DetectHumanBodyPose3DRequest()
    print("revisions:", DetectHumanBodyPose3DRequest.supportedRevisions)
    print("joints:", request.supportedJointNames.map(\.rawValue))
    print("groups:", request.supportedJointsGroupNames.map(\.rawValue))
    do {
        let observations = try await request.perform(on: image, orientation: .up)
        print("observation_count:", observations.count)
        if let first = observations.first {
            for name in first.availableJointNames {
                if let j = first.joint(for: name) {
                    let p = j.position.columns.3
                    print(name.rawValue, p.x, p.y, p.z)
                }
            }
        }
    } catch {
        print("perform_failed localized:", error.localizedDescription)
        print("perform_failed detail:", String(describing: error))
    }
}
```

---

## 8. Decision table

| Case | Observation | Interpretation | Next action |
|---|---|---|---|
| **A** | macOS CLI `perform` fails, iOS device succeeds | CLI-only limitation | Build on iOS path; CLI dev-only. |
| **B** | macOS CLI fails, macOS app succeeds | "Bare CLI" was the problem | macOS app host for Mac experiments; still validate iOS. |
| **C** | Both macOS CLI and iOS device fail | Genuine model/runtime problem | Capture full `String(describing: error)`, file Feedback, reject for now. |
| **D** | Still image succeeds, video frame fails | Pixel-format/orientation/timing issue, not the model | Fix `CVPixelBuffer` format/orientation/depth. |
| **E** | Construction fails before any input | Model metadata/ANE init failure (the *old* symptom) | OS/SDK-level; **no longer reproduces on macOS 26.5**. |
| **F (current)** | **macOS CLI succeeds end-to-end** (construct + `perform` on image *and* video) | API + model are functional on this OS; earlier blocker resolved | Move to **on-target iOS validation** (camera, depth, latency) and **accuracy** assessment on exercise framing. |

Current evidence on this machine = **Case F**.

---

## 9. Current recommendation (Apple Vision only)

- **Continue the Apple Vision 3D investigation — the blocker is gone.** On macOS
  26.5 the full pipeline (build → construct → `supportedRevisions` → `perform`)
  works for both the legacy and new APIs, returning a valid 17-joint 3D skeleton
  on a still image and a video frame.
- **Single most informative next experiment:** an **iOS physical-device
  `perform()`** (iOS 18+, A12+; LiDAR if measuring metric height) using the
  minimal app in §7 — to confirm on-device latency and (with LiDAR) measured
  depth on the real deployment target. On the Mac side, the most useful next
  step is a **multi-frame accuracy/jitter pass** over our exercise clips using
  the existing JSONL diagnose/visualize scripts.
- **Evidence sufficient to keep:** already largely met on macOS (valid 17-joint
  output end-to-end). To keep it for the *product*, the iOS device run must show
  acceptable latency and plausible joints on representative side/front exercise
  frames.
- **Evidence sufficient to reject:** on-device `perform()` fails (Case C), or
  3D joint accuracy/stability on our exercise framing is too poor to be useful.
  A macOS result alone is no longer a reason to reject — it now argues *for*
  continuing.

### Precise conclusion

> On the macOS CLI (macOS 26.5, arm64), Apple Vision 3D **works end-to-end** for
> both the legacy `VNDetectHumanBodyPose3DRequest` and the new
> `DetectHumanBodyPose3DRequest`: build, construction, `supportedRevisions`, and
> real `perform()` inference all succeed, yielding a valid 1-person, 17-joint 3D
> skeleton on both a still image and a video first frame. This **revises** the
> earlier "macOS CLI fails / EspressoPlanFailure" note — that failure no longer
> reproduces and was an OS/runtime-version artifact. We do **not** claim it works
> on iPhone yet (only macOS was tested); the **iOS physical-device app target is
> the next validation**, now framed as on-target latency/depth/accuracy
> validation rather than a feasibility blocker.

---

## Appendix: local environment & test results (this session)

- macOS 26.5 (Build 25F71), arm64; Swift 6.3.1 (`arm64-apple-macosx26.0`).
- `scripts/build_apple_vision_3d.sh` → built `apple_vision_3d_export` (exit 0).
- `scripts/build_apple_vision_3d_new_api.sh` → built
  `apple_vision_3d_new_api_diagnose` (exit 0).
- `apple_vision_3d_export --diagnose-only` → `vision_2d_pose_works: true`,
  `vision_3d_pose_works: true`.
- `apple_vision_3d_new_api_diagnose --diagnose-only` →
  `request_construction_succeeded: true`; 17 joints; 6 groups;
  `minimum_latency_frame_count: 1`; `supported_revisions: [revision1]`.
- New-API `perform()` on `assets/smoke/pushup.jpg` → `observation_count: 1`,
  17 joints.
- New-API `perform()` on `assets/smoke/vedio_1.mp4` frame 0 →
  `observation_count: 1`, 17 joints.
- Legacy `perform()` on `assets/smoke/vedio_1.mp4` frame 0 →
  `detected_frames: 1`, `body_detected: true`, `body_height_m ≈ 1.8`
  (reference, no depth), joints with meters + local + image projection.
- `python -m unittest discover -s tests` → **88 tests OK**.
- `compileall pose_feedback tests scripts` → exit 0.
