# M0 Pose Benchmark Handoff

Updated: 2026-09-02 (Asia/Seoul), phase 3 in progress

## Resume prompt

> BPT의 `bpt/benchmarks/pose/HANDOFF.md`를 읽고, 적힌 다음 미완료 단계부터 M0 benchmark 작업을 이어서 완료해줘. 기존 결과와 manifest는 보존하고 Fit3D TRAIN 학습/평가는 하지 마.

## Non-negotiable M0 contract

`RGB -> RTMPose-s -> COCO17 -> H36M17 -> screen normalization -> 27-frame lookahead5 -> MotionAGFormer-XS -> H36M17 3D`

- RTMPose uses the full-image affine path from
  `scripts/run_coreml_rtmpose_s_motionagformer_xs_pipeline.py`, not the iOS
  fast direct resize path.
- Motion input is `[1, 27, 17, 3]`; target index is 21. For target frame `i`,
  the window is `[i-21, ..., i+5]`. Clip boundaries repeat first/last frames.
- Compare output index 21 to GT frame `i`, never to the latest input frame
  `i+5`.
- No training or fine-tuning is authorized. Fit3D TRAIN must not be used as an
  evaluation substitute.

## Confirmed repository behavior

- RTMPose SimCC outputs are `[1,17,384]` and `[1,17,512]`; argmax only,
  split ratio 2.0, confidence is `min(max_x, max_y)`, inverse affine restores
  image pixels.
- COCO17 to H36M17 and confidence aggregation must reuse
  `pose_feedback/body/motionagformer_adapter.py`.
- Screen normalization is `x/W*2-1`, `y/W*2-H/W`; both axes divide by W.
- Existing MotionAGFormer tests passed: 22 tests on 2026-09-02 with
  `PYTHONPATH=.`.
- The workspace currently contains the bundled RTMPose Core ML package at
  `bpt/ios/Runner/NativePose/Models/rtmpose_s_forward.mlpackage` but did not
  initially contain a MotionAGFormer package/checkpoint.

## Dataset audit

### Fit3D official TEST

- User archive: repository-root `fit3d_test.tar.gz` (do not modify/delete).
- Extracted working copy during the original session: `/tmp/bpt_fit3d_test`.
- 3 subjects (`s02`, `s12`, `s13`), 47 sequences each, 141 videos total,
  177,703 frames, 900x900, 50fps, 3,554.06 seconds.
- Archive contents are only `videos/*.mp4` and
  `camera_parameters/*.json`. There is no 2D/3D GT or test template.
- The official `imar_vision_datasets_tools` README explicitly says test GT is
  not distributed. Local Fit3D TEST NME/MPJPE cannot be calculated from this
  archive. Do not invent metrics and do not silently use TRAIN. A valid
  official evaluation-server submission additionally needs the Fit3D test
  template/frame IDs.
- Official train-style convention (for code support if private GT is later
  supplied): `joints3d_25`, first 17 are H36M; world-to-camera is
  `(X - T) @ R.T`; distortion projection is implemented in the official
  utility.

### AthletePose3D

- Official code revision audited: `2db1f8d1b5878c081a07322e290e83cacd1003b9`.
- Latest corrected archive downloaded to `/tmp/pose_3d.zip` (Google Drive file
  `1PQerwftEKoOwqG-dhvadz_gaGxZx0D2y`), plus `/tmp/cam_param.json`.
- `pose_3d_v3` contains 3,068 test clips and 19,087 train clips of 81 frames,
  plus aggregate `valid.pkl` and `train.pkl`. Use test/validation only.
- Athlete H36M17 is explicitly defined by official `utils/rig.json`. Camera
  positions and 3D coordinates are mm. Official world-to-camera applies a
  y/z row-sign correction to R and then `R @ (X - camera_position)`.
- RGB archives are `pose_2d.zip` 29.1GB and `data.zip` 34.95GB. Initial free
  disk was about 23GB, so neither whole archive can safely be downloaded.
  Try HTTP range extraction of a deterministic evaluation subset; otherwise
  record RGB as an external blocker while still running GT-2D oracle checks.

## Protocol decisions

- Primary 2D joints: shoulders, elbows, wrists, hips, knees, ankles (12 direct
  COCO correspondences). GT bbox diagonal is the single NME/PCK scale.
- Report mean/median pixel error, NME, PCK@.05/.10/.20, normalized AUC over
  0..0.20, and per-joint values. Never threshold predictions out.
- Report pelvis-rooted MPJPE, N-MPJPE, PA-MPJPE, per-joint errors and
  percentiles. Treat raw MPJPE as physical only after unit/scale validation.
- Report elbow/knee 3D angles, bone absolute/relative error and temporal bone
  variance, MPJVE and acceleration error. Separate all frames from full-real-
  context frames (`i >= 21 and i <= N-6`).

## Timing estimate

- Fit3D M0 Stage A: approximately 50-80 minutes for all 177,703 frames based
  on the existing 78.5fps macOS prototype measurement, including decode/cache
  overhead.
- Framework/tests: 2-4 hours; model setup/smoke/overlay: 1-2 hours; feasible
  dataset inference: 1-2 hours. Total initial estimate: 4-8 hours, excluding
  external Fit3D server turnaround and RGB storage acquisition.

## Environment restored on 2026-09-02

- `external/MotionAGFormer` cloned and checked out at the pinned revision
  `4756fd1eb7cc73f0e991f091ff2280e030ab85f3`.
- Official XS H36M checkpoint restored to
  `external/MotionAGFormer/checkpoint/motionagformer-xs-h36m.pth.tr`
  (27.8MB, Google Drive `1Pab7cPvnWG8NOVd0nnL1iqAfYCUY4hDH`).
  `scripts/check_motionagformer_xs_assets.py` reports
  `ready_for_xs_inference: true`.
- The active interpreter is Python 3.13 (miniconda) with torch 2.9 and numpy
  2.3.4. `timm==0.6.11` from `requirements.txt` cannot import on Python 3.13
  (mutable dataclass default in `maxxvit`); timm 1.0.29 works and still
  exposes `timm.models.layers.DropPath`, which is all MotionAGFormer needs.
- `coremltools` 9.0 was installed during phase 3, which restores the Core ML
  path for both models. `mmpose` is still absent, so the PyTorch RTMPose
  backend remains unavailable; RTMPose runs only through Core ML.

## Phase 2 result: framework complete

Implemented and tested (`tests/test_pose_benchmark.py`, 39 tests, all passing
alongside the existing suite: 171 passed):

- `bpt/benchmarks/pose/cache.py`: resumable npz+json cache, invalidated by
  cache version or by any change in the metadata an entry was produced with.
- `bpt/benchmarks/pose/datasets/fit3d.py`: TEST discovery (141 sequences over
  s02/s12/s13), camera-parameter loading shaped for `geometry.projection`,
  video info and a frame iterator. It returns `None` for ground truth rather
  than inventing any, and accepts a separate train-style `joints3d_25`
  directory if private GT ever arrives.
- `bpt/benchmarks/pose/datasets/athletepose3d.py`: `valid.pkl` record loading
  straight out of `/tmp/pose_3d.zip`, grouped into 826 per-camera sequences
  over 293,753 frames, stacked into GT 2D, metric camera 3D, boxes, fps and
  frame ids.
- `bpt/benchmarks/pose/normalization.py`: both input conventions plus their
  shared inverse, and the official left/right flip.
- `scripts/run_m0_athletepose3d_oracle.py`: the GT-2D oracle runner.

## Unit and scale validation (required before any physical MPJPE)

- MotionAGFormer emits its prediction in the same normalized space it
  consumes. The official H36M reader denormalizes with
  `xy = (xy + [1, H/W]) * W/2` and `z = z * W/2`, then `train.py` multiplies
  by the per-clip 2.5D factor before computing MPJPE.
- AthletePose3D stores the reciprocal of that factor as `ratio`. Verified
  numerically: root-relative `joint_3d_image / ratio` reproduces
  root-relative `joint_3d_camera` to 16-41mm per sequence (25mm mean). That
  residual is the 2.5D representation's own error and is reported with every
  result as `representation_floor_mpjpe`.
- The prediction path itself is correct: with GT 2D input, root-relative
  target-frame xy lands within 5.8px mean (p90 10.8px) of GT 2D while the
  subject's torso spans about 54px. The remaining error is depth.

## Finding: the input normalization convention dominates the 3D error

Full AthletePose3D validation split, all 826 sequences, GT 2D input, official
flip test-time augmentation, frame stride 10, full real context, millimetres
(456,637 joint observations per mode, identical frames in both):

| normalization | MPJPE | N-MPJPE | PA-MPJPE | angle MAE |
| --- | ---: | ---: | ---: | ---: |
| `full_image` (what BPT ships) | 327.2 | 254.6 | 158.4 | 26.4 deg |
| `person_crop` (official demo path) | 190.1 | 181.6 | 123.4 | 19.0 deg |

All-frames context gives 330.9 / 186.4 MPJPE for the same two modes. The 2.5D
representation floor is 33.7mm, so neither mode is anywhere near
representation-limited: the gap is the model's.

`full_image` is the H36M training convention and only holds while the subject
fills a H36M-like share of the frame. In these AthletePose3D shots the subject
is small (torso about 54px inside 1920px), so full-image normalization feeds
the lifter a subject roughly an order of magnitude smaller than anything it
saw in training. BPT's iOS pipeline uses the same `full_image` convention, so
this is a real product finding, not just a benchmark artifact: whenever the
user does not fill the frame, the 3D stage degrades hard. Evaluate the
bbox-crop preprocessing before wiring MotionAGFormer into the app.

## Throughput

- The M0 contract scores one 27-frame window per target frame, so cost scales
  with frames, not clips: 1.0 GMAC per window for XS.
- Measured on this machine (MPS, PyTorch): 11 windows/s at batch 64,
  15 at batch 256, 19 at batch 512. Flip test-time augmentation doubles the
  forward count.
- The runner therefore takes `--frame-stride`: every scored frame still gets
  its own full 27-frame window and target index 21, only the set of scored
  target frames is subsampled. Stride 10 over the whole validation split is
  about 29,375 scored frames per normalization mode.

## Fit3D status

The TEST archive has no ground truth, so running RTMPose over its 177,703
frames produces nothing scoreable. That inference is deliberately not run
yet; the loader is ready for the moment private GT or the official test
template becomes available. Do not substitute TRAIN.

## Current phase / next action

- Phase 1 repository and dataset-convention audit: complete.
- Phase 2 framework implementation, tests, cache and loaders: complete.
- Phase 3 backend restore and lifter-only evaluation: complete. Both
  normalization modes ran over all 826 validation sequences at stride 10;
  per-sequence caches and summaries are in
  `assets/benchmarks/m0/athletepose3d_oracle/<mode>/`.
- Core ML MotionAGFormer-XS was re-exported during this phase
  (`coreml_safe`, FP16) to `assets/coreml/motionagformer_xs.mlpackage`, so the
  PyTorch/Core ML parity check is now unblocked.
- Next after that:
  1. RGB Stage A. AthletePose3D images are a 29.1GB archive against about
     22GB free, so this stays blocked unless a deterministic subset is
     range-extracted; Fit3D can supply RGB but no GT.
  2. Re-run the oracle through the Core ML package (now exported) to confirm
     PyTorch/Core ML parity, since the app ships Core ML.
  3. Decide the app-side normalization question raised above.

## Sources audited

- Fit3D project: https://fit3d.imar.ro/fit3d
- Fit3D official tools: https://github.com/sminchisescu-research/imar_vision_datasets_tools
- AthletePose3D official code/data: https://github.com/calvinyeungck/AthletePose3D
- AthletePose3D paper: https://arxiv.org/abs/2503.07499
