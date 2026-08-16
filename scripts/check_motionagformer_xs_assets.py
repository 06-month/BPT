import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_DIR = ROOT / "external" / "MotionAGFormer"
CONFIG_PATH = REPO_DIR / "configs" / "h36m" / "MotionAGFormer-xsmall.yaml"
CHECKPOINT_CANDIDATES = [
    REPO_DIR / "checkpoint" / "motionagformer-xs-h36m.pth.tr",
    REPO_DIR / "checkpoint" / "MotionAGFormer-XS-H36M.pth.tr",
    REPO_DIR / "checkpoint" / "motionagformer-xsmall-h36m.pth.tr",
]
README_PATH = REPO_DIR / "README.md"
OFFICIAL_H36M_WEIGHT_LINK = "https://drive.google.com/file/d/1Pab7cPvnWG8NOVd0nnL1iqAfYCUY4hDH/view?usp=sharing"


def main():
    config_info = parse_config(CONFIG_PATH) if CONFIG_PATH.exists() else {}
    checkpoint = first_existing(CHECKPOINT_CANDIDATES)
    status = {
        "repo_exists": REPO_DIR.exists(),
        "xs_config_exists": CONFIG_PATH.exists(),
        "xs_checkpoint_exists": checkpoint is not None,
        "expected_config_path": str(CONFIG_PATH),
        "expected_checkpoint_path": str(CHECKPOINT_CANDIDATES[0]),
        "alternate_checkpoint_paths": [str(path) for path in CHECKPOINT_CANDIDATES[1:]],
        "ready_for_xs_inference": CONFIG_PATH.exists() and checkpoint is not None,
        "config": config_info,
        "official_h36m_weight_link_from_readme": OFFICIAL_H36M_WEIGHT_LINK,
    }
    print(json.dumps(status, indent=2, sort_keys=True))
    if checkpoint is None:
        print("MotionAGFormer-XS checkpoint is missing.")
        print("Download the official H3.6M XS weight from the MotionAGFormer README table:")
        print(f"  {OFFICIAL_H36M_WEIGHT_LINK}")
        print(f"Place it at: {CHECKPOINT_CANDIDATES[0]}")
    else:
        print(f"checkpoint_path={checkpoint}")
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
    result["expected_output_shape"] = "[B, 27, 17, 3]" if result.get("n_frames") == 27 else None
    result["readme_params"] = "2.2M"
    result["readme_macs"] = "1.0G"
    return result


def first_existing(paths):
    for path in paths:
        if path.exists():
            return path
    return None


if __name__ == "__main__":
    raise SystemExit(main())
