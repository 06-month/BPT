"""M0 benchmark framework tests: contracts that reports depend on."""

import numpy as np
import pytest

from bpt.benchmarks.pose import cache, normalization
from bpt.benchmarks.pose.adapters.joint_mapping import (
    COCO17_NAMES,
    COCO_DIRECT_BODY_INDICES,
    H36M17_NAMES,
    H36M_DIRECT_BODY_INDICES,
    coco17_to_h36m17_input,
    fit3d25_to_h36m17,
    h36m17_pixels_to_motion_input,
    mapping_table,
)
from bpt.benchmarks.pose.datasets import athletepose3d, fit3d
from bpt.benchmarks.pose.evaluation.metrics_2d import bbox_diagonal, bbox_from_keypoints, evaluate_2d
from bpt.benchmarks.pose.evaluation.metrics_3d import evaluate_3d
from bpt.benchmarks.pose.evaluation.metrics_angles import angle_degrees, evaluate_angles
from bpt.benchmarks.pose.evaluation.metrics_bones import evaluate_bones
from bpt.benchmarks.pose.evaluation.metrics_temporal import evaluate_temporal
from bpt.benchmarks.pose.geometry.alignment import procrustes_align, root_center, scale_align
from bpt.benchmarks.pose.geometry.projection import (
    athlete_world_to_camera,
    fit3d_world_to_camera,
    project_fit3d_distorted,
    project_pinhole,
)
from bpt.benchmarks.pose.temporal import (
    build_temporal_window,
    full_real_context_mask,
    temporal_window_indices,
)


WINDOW = 27
LOOKAHEAD = 5
TARGET_INDEX = 21


def _pose(seed=0, joints=17):
    return np.random.default_rng(seed).normal(size=(joints, 3))


# --- temporal contract -----------------------------------------------------


def test_window_covers_target_minus_21_to_plus_5():
    indices = temporal_window_indices(200, 50, WINDOW, LOOKAHEAD)
    assert indices.tolist() == list(range(29, 56))
    assert indices[TARGET_INDEX] == 50


def test_window_pads_by_repeating_clip_boundaries():
    start = temporal_window_indices(100, 0, WINDOW, LOOKAHEAD)
    assert start[:TARGET_INDEX + 1].tolist() == [0] * (TARGET_INDEX + 1)
    assert start[TARGET_INDEX] == 0
    end = temporal_window_indices(100, 99, WINDOW, LOOKAHEAD)
    assert end[TARGET_INDEX] == 99
    assert end[TARGET_INDEX:].tolist() == [99] * (WINDOW - TARGET_INDEX)


def test_build_window_keeps_target_frame_identity():
    sequence = np.arange(300 * 17 * 3, dtype=np.float32).reshape(300, 17, 3)
    window, indices, target_index = build_temporal_window(sequence, 137, WINDOW, LOOKAHEAD)
    assert window.shape == (WINDOW, 17, 3)
    assert target_index == TARGET_INDEX
    assert indices[target_index] == 137
    # The comparison frame must be index 21, never the latest input frame.
    assert np.array_equal(window[target_index], sequence[137])
    assert not np.array_equal(window[-1], sequence[137])


def test_full_real_context_excludes_padded_frames():
    mask = full_real_context_mask(60, WINDOW, LOOKAHEAD)
    assert mask.sum() == 60 - TARGET_INDEX - LOOKAHEAD
    assert not mask[TARGET_INDEX - 1] and mask[TARGET_INDEX]
    assert mask[60 - 1 - LOOKAHEAD] and not mask[60 - LOOKAHEAD]


def test_window_rejects_out_of_range_target():
    with pytest.raises(IndexError):
        temporal_window_indices(10, 10)


# --- joint mapping ---------------------------------------------------------


def test_direct_body_indices_name_the_same_joints():
    for coco_index, h36m_index in zip(COCO_DIRECT_BODY_INDICES, H36M_DIRECT_BODY_INDICES):
        assert COCO17_NAMES[coco_index] == H36M17_NAMES[h36m_index]


def test_coco_to_h36m_input_matches_screen_normalization_formula():
    width, height = 900, 900
    coco = np.zeros((17, 3), dtype=np.float32)
    coco[:, 0] = np.linspace(100, 800, 17)
    coco[:, 1] = np.linspace(50, 850, 17)
    coco[:, 2] = 0.9
    motion = coco17_to_h36m17_input(coco, width, height)
    assert motion.shape == (17, 3)
    left_hip, right_hip = coco[11, :2], coco[12, :2]
    pelvis = (left_hip + right_hip) / 2.0
    expected = [pelvis[0] / width * 2 - 1, pelvis[1] / width * 2 - height / width]
    assert motion[0, :2] == pytest.approx(expected, abs=1e-5)
    assert motion[:, 2] == pytest.approx(0.9, abs=1e-5)


def test_oracle_input_defaults_to_unit_confidence():
    points = np.random.default_rng(1).uniform(0, 900, size=(17, 2))
    motion = h36m17_pixels_to_motion_input(points, 900, 900)
    assert motion.shape == (17, 3)
    assert np.all(motion[:, 2] == 1.0)
    with pytest.raises(ValueError):
        h36m17_pixels_to_motion_input(points[:16], 900, 900)


def test_fit3d25_keeps_the_first_17_h36m_joints():
    joints = np.arange(25 * 3, dtype=np.float64).reshape(25, 3)
    assert np.array_equal(fit3d25_to_h36m17(joints), joints[:17])
    with pytest.raises(ValueError):
        fit3d25_to_h36m17(joints[:16])


def test_mapping_table_marks_face_joints_invalid():
    rows = {row["rtmpose_coco_joint"]: row for row in mapping_table()}
    assert rows["left_shoulder"]["valid_primary_2d"] is True
    assert rows["nose"]["valid_primary_2d"] is False
    assert rows["nose"]["fit3d_gt_joint"] is None
    assert sum(row["valid_primary_2d"] for row in rows.values()) == 12


# --- camera geometry -------------------------------------------------------


def test_fit3d_world_to_camera_matches_official_row_vector_form():
    rotation = _rotation_z(0.3)
    translation = np.array([1.0, -2.0, 0.5])
    world = np.random.default_rng(2).normal(size=(17, 3))
    expected = np.stack([rotation @ (point - translation) for point in world])
    assert fit3d_world_to_camera(world, rotation, translation) == pytest.approx(expected)


def test_athlete_world_to_camera_applies_the_yz_row_sign_correction():
    rotation = _rotation_z(0.2)
    position = np.array([0.5, 1.5, -3.0])
    world = np.random.default_rng(3).normal(size=(17, 3))
    corrected = rotation.copy()
    corrected[1:, :] *= -1.0
    expected = np.stack([corrected @ (point - position) for point in world])
    assert athlete_world_to_camera(world, rotation, position) == pytest.approx(expected)


def test_distorted_projection_equals_pinhole_without_distortion():
    points = np.array([[0.1, -0.2, 2.0], [0.4, 0.3, 3.5], [-0.3, 0.1, 1.5]])
    focal, center = np.array([1029.0, 1025.0]), np.array([469.0, 471.0])
    plain = project_pinhole(points, focal, center)
    distorted = project_fit3d_distorted(points, focal, center, np.zeros(3), np.zeros(2))
    assert distorted == pytest.approx(plain)


def test_distortion_moves_points_away_from_the_pinhole_projection():
    points = np.array([[0.35, 0.30, 1.0]])
    focal, center = np.array([1000.0, 1000.0]), np.array([450.0, 450.0])
    plain = project_pinhole(points, focal, center)
    distorted = project_fit3d_distorted(
        points, focal, center, np.array([-0.204, 0.090, 0.0039]), np.array([0.00064, 0.00358])
    )
    assert np.linalg.norm(distorted - plain) > 1.0


# --- alignment -------------------------------------------------------------


def test_root_center_puts_the_pelvis_at_the_origin():
    pose = _pose(4)
    assert root_center(pose)[0] == pytest.approx(np.zeros(3))


def test_scale_align_recovers_a_known_scalar():
    gt = root_center(_pose(5))
    prediction = gt / 2.5
    aligned, scales = scale_align(prediction, gt)
    assert scales == pytest.approx(2.5)
    assert aligned == pytest.approx(gt)


def test_procrustes_recovers_rotation_scale_and_translation():
    gt = _pose(6)
    rotation, scale, shift = _rotation_z(0.7), 1.8, np.array([2.0, -1.0, 0.5])
    prediction = (gt @ rotation.T) * scale + shift
    aligned = procrustes_align(prediction, gt)
    assert aligned == pytest.approx(gt, abs=1e-8)


def test_alignment_ignores_masked_out_joints():
    gt = root_center(_pose(7))
    prediction = gt.copy()
    prediction[3] = 1e6
    valid = np.ones(17, dtype=bool)
    valid[3] = False
    _, scales = scale_align(prediction, gt, valid)
    assert scales == pytest.approx(1.0)


# --- metrics ---------------------------------------------------------------


def test_2d_metrics_use_the_bbox_diagonal_as_the_single_scale():
    gt = np.zeros((4, 12, 2))
    prediction = gt.copy()
    prediction[..., 0] += 5.0  # 5px error everywhere
    boxes = np.tile([0.0, 0.0, 30.0, 40.0], (4, 1))  # diagonal 50
    valid = np.ones((4, 12), dtype=bool)
    result = evaluate_2d(prediction, gt, valid, boxes)
    assert bbox_diagonal(boxes)[0] == pytest.approx(50.0)
    assert result["mean_pixel_error"] == pytest.approx(5.0)
    assert result["nme"] == pytest.approx(0.1)
    assert result["pck_0.05"] == 0.0
    assert result["pck_0.10"] == 1.0
    assert result["count"] == 48


def test_2d_metrics_never_threshold_predictions_out():
    gt = np.zeros((2, 12, 2))
    prediction = gt.copy()
    prediction[1] += 500.0
    boxes = np.tile([0.0, 0.0, 30.0, 40.0], (2, 1))
    result = evaluate_2d(prediction, gt, np.ones((2, 12), dtype=bool), boxes)
    assert result["count"] == 24
    assert result["pck_0.20"] == pytest.approx(0.5)


def test_bbox_from_keypoints_uses_only_valid_joints():
    points = np.array([[[0.0, 0.0], [10.0, 20.0], [999.0, 999.0]]])
    valid = np.array([[True, True, False]])
    assert bbox_from_keypoints(points, valid)[0] == pytest.approx([0.0, 0.0, 10.0, 20.0])


def test_3d_metrics_are_zero_for_a_perfect_prediction():
    gt = _pose(8)[None]
    result = evaluate_3d(gt.copy(), gt, np.ones((1, 17), dtype=bool))
    assert result["mpjpe"] == pytest.approx(0.0, abs=1e-9)
    assert result["pa_mpjpe"] == pytest.approx(0.0, abs=1e-9)


def test_scale_error_survives_mpjpe_but_not_n_mpjpe():
    gt = root_center(_pose(9))[None]
    prediction = gt * 0.5
    result = evaluate_3d(prediction, gt, np.ones((1, 17), dtype=bool))
    assert result["mpjpe"] > 0.1
    assert result["n_mpjpe"] == pytest.approx(0.0, abs=1e-9)
    assert result["scales"][0] == pytest.approx(2.0)


def test_rotation_error_survives_n_mpjpe_but_not_pa_mpjpe():
    gt = root_center(_pose(10))[None]
    prediction = gt @ _rotation_z(0.4).T
    result = evaluate_3d(prediction, gt, np.ones((1, 17), dtype=bool))
    assert result["n_mpjpe"] > 0.05
    assert result["pa_mpjpe"] == pytest.approx(0.0, abs=1e-8)


def test_angle_metrics_measure_degrees_on_h36m_indices():
    assert angle_degrees(np.array([1.0, 0, 0]), np.zeros(3), np.array([0, 1.0, 0])) == pytest.approx(90.0)
    gt = _pose(11)[None]
    result = evaluate_angles(gt.copy(), gt, np.ones((1, 17), dtype=bool))
    assert result["mae_degrees"] == pytest.approx(0.0, abs=1e-9)
    assert set(result["per_angle"]) >= {"left_elbow", "right_elbow", "left_knee", "right_knee"}


def test_bone_metrics_report_absolute_and_relative_error():
    gt = np.zeros((3, 17, 3))
    gt[:, 4] = [0.0, 0.4, 0.0]  # pelvis -> left hip, length 0.4
    prediction = gt.copy()
    prediction[:, 4] = [0.0, 0.5, 0.0]
    result = evaluate_bones(prediction, gt, np.ones((3, 17), dtype=bool))
    bone = result["per_bone"]["pelvis_left_hip"]
    assert bone["absolute_error"] == pytest.approx(0.1)
    assert bone["relative_error"] == pytest.approx(0.25)
    assert bone["prediction_variance"] == pytest.approx(0.0, abs=1e-12)


def test_temporal_metrics_ignore_a_constant_offset_and_scale_with_fps():
    gt = np.cumsum(np.random.default_rng(12).normal(size=(30, 17, 3)), axis=0)
    prediction = gt + np.array([1.0, -2.0, 0.5])
    valid = np.ones((30, 17), dtype=bool)
    per_frame = evaluate_temporal(prediction, gt, valid)
    assert per_frame["mpjve"] == pytest.approx(0.0, abs=1e-9)
    assert per_frame["time_basis"] == "per_frame"
    noisy = gt.copy()
    noisy[1::2] += 0.1
    at_50fps = evaluate_temporal(noisy, gt, valid, fps=50.0)
    at_100fps = evaluate_temporal(noisy, gt, valid, fps=100.0)
    assert at_50fps["fps"] == 50.0
    assert at_100fps["mpjve"] == pytest.approx(2.0 * at_50fps["mpjve"])


# --- cache -----------------------------------------------------------------


def test_cache_round_trips_arrays_and_metadata(tmp_path):
    arrays = {"coco17": np.arange(34, dtype=np.float32).reshape(2, 17), "frame_ids": np.arange(2)}
    metadata = {"model": "motionagformer_xs", "lookahead": 5}
    cache.save(tmp_path, "s02/deadlift", arrays, metadata)
    loaded = cache.load(tmp_path, "s02/deadlift")
    assert loaded is not None
    restored, restored_metadata = loaded
    assert np.array_equal(restored["coco17"], arrays["coco17"])
    assert restored_metadata == metadata
    assert cache.cached_keys(tmp_path) == ["s02/deadlift"]


def test_cache_miss_on_changed_metadata_or_missing_entry(tmp_path):
    cache.save(tmp_path, "seq", {"x": np.zeros(3)}, {"preprocessing": "full_image_affine"})
    assert cache.is_cached(tmp_path, "seq", {"preprocessing": "full_image_affine"})
    assert not cache.is_cached(tmp_path, "seq", {"preprocessing": "fast_resize"})
    assert cache.load(tmp_path, "absent") is None


def test_cache_miss_on_version_change(tmp_path, monkeypatch):
    cache.save(tmp_path, "seq", {"x": np.zeros(3)}, {})
    monkeypatch.setattr(cache, "CACHE_VERSION", cache.CACHE_VERSION + 1)
    assert cache.load(tmp_path, "seq") is None


# --- dataset loaders -------------------------------------------------------


def test_fit3d_discovery_and_camera_loading(tmp_path):
    subject = tmp_path / "test" / "s02"
    (subject / "videos").mkdir(parents=True)
    (subject / "camera_parameters").mkdir(parents=True)
    (subject / "videos" / "deadlift.mp4").write_bytes(b"")
    camera = {
        "extrinsics": {"R": np.eye(3).tolist(), "T": [[1.0, 2.0, 3.0]]},
        "intrinsics_w_distortion": {
            "f": [[1000.0, 1001.0]],
            "c": [[450.0, 451.0]],
            "k": [[-0.2, 0.09, 0.003]],
            "p": [[0.0006, 0.0035]],
        },
        "intrinsics_wo_distortion": {"f": [1000.0, 1001.0], "c": [450.0, 451.0]},
    }
    import json

    (subject / "camera_parameters" / "deadlift.json").write_text(json.dumps(camera))
    sequences = fit3d.discover(tmp_path)
    assert [s.key for s in sequences] == ["s02/deadlift"]
    loaded = fit3d.load_camera(sequences[0].camera_path)
    assert loaded["extrinsics"]["T"].shape == (3,)
    assert loaded["intrinsics_w_distortion"]["k"].shape == (3,)
    assert loaded["intrinsics_w_distortion"]["f"] == pytest.approx([1000.0, 1001.0])


def test_fit3d_reports_no_ground_truth_when_none_is_supplied(tmp_path):
    assert fit3d.load_joints3d_25(tmp_path, "s02", "deadlift") is None
    assert fit3d.has_ground_truth(None, "s02", "deadlift") is False


def test_athletepose3d_groups_and_stacks_sequences(tmp_path):
    records = [_athlete_record(image_id) for image_id in (2, 0, 1)]
    records.append(_athlete_record(0, camera="fs_camera_2"))
    path = tmp_path / "valid.pkl"
    import pickle

    path.write_bytes(pickle.dumps(records))
    sequences = athletepose3d.group_sequences(athletepose3d.load_records(path))
    assert [s.key for s in sequences] == [
        "S1/fs/Axel_1/fs_camera_1",
        "S1/fs/Axel_1/fs_camera_2",
    ]
    arrays = athletepose3d.sequence_arrays(sequences[0])
    assert arrays["frame_ids"].tolist() == [0, 1, 2]
    assert arrays["joints_2d"].shape == (3, 17, 2)
    assert arrays["joints_3d_camera"].shape == (3, 17, 3)
    assert arrays["boxes_xyxy"].shape == (3, 4)
    assert (arrays["width"], arrays["height"], arrays["fps"]) == (1920, 1088, 60.0)
    assert arrays["units"] == "millimetre"


def _athlete_record(image_id, camera="fs_camera_1"):
    joints = np.full((17, 3), float(image_id))
    return {
        "imageid": image_id,
        "cameraid": camera,
        "subject": "S1",
        "action": "fs",
        "subaction": "Axel_1",
        "image_path": f"pose_3d/valid_img/S1_Axel_1_{image_id}.jpg",
        "joint_3d_image": joints,
        "joint_3d_camera": joints * 10.0,
        "box": np.array([0.0, 0.0, 100.0, 200.0]),
        "video_width": 1920,
        "video_height": 1088,
        "fps": 60.0,
    }


def _rotation_z(angle):
    cos, sin = np.cos(angle), np.sin(angle)
    return np.array([[cos, -sin, 0.0], [sin, cos, 0.0], [0.0, 0.0, 1.0]])


# --- normalization contract ------------------------------------------------


def test_full_image_normalization_round_trips_through_denormalize():
    points = np.random.default_rng(13).uniform(0, 900, size=(40, 17, 2))
    windows = normalization.build_pixel_windows(points)
    inputs, terms = normalization.normalize_windows(windows, 900, 1600, "full_image")
    assert inputs.shape == (40, 27, 17, 3)
    assert np.all(inputs[..., 2] == 1.0)
    targets = np.concatenate(
        (inputs[:, normalization.TARGET_INDEX, :, :2], np.zeros((40, 17, 1))), axis=-1
    )
    restored = normalization.denormalize_targets(targets, terms)
    assert restored[..., :2] == pytest.approx(points, abs=1e-3)  # float32 inputs


def test_full_image_normalization_matches_the_production_formula():
    points = np.array([[[100.0, 200.0]] * 17])
    windows = normalization.build_pixel_windows(points)
    inputs, _ = normalization.normalize_windows(windows, 900, 1600, "full_image")
    assert inputs[0, 0, 0, 0] == pytest.approx(100.0 / 900 * 2 - 1)
    assert inputs[0, 0, 0, 1] == pytest.approx(200.0 / 900 * 2 - 1600 / 900)


def test_person_crop_normalization_fills_the_normalized_range():
    points = np.random.default_rng(14).uniform(800, 860, size=(30, 17, 2))
    windows = normalization.build_pixel_windows(points)
    full, _ = normalization.normalize_windows(windows, 1920, 1088, "full_image")
    crop, terms = normalization.normalize_windows(windows, 1920, 1088, "person_crop")
    # The same tiny subject occupies far more of the crop-normalized range.
    full_span = np.ptp(full[..., 0], axis=(1, 2)).mean()
    crop_span = np.ptp(crop[..., 0], axis=(1, 2)).mean()
    assert crop_span > 10 * full_span
    assert crop[..., :2].min() >= -1.0 and crop[..., :2].max() <= 1.0
    targets = np.concatenate((crop[:, normalization.TARGET_INDEX, :, :2], np.zeros((30, 17, 1))), axis=-1)
    assert normalization.denormalize_targets(targets, terms)[..., :2] == pytest.approx(points, abs=1e-3)


def test_depth_is_denormalized_with_the_same_scale():
    windows = np.zeros((2, 27, 17, 2))
    _, terms = normalization.normalize_windows(windows, 900, 1600, "full_image")
    prediction = np.zeros((2, 17, 3))
    prediction[..., 2] = 0.5
    assert normalization.denormalize_targets(prediction, terms)[..., 2] == pytest.approx(0.5 * 900 / 2)


def test_flip_is_an_involution_that_swaps_left_and_right():
    data = np.random.default_rng(15).normal(size=(3, 27, 17, 3))
    flipped = normalization.flip_data(data)
    assert normalization.flip_data(flipped) == pytest.approx(data)
    assert flipped[..., 4, 1:] == pytest.approx(data[..., 1, 1:])  # left hip <-> right hip
    assert flipped[..., 4, 0] == pytest.approx(-data[..., 1, 0])
    assert flipped[..., 0, :] == pytest.approx(data[..., 0, :] * [-1, 1, 1])  # pelvis stays


def test_unknown_normalization_mode_is_rejected():
    with pytest.raises(ValueError):
        normalization.normalize_windows(np.zeros((1, 27, 17, 2)), 900, 900, "bbox_square")
