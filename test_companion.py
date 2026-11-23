import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.request import urlopen

import avatar_ui
import consciousness
import memory
import perception
from soul import hina_soul


class CompanionMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = memory.DB_PATH
        memory.DB_PATH = str(Path(self.temp_dir.name) / "memory.db")

    def tearDown(self):
        memory.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def test_transcript_is_persisted_and_searchable(self):
        memory.save_message("user", "My favorite place is Kyoto.")
        memory.save_message("assistant", "What do you love about Kyoto?")
        memory.save_message("user", "The quiet gardens in spring.")

        self.assertEqual(
            memory.get_recent_messages(limit=2),
            [
                {"role": "assistant", "content": "What do you love about Kyoto?"},
                {"role": "user", "content": "The quiet gardens in spring."},
            ],
        )
        self.assertEqual(
            memory.search_messages("favorite place", limit=1),
            [{"role": "user", "content": "My favorite place is Kyoto."}],
        )
        self.assertFalse(memory.is_first_meeting())

    def test_avatar_expression_tracks_conversational_cues(self):
        self.assertEqual(hina_soul.get_avatar_emotion("I feel lonely"), "sad")
        self.assertEqual(hina_soul.get_avatar_emotion("That is amazing"), "happy")
        self.assertEqual(hina_soul.get_avatar_emotion("Let's take a breath"), "relaxed")
        self.assertEqual(hina_soul.get_avatar_emotion("That was unexpected"), "surprised")
        self.assertEqual(hina_soul.get_avatar_emotion("I feel furious"), "angry")
        self.assertEqual(hina_soul.get_avatar_emotion("Tell me a story"), "neutral")
        self.assertEqual(
            hina_soul.get_avatar_emotion("How was your day?", "I'm happy to see you."),
            "happy"
        )

    def test_brain_persists_user_turns_without_recording_private_greeting_prompts(self):
        previous_brain = sys.modules.pop("brain", None)
        try:
            import brain

            model_response = Mock()
            model_response.json.side_effect = [
                {"message": {"content": "That sounds wonderful."}},
                {"message": {"content": "It's good to see you again."}},
            ]
            with (
                patch.object(brain.hina_soul, "update_after_interaction"),
                patch.object(
                    brain.hina_soul,
                    "get_avatar_emotion",
                    side_effect=["relaxed", "happy"]
                ),
                patch.object(brain, "set_emotion") as update_avatar_emotion,
                patch.object(brain, "build_prompt", return_value="system prompt"),
                patch.object(brain.requests, "post", return_value=model_response),
            ):
                brain.conversation_history = []
                brain.session_messages = []
                brain.think("I like tea.")
                brain.think("Introduce yourself warmly.", record_user=False)

            update_avatar_emotion.assert_any_call("happy")
            self.assertEqual(
                memory.get_recent_messages(limit=3),
                [
                    {"role": "user", "content": "I like tea."},
                    {"role": "assistant", "content": "That sounds wonderful."},
                    {"role": "assistant", "content": "It's good to see you again."},
                ],
            )
        finally:
            if previous_brain is None:
                sys.modules.pop("brain", None)
            else:
                sys.modules["brain"] = previous_brain

    def test_voice_amplitude_is_sampled_for_avatar_lip_sync(self):
        stub = types.ModuleType("kokoro_onnx")
        stub.Kokoro = lambda *_args, **_kwargs: object()
        previous_voice = sys.modules.pop("voice", None)
        try:
            with patch.dict(sys.modules, {"kokoro_onnx": stub}):
                import voice
                import numpy as np

                samples = np.concatenate((
                    np.full(480, 0.1),
                    np.zeros(480),
                    np.full(480, 0.2),
                ))
                levels = voice._voice_envelope(samples, rate=16000)

            self.assertEqual(len(levels), 3)
            self.assertGreater(levels[0], levels[1])
            self.assertGreater(levels[2], levels[0])
        finally:
            if previous_voice is None:
                sys.modules.pop("voice", None)
            else:
                sys.modules["voice"] = previous_voice


class AvatarStateTests(unittest.TestCase):
    def tearDown(self):
        avatar_ui.set_speaking(speaking=False)
        avatar_ui.set_status("Starting")
        avatar_ui.set_emotion("neutral")
        avatar_ui.set_dialogue("", "")
        avatar_ui.stop_avatar_ui()

    @patch("avatar_ui.webbrowser.open", return_value=True)
    def test_local_api_exposes_live_companion_state(self, _open_browser):
        url = avatar_ui.start_avatar_ui()
        for path in (
            "",
            "mesh-avatar.js",
            "avatar/rig.json",
            "avatar/avatar.json",
            "avatar/built/layers.json",
            "avatar/built/base.png",
        ):
            with urlopen(url + path, timeout=2) as response:
                self.assertEqual(response.status, 200, path)

        avatar_ui.set_dialogue("Hina", "I remember.")
        avatar_ui.set_status("Thinking")
        avatar_ui.set_emotion("happy")
        avatar_ui.set_speaking(0.6, voice_envelope=[0.1, 0.8])

        with urlopen(url + "api/state", timeout=2) as response:
            state = json.load(response)

        self.assertEqual(state["speaker"], "Hina")
        self.assertEqual(state["text"], "I remember.")
        self.assertEqual(state["status"], "Speaking")
        self.assertEqual(state["emotion"], "happy")
        self.assertEqual(state["voice_envelope"], [0.1, 0.8])
        self.assertTrue(state["speaking"])

        avatar_ui.set_speaking(speaking=False)
        with urlopen(url + "api/state", timeout=2) as response:
            stopped_state = json.load(response)
        self.assertFalse(stopped_state["speaking"])
        self.assertEqual(stopped_state["status"], "Ready")
        self.assertEqual(stopped_state["voice_envelope"], [])


class ConsciousnessLifecycleTests(unittest.TestCase):
    def test_background_thought_loop_is_idempotent_and_stoppable(self):
        thread = consciousness.start_consciousness_loop()
        try:
            self.assertIs(consciousness.start_consciousness_loop(), thread)
        finally:
            consciousness.stop_consciousness_loop()
        self.assertFalse(thread.is_alive())


class PerceptionTests(unittest.TestCase):
    @patch("perception.cv2.VideoCapture")
    def test_unavailable_camera_is_reported_instead_of_claiming_vision(self, video_capture):
        video_capture.return_value.isOpened.return_value = False
        vision = perception.HinaPerception()

        with self.assertRaisesRegex(RuntimeError, "Camera device 0"):
            vision.start()

        video_capture.return_value.release.assert_called_once()
        self.assertFalse(vision.is_running)


if __name__ == "__main__":
    unittest.main()
