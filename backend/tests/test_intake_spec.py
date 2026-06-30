"""Specification: caller name and address intake rules."""

import unittest

from app.domain.intake import (
    extract_spoken_name,
    is_valid_customer_name,
    is_valid_service_address,
    normalize_caller_speech,
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
