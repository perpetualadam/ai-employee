"""Specification: gather retry logic for noisy or incomplete speech."""

import unittest
from unittest.mock import MagicMock

from app.models.enums import Industry

from app.domain.intake import normalize_caller_speech
from app.domain.trades.registry import resolve_trade_context
from app.voice.gather_prompts import empty_gather_prompt, is_truncated_speech, is_unreliable_speech
from app.voice.stt.gather_stt import GatherSpeechSTT
from tests.helpers import sample_business


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

    def test_empty_gather_first_turn_is_trade_specific(self) -> None:
        call_log = MagicMock(conversation_history=[])
        trade = resolve_trade_context(sample_business(industry=Industry.PLASTERER))
        prompt = empty_gather_prompt(call_log, trade)
        self.assertIn("replastering", prompt.lower())


if __name__ == "__main__":
    unittest.main()
