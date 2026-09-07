import json
from pathlib import Path
import subprocess
import sys
import textwrap


ROOT = Path(__file__).resolve().parents[1]
IMAGE_PATH = ROOT / "assets" / "smoke" / "hand_crop_test.jpg"


CASES = [
    {
        "name": "Case A",
        "description": "env before imports, cv2 before mediapipe, construct only",
        "cwd": str(ROOT),
        "set_env": True,
        "import_order": "cv2_then_mediapipe",
        "load_image": False,
        "process": False,
        "import_project_first": False,
        "use_runner": False,
    },
    {
        "name": "Case B",
        "description": "env before imports, mediapipe before cv2, construct only",
        "cwd": str(ROOT),
        "set_env": True,
        "import_order": "mediapipe_then_cv2",
        "load_image": False,
        "process": False,
        "import_project_first": False,
        "use_runner": False,
    },
    {
        "name": "Case C",
        "description": "no MEDIAPIPE_DISABLE_GPU, cv2 before mediapipe, construct only",
        "cwd": str(ROOT),
        "set_env": False,
        "import_order": "cv2_then_mediapipe",
        "load_image": False,
        "process": False,
        "import_project_first": False,
        "use_runner": False,
    },
    {
        "name": "Case D",
        "description": "repo root, load image, construct, process",
        "cwd": str(ROOT),
        "set_env": True,
        "import_order": "cv2_then_mediapipe",
        "load_image": True,
        "process": True,
        "import_project_first": False,
        "use_runner": False,
    },
    {
        "name": "Case E",
        "description": "/tmp cwd, absolute image path, construct, process",
        "cwd": "/tmp",
        "set_env": True,
        "import_order": "cv2_then_mediapipe",
        "load_image": True,
        "process": True,
        "import_project_first": False,
        "use_runner": False,
    },
    {
        "name": "Case F",
        "description": "repo root, import project runner module first, construct, process",
        "cwd": str(ROOT),
        "set_env": True,
        "import_order": "cv2_then_mediapipe",
        "load_image": True,
        "process": True,
        "import_project_first": True,
        "use_runner": False,
    },
    {
        "name": "Case G",
        "description": "repo root, instantiate MediaPipeHandsRunner, process crop",
        "cwd": str(ROOT),
        "set_env": True,
        "import_order": "cv2_then_mediapipe",
        "load_image": True,
        "process": True,
        "import_project_first": False,
        "use_runner": True,
    },
]


def main():
    results = []
    for case in CASES:
        result = run_case(case)
        results.append(result)
        print_case(result)
    print_summary(results)
    return 0


def run_case(case):
    config = dict(case)
    config["repo_root"] = str(ROOT)
    config["image_path"] = str(IMAGE_PATH)
    try:
        completed = subprocess.run(
            [sys.executable, "-c", subprocess_code(config)],
            cwd=case["cwd"],
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "case": case["name"],
            "description": case["description"],
            "cwd": case["cwd"],
            "python_executable": sys.executable,
            "python_version": None,
            "platform_machine": None,
            "mediapipe_version": None,
            "cv2_version": None,
            "mp_solutions_exists": None,
            "mediapipe_disable_gpu": None,
            "hands_constructed": False,
            "process_succeeded": False,
            "landmarks_produced": False,
            "failure_stage": "subprocess_timeout",
            "exception_type": "TimeoutExpired",
            "exception_message": str(exc),
            "subprocess_returncode": None,
            "stderr_tail": "",
        }
    record = parse_record(completed.stdout)
    record["subprocess_returncode"] = completed.returncode
    record["stderr_tail"] = "\n".join(completed.stderr.strip().splitlines()[-8:])
    return record


def subprocess_code(config):
    payload = json.dumps(config)
    return textwrap.dedent(
        f"""
        import json
        import os
        import platform
        import sys
        import traceback

        config = json.loads({payload!r})
        record = {{
            "case": config["name"],
            "description": config["description"],
            "cwd": os.getcwd(),
            "python_executable": sys.executable,
            "python_version": sys.version.split()[0],
            "platform_machine": platform.machine(),
            "mediapipe_version": None,
            "cv2_version": None,
            "mp_solutions_exists": None,
            "mediapipe_disable_gpu": None,
            "hands_constructed": False,
            "process_succeeded": None,
            "landmarks_produced": None,
            "failure_stage": None,
            "exception_type": None,
            "exception_message": None,
        }}

        try:
            if config["set_env"]:
                os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"
            record["mediapipe_disable_gpu"] = os.environ.get("MEDIAPIPE_DISABLE_GPU")

            if config["repo_root"] not in sys.path:
                sys.path.insert(0, config["repo_root"])

            if config["import_project_first"]:
                record["failure_stage"] = "project_import"
                import pose_feedback.hand.mediapipe_hand_runner  # noqa: F401

            record["failure_stage"] = "imports"
            if config["import_order"] == "mediapipe_then_cv2":
                import mediapipe as mp
                import cv2
            else:
                import cv2
                import mediapipe as mp

            record["mediapipe_version"] = getattr(mp, "__version__", None)
            record["cv2_version"] = getattr(cv2, "__version__", None)
            record["mp_solutions_exists"] = hasattr(mp, "solutions")

            image = None
            rgb = None
            crop_box = None
            if config["load_image"]:
                record["failure_stage"] = "image_load"
                image = cv2.imread(config["image_path"])
                if image is None:
                    raise RuntimeError("image load failed")
                rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                crop_box = (0, 0, image.shape[1], image.shape[0])

            if config["use_runner"]:
                record["failure_stage"] = "runner_import"
                from pose_feedback.hand.mediapipe_hand_runner import MediaPipeHandsRunner
                record["failure_stage"] = "runner_construction"
                runner = MediaPipeHandsRunner(
                    static_image_mode=True,
                    max_num_hands=1,
                    min_detection_confidence=0.3,
                    min_tracking_confidence=0.3,
                    cpu_only=True,
                    input_color_format="BGR",
                )
                record["hands_constructed"] = True
                if config["process"]:
                    record["failure_stage"] = "run_crop_process"
                    results = runner.run_crop(image, crop_box)
                    record["process_succeeded"] = True
                    record["landmarks_produced"] = bool(results)
                runner.close()
            else:
                record["failure_stage"] = "hands_construction"
                hands = mp.solutions.hands.Hands(
                    static_image_mode=True,
                    max_num_hands=1,
                    min_detection_confidence=0.3,
                )
                record["hands_constructed"] = True
                if config["process"]:
                    record["failure_stage"] = "hands_process"
                    result = hands.process(rgb)
                    record["process_succeeded"] = True
                    record["landmarks_produced"] = bool(
                        getattr(result, "multi_hand_landmarks", None)
                    )
                hands.close()
            record["failure_stage"] = None
        except Exception as exc:
            record["exception_type"] = type(exc).__name__
            record["exception_message"] = str(exc)
            if config["process"] and record["process_succeeded"] is None:
                record["process_succeeded"] = False
            if config["process"] and record["landmarks_produced"] is None:
                record["landmarks_produced"] = False

        print("JSON_RESULT:" + json.dumps(record, ensure_ascii=False))
        """
    )


def parse_record(stdout):
    for line in reversed(stdout.splitlines()):
        if line.startswith("JSON_RESULT:"):
            return json.loads(line[len("JSON_RESULT:") :])
    return {
        "case": "unknown",
        "description": "failed to parse subprocess output",
        "cwd": None,
        "python_executable": None,
        "python_version": None,
        "platform_machine": None,
        "mediapipe_version": None,
        "cv2_version": None,
        "mp_solutions_exists": None,
        "mediapipe_disable_gpu": None,
        "hands_constructed": False,
        "process_succeeded": False,
        "landmarks_produced": False,
        "failure_stage": "subprocess_output_parse",
        "exception_type": None,
        "exception_message": stdout.strip(),
    }


def print_case(result):
    print(
        json.dumps(
            {
                "case": result["case"],
                "description": result["description"],
                "cwd": result["cwd"],
                "python_executable": result["python_executable"],
                "python_version": result["python_version"],
                "platform_machine": result["platform_machine"],
                "mediapipe_version": result["mediapipe_version"],
                "cv2_version": result["cv2_version"],
                "mp_solutions_exists": result["mp_solutions_exists"],
                "mediapipe_disable_gpu": result["mediapipe_disable_gpu"],
                "hands_constructed": result["hands_constructed"],
                "process_succeeded": result["process_succeeded"],
                "landmarks_produced": result["landmarks_produced"],
                "failure_stage": result["failure_stage"],
                "exception_type": result["exception_type"],
                "exception_message": result["exception_message"],
                "subprocess_returncode": result["subprocess_returncode"],
            },
            ensure_ascii=False,
        )
    )


def print_summary(results):
    print("Summary:")
    for result in results:
        status = "success" if result["hands_constructed"] else "failure"
        stage = result["failure_stage"] or "none"
        print(f"- {result['case']}: {status}, stage={stage}")


if __name__ == "__main__":
    raise SystemExit(main())
