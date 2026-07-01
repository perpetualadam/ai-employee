"""Specification: gather retry logic for noisy or incomplete speech."""

import unittest
from unittest.mock import MagicMock

from app.domain.intake import normalize_caller_speech
from app.voice.gather_prompts import is_truncated_speech, is_unreliable_speech
from app.voice.stt.gather_stt import GatherSpeechSTT


class GatherPromptSpecification(unittest.TestCase):
    def test_treats_punctuation_only_as_empty(self) -> None:
        self.assertTrue(GatherSpeechSTT.is_empty("."))
        self.assertFalse(GatherSpeechSTT.is_empty(". . . no"))

    def test_normalizes_im_having_a_week(self) -> None:
        self.assertEqual(normalize_caller_speech("I'm having a week"), "I have a leak")

    def test_rejects_truncated_problem_phrases(self) -> None:
        self.assertTrue(is_truncated_speech("I have a", 0.98))
        self.assertTrue(is_truncated_speech("I can't", 0.30))

    def test_rejects_low_confidence_noise(self) -> None:
        call_log = MagicMock(conversation_history=[])
        self.assertTrue(is_unreliable_speech("call me", 0.26, call_log))
        self.assertTrue(is_unreliable_speech("am", 0.12, call_log))

    def test_accepts_full_name_with_reasonable_confidence(self) -> None:
        call_log = MagicMock(
            conversation_history=[
                {"role": "assistant", "content": "Can you tell me your full name?"}
            ]
        )
        self.assertFalse(
            is_unreliable_speech("my name is Brian May", 0.75, call_log)
        )


if __name__ == "__main__":
    unittest.main()
