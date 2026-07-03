"""Specification: caller name and address intake rules."""

import unittest

from app.models.enums import Industry
from app.domain.intake import (
    address_appears_in_caller_text,
    extract_spoken_name,
    is_valid_customer_name,
    is_valid_service_address,
    normalize_caller_speech,
    service_address_validation_message,
    validate_us_service_address,
)


class IntakeSpecification(unittest.TestCase):
    """How intake validation must behave on phone calls."""

    def test_accepts_real_customer_name(self) -> None:
        self.assertTrue(is_valid_customer_name("Brian Smith"))

    def test_rejects_placeholder_names(self) -> None:
        for bad in ("Caller", "customer", "Unknown", "test", "Guest"):
            with self.subTest(name=bad):
                self.assertFalse(is_valid_customer_name(bad))

    def test_accepts_full_street_address(self) -> None:
        self.assertTrue(is_valid_service_address("123 Main Street, Columbus, OH 43215"))

    def test_rejects_city_or_state_only(self) -> None:
        for bad in ("Michigan", "Columbus, Ohio", "OH", "near downtown"):
            with self.subTest(address=bad):
                self.assertFalse(is_valid_service_address(bad))

    def test_rejects_placeholder_addresses(self) -> None:
        self.assertFalse(is_valid_service_address("unknown"))
        self.assertFalse(is_valid_service_address("n/a"))

    def test_rejects_fragmentary_or_guessed_addresses(self) -> None:
        for bad in (
            "123",
            "close. Florida",
            "123 close Florida",
            "123 Main St",
            "101 flamingo way florida",
            "123 Boulevard closed Orlando Florida",
            "Michigan",
        ):
            with self.subTest(address=bad):
                self.assertFalse(is_valid_service_address(bad))

    def test_accepts_full_us_addresses(self) -> None:
        for good in (
            "123 Main Street, Columbus, OH 43215",
            "101 Flamingo Way, Hollywood, FL 33020",
            "123 Boulevard, Orlando, FL 32801",
            "456 Oak Avenue, Apt 2, Detroit, MI 48201",
            "101 flamingo way hollywood florida 33020",
        ):
            with self.subTest(address=good):
                self.assertTrue(is_valid_service_address(good))

    def test_validation_message_lists_missing_parts(self) -> None:
        message = service_address_validation_message("123 Main Street, Orlando, FL")
        self.assertIn("ZIP", message)

    def test_validate_us_service_address_parts(self) -> None:
        ok, missing = validate_us_service_address("123 Main St, Columbus, OH 43215")
        self.assertTrue(ok)
        self.assertEqual(missing, [])
        ok, missing = validate_us_service_address("123 Main St, Columbus, OH")
        self.assertFalse(ok)
        self.assertIn("5-digit ZIP code", missing)

    def test_rejects_garbled_stt_names(self) -> None:
        for bad in ("having a week", "having a water leak", "water leak"):
            with self.subTest(name=bad):
                self.assertFalse(is_valid_customer_name(bad))

    def test_rejects_trade_specific_garbled_names(self) -> None:
        self.assertFalse(
            is_valid_customer_name("boiler breakdown", industry=Industry.GAS_ENGINEER)
        )

    def test_normalizes_leak_week_stt_confusion(self) -> None:
        self.assertEqual(normalize_caller_speech("My name is having a week"), "I have a leak")
        self.assertEqual(normalize_caller_speech("I'm having a week"), "I have a leak")
        self.assertEqual(
            normalize_caller_speech("My name is having a water leak"),
            "I have a water leak",
        )

    def test_address_must_match_caller_words(self) -> None:
        caller = ["123", "close. Florida"]
        self.assertFalse(
            address_appears_in_caller_text(
                "456 Oak Avenue Springfield Illinois",
                caller,
            )
        )
        self.assertTrue(
            address_appears_in_caller_text(
                "123 Boulevard closed Orlando Florida",
                ["123 Boulevard closed Orlando Florida"],
            )
        )

    def test_normalizes_spoken_name_from_stt(self) -> None:
        self.assertEqual(
            normalize_caller_speech("yeah my name is Brian Smith"),
            "My name is Brian Smith",
        )
        self.assertEqual(extract_spoken_name("I'm Brian Smith"), "Brian Smith")

    def test_intake_requires_both_name_and_address_before_booking(self) -> None:
        """Documented contract: neither field alone is enough."""
        self.assertTrue(is_valid_customer_name("Brian Smith"))
        self.assertFalse(is_valid_service_address("Michigan"))
        self.assertFalse(
            is_valid_customer_name("Caller") and is_valid_service_address("123 Main St")
        )


if __name__ == "__main__":
    unittest.main()
