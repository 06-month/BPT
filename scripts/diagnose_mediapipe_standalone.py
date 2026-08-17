import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def parse_args():
    parser = argparse.ArgumentParser(description="Diagnose standalone MediaPipe Hands.")
    parser.add_argument(
        "--import-project-first",
        action="store_true",
        help="Import pose_feedback.hand.mediapipe_hand_runner before constructing Hands.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"

    if args.import_project_first:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        import pose_feedback.hand.mediapipe_hand_runner  # noqa: F401

    import cv2
    import mediapipe as mp

    image_bgr = cv2.imread("assets/smoke/hand_crop_test.jpg")
    if image_bgr is None:
        print({"image_read": False, "path": "assets/smoke/hand_crop_test.jpg"})
        return 0
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    print({"image_shape": tuple(int(value) for value in image_bgr.shape)})
    print({"mediapipe_version": getattr(mp, "__version__", None)})
    print({"has_solutions": hasattr(mp, "solutions")})
    print({"import_project_first": args.import_project_first})

    try:
        hands = mp.solutions.hands.Hands(
            static_image_mode=True,
            max_num_hands=1,
            min_detection_confidence=0.3,
        )
    except Exception as exc:
        print({"hands_constructed": False, "reason": str(exc)})
        return 0

    try:
        results = hands.process(rgb)
    finally:
        hands.close()

    landmarks = getattr(results, "multi_hand_landmarks", None)
    handedness = getattr(results, "multi_handedness", None)
    print({"landmarks_exist": bool(landmarks)})
    if handedness:
        labels = []
        for item in handedness:
            classification = getattr(item, "classification", None)
            if classification:
                labels.append(getattr(classification[0], "label", None))
        print({"handedness": labels})
    else:
        print({"handedness": []})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
