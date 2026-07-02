"""Specification: country telecom profiles and phone normalization."""

from __future__ import annotations

import unittest

from app.domain.phone import is_plausible_phone, normalize_phone
from app.domain.telecom import (
    get_address_format_hint,
    get_dial_code,
    get_telecom_profile,
    resolve_region_code,
)


class TelecomProfileSpecification(unittest.TestCase):
    def test_supported_regions_resolve(self) -> None:
        for country in ("US", "AU", "GB", "NZ", "JP", "CN", "RU", "DE", "FR"):
            profile = get_telecom_profile(country)
            self.assertIsNotNone(profile.recommended_sms_providers)

    def test_eu_members_share_eu_profile(self) -> None:
        self.assertEqual(resolve_region_code("DE"), "EU")
        self.assertEqual(get_telecom_profile("DE").region_code, "EU")

    def test_country_dial_codes(self) -> None:
        self.assertEqual(get_dial_code("GB"), "44")
        self.assertEqual(get_dial_code("AU"), "61")
        self.assertEqual(get_dial_code("JP"), "81")

    def test_address_hints_vary_by_country(self) -> None:
        us_hint = get_address_format_hint("US")
        gb_hint = get_address_format_hint("GB")
        self.assertNotEqual(us_hint, gb_hint)
        self.assertIn("postcode", gb_hint.lower())


class CountryPhoneNormalizationSpecification(unittest.TestCase):
    def test_us_ten_digit_local(self) -> None:
        self.assertEqual(normalize_phone("6145551234", "US"), "+16145551234")

    def test_uk_mobile(self) -> None:
        normalized = normalize_phone("07949046947", "GB")
        self.assertTrue(normalized.startswith("+44"))

    def test_australian_mobile(self) -> None:
        normalized = normalize_phone("0412345678", "AU")
        self.assertTrue(normalized.startswith("+61"))

    def test_plausible_uk_number(self) -> None:
        self.assertTrue(is_plausible_phone("+447949046947", "GB"))


if __name__ == "__main__":
    unittest.main()
