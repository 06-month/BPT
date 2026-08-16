"""Compare RTMPose and MediaPipe wrist-source JSONL jitter diagnostics."""

import argparse
import json
import math
from pathlib import Path


SIDES = ("left", "right")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtmpose-jsonl", required=True)
    parser.add_argument("--mediapipe-jsonl", required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    rtmpose_rows = load_jsonl(Path(args.rtmpose_jsonl))
    mediapipe_rows = load_jsonl(Path(args.mediapipe_jsonl))
    report = {
        "rtmpose_jsonl": args.rtmpose_jsonl,
        "mediapipe_jsonl": args.mediapipe_jsonl,
        "frames": {
            "rtmpose": len(rtmpose_rows),
            "mediapipe": len(mediapipe_rows),
        },
        "sides": {},
    }
    for side in SIDES:
        side_report = {
            "rtmpose_mode": analyze_side(rtmpose_rows, side),
            "mediapipe_mode": analyze_side(mediapipe_rows, side),
        }
        side_report["comparison"] = compare_side(side_report)
        report["sides"][side] = side_report
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def analyze_side(rows, side):
    return {
        "raw_rtmpose_wrist_2d": sequence_stats(rows, f"{side}_rtmpose_wrist_px"),
        "mediapipe_wrist_2d": sequence_stats(rows, f"{side}_mediapipe_wrist_px"),
        "motionagformer_input_wrist_2d": sequence_stats(
            rows,
            f"{side}_motionagformer_input_wrist_px",
        ),
        "motionagformer_wrist_3d": sequence_stats(rows, f"{side}_motionagformer_wrist_3d"),
        "motionagformer_elbow_wrist_length_3d": scalar_stats(
            [row.get(f"{side}_motionagformer_elbow_wrist_length_3d") for row in rows],
        ),
        "source_counts": source_counts(rows, side),
        "hand_detected_count": sum(bool(row.get(side, {}).get("hand_detected")) for row in rows),
        "anchor_error": scalar_stats([row.get(f"{side}_hand_3d_anchor_error") for row in rows]),
    }


def compare_side(side_report):
    rt_3d = side_report["rtmpose_mode"]["motionagformer_wrist_3d"]
    mp_3d = side_report["mediapipe_mode"]["motionagformer_wrist_3d"]
    rt_bone = side_report["rtmpose_mode"]["motionagformer_elbow_wrist_length_3d"]
    mp_bone = side_report["mediapipe_mode"]["motionagformer_elbow_wrist_length_3d"]
    return {
        "motionagformer_3d_velocity_mean_delta_mediapipe_minus_rtmpose": diff_or_none(
            mp_3d["velocity_norm"]["mean"],
            rt_3d["velocity_norm"]["mean"],
        ),
        "motionagformer_3d_acceleration_mean_delta_mediapipe_minus_rtmpose": diff_or_none(
            mp_3d["acceleration_norm"]["mean"],
            rt_3d["acceleration_norm"]["mean"],
        ),
        "bone_length_std_delta_mediapipe_minus_rtmpose": diff_or_none(
            mp_bone["std"],
            rt_bone["std"],
        ),
        "interpretation": interpretation(rt_3d, mp_3d, rt_bone, mp_bone),
    }


def sequence_stats(rows, key):
    points = [row.get(key) for row in rows]
    valid = [as_vector(point) for point in points if as_vector(point) is not None]
    if len(valid) < 1:
        return empty_sequence_stats()
    velocities = [distance(valid[idx], valid[idx - 1]) for idx in range(1, len(valid))]
    accelerations = [
        distance(vector_sub(valid[idx], scalar_mul(valid[idx - 1], 2.0), valid[idx - 2]), zero(len(valid[idx])))
        for idx in range(2, len(valid))
    ]
    return {
        "valid_count": len(valid),
        "velocity_norm": scalar_stats(velocities),
        "acceleration_norm": scalar_stats(accelerations),
    }


def scalar_stats(values):
    valid = [float(value) for value in values if value is not None and not is_nan(value)]
    if not valid:
        return {"count": 0, "mean": None, "std": None, "p95": None, "max": None}
    mean = sum(valid) / len(valid)
    var = sum((value - mean) ** 2 for value in valid) / len(valid)
    return {
        "count": len(valid),
        "mean": mean,
        "std": math.sqrt(var),
        "p95": percentile(valid, 95),
        "max": max(valid),
    }


def source_counts(rows, side):
    counts = {"rtmpose": 0, "mediapipe": 0, "fallback": 0, "missing": 0}
    key = f"{side}_motionagformer_wrist_source_used"
    for row in rows:
        source = row.get(key)
        if source in counts:
            counts[source] += 1
        else:
            counts["missing"] += 1
    return counts


def interpretation(rt_3d, mp_3d, rt_bone, mp_bone):
    if rt_3d["velocity_norm"]["mean"] is None or mp_3d["velocity_norm"]["mean"] is None:
        return "3D wrist jitter not available in one or both runs."
    jitter_delta = mp_3d["velocity_norm"]["mean"] - rt_3d["velocity_norm"]["mean"]
    bone_delta = None
    if rt_bone["std"] is not None and mp_bone["std"] is not None:
        bone_delta = mp_bone["std"] - rt_bone["std"]
    if jitter_delta < 0 and (bone_delta is None or bone_delta <= 0):
        return "MediaPipe wrist source reduced measured 3D wrist velocity without increasing bone-length variation."
    if jitter_delta < 0:
        return "MediaPipe wrist source reduced measured 3D wrist velocity but may increase bone-length variation."
    return "MediaPipe wrist source did not reduce measured 3D wrist velocity in this run."


def empty_sequence_stats():
    return {
        "valid_count": 0,
        "velocity_norm": scalar_stats([]),
        "acceleration_norm": scalar_stats([]),
    }


def as_vector(value):
    if value is None:
        return None
    if len(value) < 2:
        return None
    return [float(v) for v in value]


def distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def vector_sub(a, b, c):
    return [x - y + z for x, y, z in zip(a, b, c)]


def scalar_mul(a, value):
    return [x * value for x in a]


def zero(length):
    return [0.0 for _ in range(length)]


def percentile(values, pct):
    ordered = sorted(values)
    if not ordered:
        return None
    rank = (len(ordered) - 1) * pct / 100.0
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return ordered[low]
    weight = rank - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def diff_or_none(a, b):
    if a is None or b is None:
        return None
    return a - b


def is_nan(value):
    try:
        return math.isnan(float(value))
    except (TypeError, ValueError):
        return False


if __name__ == "__main__":
    raise SystemExit(main())
