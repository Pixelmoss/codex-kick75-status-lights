# SPDX-License-Identifier: MIT
import pathlib
import sys
import tempfile
import unittest


SRC = pathlib.Path(__file__).parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import codex_kick75_common


class CommonTests(unittest.TestCase):
    def test_normalization_drops_prompt_and_tool_payload(self):
        event = {
            "hook_event_name": "PostToolUse",
            "session_id": "session-a",
            "turn_id": "turn-a",
            "prompt": "private prompt",
            "tool_input": {"secret": "private input"},
            "tool_response": {"exit_code": 7, "output": "private output"},
        }
        normalized = codex_kick75_common.normalize_hook_event(event)
        self.assertEqual(
            normalized,
            {
                "hook_event_name": "PostToolUse",
                "session_id": "session-a",
                "turn_id": "turn-a",
                "tool_failed": True,
            },
        )

    def test_successful_nested_response_is_not_failure(self):
        self.assertFalse(
            codex_kick75_common.response_failed(
                {"content": [{"result": {"exit_code": 0, "ok": True}}]}
            )
        )

    def test_settings_are_normalized_and_encoded_as_side_state(self):
        settings = codex_kick75_common.default_settings()
        settings["states"]["running"] = {"color": "#123abc", "brightness": 42}
        normalized = codex_kick75_common.validate_settings(settings)
        self.assertEqual(normalized["states"]["running"]["color"], "#123ABC")
        self.assertEqual(
            codex_kick75_common.side_state_for(normalized, "running"),
            "022a010000123abc",
        )

    def test_settings_reject_invalid_color_and_brightness(self):
        settings = codex_kick75_common.default_settings()
        settings["states"]["running"]["color"] = "red"
        with self.assertRaises(ValueError):
            codex_kick75_common.validate_settings(settings)
        settings = codex_kick75_common.default_settings()
        settings["states"]["running"]["brightness"] = 101
        with self.assertRaises(ValueError):
            codex_kick75_common.validate_settings(settings)

    def test_settings_round_trip_uses_private_file_permissions(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "settings.json"
            codex_kick75_common.save_settings(codex_kick75_common.default_settings(), path)
            loaded = codex_kick75_common.load_settings(path)
            self.assertEqual(loaded, codex_kick75_common.default_settings())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(path.parent.glob(".settings.json-*.tmp")), [])


class NormalizeColorTests(unittest.TestCase):
    def test_normalize_color_accepts_six_digit_hex_and_uppercases(self):
        cases = {
            "#000000": "#000000",
            "#ffffff": "#FFFFFF",
            "#aB12cD": "#AB12CD",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(codex_kick75_common.normalize_color(value), expected)

    def test_normalize_color_rejects_invalid_lengths_characters_and_types(self):
        invalid_values = ("#12345", "#1234567", "123456", "#12x456", None, 123456, True)
        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "^color must use #RRGGBB format$"):
                    codex_kick75_common.normalize_color(value)


if __name__ == "__main__":
    unittest.main()
