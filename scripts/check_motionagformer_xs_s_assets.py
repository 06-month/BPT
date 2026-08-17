import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_DIR = ROOT / "external" / "MotionAGFormer"

MODELS = {
    "xs": {
        "config": REPO_DIR / "configs" / "h36m" / "MotionAGFormer-xsmall.yaml",
        "checkpoint": REPO_DIR / "checkpoint" / "motionagformer-xs-h36m.pth.tr",
        "official_link": "https://drive.google.com/file/d/1Pab7cPvnWG8NOVd0nnL1iqAfYCUY4hDH/view?usp=sharing",
        "frames": 27,
        "params": "2.2M",
        "macs": "1.0G",
    },
    "s": {
        "config": REPO_DIR / "configs" / "h36m" / "MotionAGFormer-small.yaml",
        "checkpoint": REPO_DIR / "checkpoint" / "motionagformer-s-h36m.pth.tr",
        "official_link": "https://drive.google.com/file/d/1DrF7WZdDvRPsH12gQm5DPXbviZ4waYFf/view?usp=sharing",
        "frames": 81,
        "params": "4.8M",
        "macs": "6.6G",
    },
}


def main():
    status = {
        "repo_exists": REPO_DIR.exists(),
        "xs_config_exists": MODELS["xs"]["config"].exists(),
        "s_config_exists": MODELS["s"]["config"].exists(),
        "xs_checkpoint_exists": MODELS["xs"]["checkpoint"].exists(),
        "s_checkpoint_exists": MODELS["s"]["checkpoint"].exists(),
        "xs_expected_config_path": str(MODELS["xs"]["config"]),
        "s_expected_config_path": str(MODELS["s"]["config"]),
        "xs_expected_checkpoint_path": str(MODELS["xs"]["checkpoint"]),
        "s_expected_checkpoint_path": str(MODELS["s"]["checkpoint"]),
        "ready_for_xs_inference": MODELS["xs"]["config"].exists() and MODELS["xs"]["checkpoint"].exists(),
        "ready_for_s_inference": MODELS["s"]["config"].exists() and MODELS["s"]["checkpoint"].exists(),
        "models": {
            name: {
                "config": parse_config(meta["config"]) if meta["config"].exists() else {},
                "official_h36m_weight_link_from_readme": meta["official_link"],
                "readme_frames": meta["frames"],
                "readme_params": meta["params"],
                "readme_macs": meta["macs"],
            }
            for name, meta in MODELS.items()
        },
    }
    print(json.dumps(status, indent=2, sort_keys=True))
    for name, meta in MODELS.items():
        if not meta["checkpoint"].exists():
            print(f"MotionAGFormer-{name.upper()} checkpoint is missing.")
            print("Download the official H3.6M weight from the MotionAGFormer README table:")
            print(f"  {meta['official_link']}")
            print(f"Place it at: {meta['checkpoint']}")
    return 0


def parse_config(path):
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        clean = line.split("#", 1)[0].strip()
        if not clean or ":" not in clean:
            continue
        key, value = clean.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in {"n_frames", "dim_in", "dim_out", "num_joints", "n_layers", "dim_feat", "dim_rep"}:
            try:
                result[key] = int(value)
            except ValueError:
                result[key] = value
        elif key in {"model_name", "subset_list"}:
            result[key] = value
    n_frames = result.get("n_frames")
    if n_frames:
        result["expected_output_shape"] = f"[B, {n_frames}, 17, 3]"
    return result


if __name__ == "__main__":
    raise SystemExit(main())
