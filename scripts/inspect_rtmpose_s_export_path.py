"""Inspect RTMPose-s model-forward export feasibility for Core ML."""

import json
import sys
import traceback
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from rtmpose_s_coreml_common import (  # noqa: E402
    CHECKPOINT_PATH,
    CONFIG_PATH,
    INPUT_SHAPE,
    INPUT_SIZE_WH,
    VIDEO_PATH,
    forward_output_dict,
    load_rtmpose_model,
    prepare_input_tensor_from_frame,
    read_first_video_frame,
    shape_dict,
)


OUTPUT_JSON = ROOT / "assets/coreml/rtmpose_s_export_inspection.json"


def main():
    result = base_result()
    try:
        from mmengine import Config

        cfg = Config.fromfile(str(CONFIG_PATH))
        model_cfg = cfg.get("model", {})
        result.update(config_summary(cfg, model_cfg))
    except Exception as exc:
        result["config_parse_error"] = f"{type(exc).__name__}: {exc}"

    try:
        model = load_rtmpose_model(device="cpu")
        result["model_loaded"] = True
        result["model_class"] = f"{type(model).__module__}.{type(model).__name__}"
        result["head_class"] = f"{type(model.head).__module__}.{type(model.head).__name__}"
        result["backbone_class"] = f"{type(model.backbone).__module__}.{type(model.backbone).__name__}"
        result["data_preprocessor_class"] = (
            f"{type(model.data_preprocessor).__module__}.{type(model.data_preprocessor).__name__}"
        )
        input_tensor = prepare_input_tensor_from_frame(read_first_video_frame(VIDEO_PATH))
        result["input_shape"] = list(input_tensor.shape)
        with torch.no_grad():
            raw_outputs = model.head(model.extract_feat(torch.from_numpy(input_tensor)))
        result["raw_output_shapes"] = shape_dict(forward_output_dict(raw_outputs))
        result["raw_output_names"] = list(forward_output_dict(raw_outputs).keys())
        result["decoded_keypoint_shape_if_available"] = decoded_keypoint_shape(model)
    except Exception as exc:
        result["model_loaded"] = False
        result["load_or_forward_error"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc()

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def base_result():
    return {
        "config_path": str(CONFIG_PATH.relative_to(ROOT)),
        "checkpoint_path": str(CHECKPOINT_PATH.relative_to(ROOT)),
        "model_loaded": False,
        "input_shape": list(INPUT_SHAPE),
        "input_size_wh": list(INPUT_SIZE_WH),
        "raw_output_shapes": {},
        "decoded_keypoint_shape_if_available": None,
        "uses_simcc": True,
        "postprocess_outside_model": [
            "person detector or person bbox selection",
            "bbox center/scale calculation",
            "TopdownAffine crop and resize to 192x256",
            "BGR to RGB conversion and mean/std normalization",
            "SimCC decode from logits to COCO17 keypoints",
            "inverse affine transform back to original image coordinates",
            "COCO17 to H36M17 conversion for MotionAGFormer-XS",
            "2D normalization and 27-frame ring buffer",
        ],
        "coreml_conversion_risk_notes": [
            "MMPose preprocessing and Python data samples are not part of the Core ML graph.",
            "Only the tensor forward model.extract_feat + model.head is targeted for conversion.",
            "RTMCCHead returns SimCC logits, not final image-space COCO17 keypoints.",
            "CSPNeXt backbone contains SiLU, SyncBatchNorm-derived normalization, pooling, and channel attention.",
            "Core ML conversion success does not imply ANE execution.",
        ],
        "detector_status": "not included; existing RTMPoseRunner passes a full-image bbox to inference_topdown",
        "video_path": str(VIDEO_PATH.relative_to(ROOT)),
    }


def config_summary(cfg, model_cfg):
    codec = cfg.get("codec", {})
    head = model_cfg.get("head", {})
    return {
        "data_mode": cfg.get("data_mode"),
        "model_type": model_cfg.get("type"),
        "backbone_type": model_cfg.get("backbone", {}).get("type"),
        "head_type": head.get("type"),
        "codec_type": codec.get("type"),
        "simcc_split_ratio": codec.get("simcc_split_ratio"),
        "test_cfg": model_cfg.get("test_cfg"),
        "uses_simcc": codec.get("type") == "SimCCLabel" or head.get("type") == "RTMCCHead",
    }


def decoded_keypoint_shape(model):
    from mmpose.apis import inference_topdown

    frame = read_first_video_frame(VIDEO_PATH)
    image_h, image_w = frame.shape[:2]
    bbox = np.asarray([[0.0, 0.0, float(image_w), float(image_h)]], dtype="float32")
    samples = inference_topdown(model, frame, bboxes=bbox)
    if not samples:
        return None
    keypoints = samples[0].pred_instances.keypoints
    return list(np.asarray(keypoints).shape)


if __name__ == "__main__":
    raise SystemExit(main())
