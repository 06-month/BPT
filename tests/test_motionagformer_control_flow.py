from types import SimpleNamespace
import unittest
from unittest import mock

from scripts import visualize_rtmpose_body_and_both_hands_video as video


class MotionAGFormerControlFlowTests(unittest.TestCase):
    def test_default_is_2d_only(self):
        args = args_for(run_motionagformer=False, draw_3d_panel=False, draw_3d_hands=False)

        self.assertFalse(video.should_run_motionagformer(args))
        self.assertFalse(video.should_draw_3d_panel(args))
        self.assertEqual(video.effective_hand_3d_mode(args), "none")

    def test_run_motionagformer_without_panel_runs_inference_only(self):
        args = args_for(run_motionagformer=True, draw_3d_panel=False, draw_3d_hands=False)

        self.assertTrue(video.should_run_motionagformer(args))
        self.assertFalse(video.should_draw_3d_panel(args))
        self.assertEqual(video.effective_hand_3d_mode(args), "wrist-anchored")

    def test_draw_3d_panel_implies_motionagformer_and_render_panel(self):
        args = args_for(run_motionagformer=False, draw_3d_panel=True, draw_3d_hands=False)

        self.assertTrue(video.should_run_motionagformer(args))
        self.assertTrue(video.should_draw_3d_panel(args))

    def test_legacy_draw_3d_hands_implies_motionagformer_and_panel(self):
        args = args_for(run_motionagformer=False, draw_3d_panel=False, draw_3d_hands=True)

        self.assertTrue(video.should_run_motionagformer(args))
        self.assertTrue(video.should_draw_3d_panel(args))
        self.assertEqual(video.effective_hand_3d_mode(args), "wrist-anchored")

    def test_explicit_hand_3d_none_is_respected(self):
        args = args_for(run_motionagformer=True, hand_3d_mode="none")

        self.assertTrue(video.should_run_motionagformer(args))
        self.assertEqual(video.effective_hand_3d_mode(args), "none")

    def test_assign_motionagformer_3d_skips_when_not_requested(self):
        args = args_for(run_motionagformer=False, draw_3d_panel=False, draw_3d_hands=False)
        with mock.patch.object(video, "assign_live_motionagformer_3d") as live_mock:
            status = video.assign_motionagformer_3d([], {}, args)

        self.assertEqual(status["generation"], "disabled")
        live_mock.assert_not_called()

    def test_assign_motionagformer_3d_runs_when_inference_only_requested(self):
        args = args_for(run_motionagformer=True, motionagformer_3d_source="live")
        expected = {"generation": "live_pytorch", "key_used": "fake", "warning": None}
        with mock.patch.object(video, "assign_live_motionagformer_3d", return_value=expected) as live_mock:
            status = video.assign_motionagformer_3d([{"motionagformer_input_2d": object()}], {}, args)

        self.assertEqual(status, expected)
        live_mock.assert_called_once()


def args_for(**overrides):
    values = {
        "run_motionagformer": False,
        "draw_3d_panel": False,
        "draw_3d_hands": False,
        "hand_3d_mode": None,
        "motionagformer_3d_source": "live",
        "motionagformer_wrist_source": "rtmpose",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


if __name__ == "__main__":
    unittest.main()
