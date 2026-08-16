import argparse
from importlib.util import find_spec
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bpt_mplconfig")


def parse_args():
    parser = argparse.ArgumentParser(description="Smoke test MediaPipe Hands crop mode.")
    parser.add_argument("image_path", nargs="?", help="Optional image path.")
    parser.add_argument(
        "--crop",
        default="full",
        help='Crop mode: "full", "center", or explicit "x1,y1,x2,y2".',
    )
    parser.add_argument(
        "--save-debug-crop",
        help="Optional path where the actual crop image should be saved.",
    )
    parser.add_argument(
        "--inject-standalone-hands",
        action="store_true",
        help="Construct MediaPipe Hands in the smoke script and inject it into the runner.",
    )
    return parser.parse_args()


def load_image(path):
    try:
        import cv2
    except ModuleNotFoundError:
        cv2 = None

    if cv2 is not None:
        image_bgr = cv2.imread(str(path))
        if image_bgr is None:
            raise ValueError(f"Could not read image: {path}")
        return image_bgr, "BGR"

    try:
        from PIL import Image
        import numpy as np
    except ModuleNotFoundError as exc:
        raise ImportError("Reading image paths requires cv2 or Pillow.") from exc

    return np.array(Image.open(path).convert("RGB")), "RGB"


def blank_image():
    import numpy as np

    return np.zeros((480, 640, 3), dtype=np.uint8), "BGR"


def image_shape(image):
    shape = getattr(image, "shape", None)
    if shape is not None:
        return tuple(int(value) for value in shape)
    return (len(image), len(image[0]), len(image[0][0]) if image and image[0] else 0)


def image_width_height(image):
    shape = image_shape(image)
    return shape[1], shape[0]


def parse_crop(crop_spec, image):
    image_w, image_h = image_width_height(image)
    if crop_spec == "full":
        return (0, 0, image_w, image_h)
    if crop_spec == "center":
        side = int(min(image_w, image_h) * 0.8)
        cx = image_w // 2
        cy = image_h // 2
        x1 = max(0, cx - side // 2)
        y1 = max(0, cy - side // 2)
        x2 = min(image_w, x1 + side)
        y2 = min(image_h, y1 + side)
        return (x1, y1, x2, y2)

    parts = crop_spec.split(",")
    if len(parts) != 4:
        raise ValueError('--crop must be "full", "center", or "x1,y1,x2,y2"')
    x1, y1, x2, y2 = (int(value) for value in parts)
    if not (0 <= x1 < x2 <= image_w and 0 <= y1 < y2 <= image_h):
        raise ValueError(f"crop_box {(x1, y1, x2, y2)} is outside image bounds")
    return (x1, y1, x2, y2)


def crop_image(image, crop_box):
    x1, y1, x2, y2 = crop_box
    return image[y1:y2, x1:x2]


def save_image(image, path, color_format):
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import cv2

        output = image
        if color_format == "RGB":
            output = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(output_path), output)
        return
    except ModuleNotFoundError:
        pass

    try:
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise ImportError("Saving debug crops requires cv2 or Pillow.") from exc

    output = image
    if color_format == "BGR":
        output = image[:, :, ::-1]
    Image.fromarray(output).save(output_path)


def main():
    args = parse_args()
    os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"
    if find_spec("mediapipe") is None:
        print("MediaPipe is not installed; skipping crop smoke test.")
        return 0

    from pose_feedback.hand.mediapipe_hand_runner import MediaPipeHandsRunner

    image, color_format = (
        load_image(Path(args.image_path)) if args.image_path else blank_image()
    )
    crop_box = parse_crop(args.crop, image)
    print({"image_shape": image_shape(image), "crop_box": crop_box})
    if args.save_debug_crop:
        save_image(crop_image(image, crop_box), args.save_debug_crop, color_format)
        print({"saved_debug_crop": args.save_debug_crop})

    print({"inject_standalone_hands": args.inject_standalone_hands})
    hands = None
    if args.inject_standalone_hands:
        try:
            import mediapipe as mp

            hands = mp.solutions.hands.Hands(
                static_image_mode=True,
                max_num_hands=1,
                min_detection_confidence=0.3,
            )
        except Exception as exc:
            print({"failure_stage": "manual_hands_construction", "reason": str(exc)})
            return 0

    try:
        runner = create_runner(
            MediaPipeHandsRunner=MediaPipeHandsRunner,
            color_format=color_format,
            hands=hands,
        )
    except Exception as exc:
        print({"failure_stage": "runner_construction", "reason": str(exc)})
        return 0

    try:
        results = runner.run_crop(image, crop_box)
    except Exception as exc:
        print({"failure_stage": "run_crop_process", "reason": str(exc)})
        return 0
    finally:
        runner.close()

    print({"detected_hands": len(results)})
    for index, result in enumerate(results):
        wrist_px = result["wrist_px"]
        print(
            {
                "index": index,
                "handedness": result["handedness"],
                "wrist_px": tuple(float(value) for value in wrist_px),
                "hand_landmarks_present": result["hand_landmarks"] is not None,
                "hand_world_landmarks_present": result["hand_world_landmarks"] is not None,
            },
        )
    return 0


def create_runner(MediaPipeHandsRunner, color_format, hands=None):
    return MediaPipeHandsRunner(
        static_image_mode=True,
        max_num_hands=1,
        min_detection_confidence=0.3,
        min_tracking_confidence=0.3,
        cpu_only=True,
        input_color_format=color_format,
        hands=hands,
    )


if __name__ == "__main__":
    raise SystemExit(main())
