from pathlib import Path


REPO_DIR = Path("external/MotionAGFormer")
README_PATH = REPO_DIR / "README.md"
CONFIG_PATH = REPO_DIR / "configs/h36m/MotionAGFormer-base.yaml"
CHECKPOINT_PATH = REPO_DIR / "checkpoint/motionagformer-b-h36m.pth.tr"
INPUT_NPZ_PATH = Path("assets/smoke/vedio_1_motionagformer_input_debug.npz")


def main():
    status = {
        "repo_exists": REPO_DIR.exists(),
        "readme_exists": README_PATH.exists(),
        "config_exists": CONFIG_PATH.exists(),
        "expected_config_path": str(CONFIG_PATH),
        "expected_checkpoint_path": str(CHECKPOINT_PATH),
        "input_npz_exists": INPUT_NPZ_PATH.exists(),
        "checkpoint_exists": CHECKPOINT_PATH.exists(),
    }
    status["ready_for_motionagformer_inference"] = (
        status["repo_exists"]
        and status["config_exists"]
        and status["input_npz_exists"]
        and status["checkpoint_exists"]
    )
    print(status)
    if not status["checkpoint_exists"]:
        print(
            {
                "checkpoint_missing": True,
                "official_readme_instructions": [
                    "Use the MotionAGFormer README Evaluation table, row 'MotionAGFormer-B'.",
                    "Download the official H3.6M weights from the README link:",
                    "https://drive.google.com/file/d/1Iii5EwsFFm9_9lKBUPfN8bV5LmfkNUMP/view?usp=drive_link",
                    "The demo section also refers to the same base model checkpoint.",
                    "Place or rename the downloaded file to:",
                    str(CHECKPOINT_PATH),
                ],
                "matching_config": str(CONFIG_PATH),
                "window_length": 243,
            },
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
