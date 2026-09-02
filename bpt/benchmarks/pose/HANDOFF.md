# M0 Pose Benchmark Handoff

Updated: 2026-09-02 (Asia/Seoul)

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

## Current phase / next action

- Phase 1 repository and dataset-convention audit: complete.
- Phase 2 framework implementation: in progress.
- Next: implement/test mappings, projections, alignments, metrics, temporal
  indexing, cache serialization and dataset loaders. Then restore the official
  pinned MotionAGFormer XS checkpoint/backend and run smoke tests.

## Sources audited

- Fit3D project: https://fit3d.imar.ro/fit3d
- Fit3D official tools: https://github.com/sminchisescu-research/imar_vision_datasets_tools
- AthletePose3D official code/data: https://github.com/calvinyeungck/AthletePose3D
- AthletePose3D paper: https://arxiv.org/abs/2503.07499
