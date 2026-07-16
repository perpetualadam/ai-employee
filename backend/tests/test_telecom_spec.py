"""Specification: country telecom profiles and phone normalization."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, call, patch

from app.domain.phone import is_plausible_phone, normalize_phone
from app.domain.telecom import (
    EU_MEMBER_CODES,
    get_address_format_hint,
    get_country_defaults,
    get_dial_code,
    get_example_phone_number,
    get_number_search_profile,
    get_telecom_profile,
    resolve_region_code,
    resolve_voice_locale,
)


class TelecomProfileSpecification(unittest.TestCase):
    def test_supported_regions_resolve(self) -> None:
        for country in ("US", "AU", "GB", "NZ", "DE", "FR"):
            profile = get_telecom_profile(country)
            self.assertIsNotNone(profile.recommended_sms_providers)

    def test_eu_members_share_eu_profile(self) -> None:
        self.assertEqual(resolve_region_code("DE"), "EU")
        self.assertEqual(get_telecom_profile("DE").region_code, "EU")

    def test_country_dial_codes(self) -> None:
        self.assertEqual(get_dial_code("GB"), "44")
        self.assertEqual(get_dial_code("AU"), "61")
        self.assertEqual(get_dial_code("DE"), "49")

    def test_address_hints_vary_by_country(self) -> None:
        us_hint = get_address_format_hint("US")
        gb_hint = get_address_format_hint("GB")
        self.assertNotEqual(us_hint, gb_hint)
        self.assertIn("postcode", gb_hint.lower())

    def test_canada_has_dedicated_telecom_profile(self) -> None:
        self.assertEqual(resolve_region_code("CA"), "CA")
        self.assertEqual(get_telecom_profile("CA").region_code, "CA")

    def test_country_defaults_for_uk(self) -> None:
        defaults = get_country_defaults("GB")
        self.assertEqual(defaults.timezone, "Europe/London")
        self.assertEqual(defaults.currency, "GBP")

    def test_voice_locale_for_uk(self) -> None:
        locale = resolve_voice_locale("GB")
        self.assertEqual(locale.language, "en-GB")
        self.assertEqual(locale.voice, "Polly.Amy")

    def test_example_phone_for_uk(self) -> None:
        self.assertTrue(get_example_phone_number("GB").startswith("+44"))


class CountryPhoneNormalizationSpecification(unittest.TestCase):
    def test_us_ten_digit_local(self) -> None:
        self.assertEqual(normalize_phone("6145551234", "US"), "+16145551234")

    def test_us_does_not_strip_leading_digit(self) -> None:
        """NANP has no trunk 0 — 10-digit numbers must not be altered."""
        self.assertEqual(normalize_phone("6145551234", "US"), "+16145551234")

    # --- trunk-0 stripping (E.164 requires dropping the trunk prefix) ---

    def test_uk_mobile_trunk_zero_stripped(self) -> None:
        """07949046947 -> +447949046947 (trunk 0 dropped, not +4407949046947)."""
        self.assertEqual(normalize_phone("07949046947", "GB"), "+447949046947")

    def test_uk_e164_passthrough(self) -> None:
        """Already-E164 UK number is returned unchanged."""
        self.assertEqual(normalize_phone("+447949046947", "GB"), "+447949046947")

    def test_australian_mobile_trunk_zero_stripped(self) -> None:
        """0412345678 -> +61412345678 (not +610412345678)."""
        self.assertEqual(normalize_phone("0412345678", "AU"), "+61412345678")

    def test_german_landline_trunk_zero_stripped(self) -> None:
        """030 12345678 (Berlin) -> +493012345678 (not +4903012345678)."""
        self.assertEqual(normalize_phone("0301234567", "DE"), "+49301234567")

    def test_nz_trunk_zero_stripped(self) -> None:
        """091234567 (NZ) -> +6491234567 (not +64091234567)."""
        self.assertEqual(normalize_phone("091234567", "NZ"), "+6491234567")

    def test_ie_trunk_zero_stripped(self) -> None:
        """012345678 (Dublin) -> +35312345678 (not +353012345678)."""
        self.assertEqual(normalize_phone("012345678", "IE"), "+35312345678")

    def test_plausible_uk_number(self) -> None:
        self.assertTrue(is_plausible_phone("+447949046947", "GB"))


class NumberSearchProfileSpecification(unittest.TestCase):
    """get_number_search_profile returns country-correct Telnyx filter params."""

    def test_us_uses_ndc_filter_and_3_digit_area_code(self) -> None:
        p = get_number_search_profile("US")
        self.assertEqual(p.prefix_param, "filter[national_destination_code]")
        self.assertIn(3, p.prefix_digits)
        self.assertNotEqual(p.prefix_example, "")

    def test_uk_uses_locality_filter_not_ndc(self) -> None:
        """GB numbers are searched by city/area, not a numeric NDC."""
        p = get_number_search_profile("GB")
        self.assertEqual(p.prefix_param, "filter[locality]")
        self.assertEqual(p.prefix_digits, ())  # free text, no digit constraint
        self.assertIn("London", p.prefix_example)

    def test_australia_uses_ndc_with_2_digit_std(self) -> None:
        p = get_number_search_profile("AU")
        self.assertEqual(p.prefix_param, "filter[national_destination_code]")
        self.assertIn(2, p.prefix_digits)

    def test_nz_has_no_prefix_param(self) -> None:
        """NZ is not filterable via Telnyx prefix; prefix_param must be None."""
        p = get_number_search_profile("NZ")
        self.assertIsNone(p.prefix_param)

    def test_eu_member_without_dedicated_profile_falls_back_to_eu(self) -> None:
        """An EU country not listed individually (e.g. PL) gets the EU profile."""
        self.assertIn("PL", EU_MEMBER_CODES)
        p = get_number_search_profile("PL")
        self.assertIsNotNone(p.prefix_param)  # EU profile has NDC param

    def test_de_has_dedicated_profile_not_eu_fallback(self) -> None:
        """DE has its own profile with a correct Vorwahl label."""
        p = get_number_search_profile("DE")
        self.assertIn("Vorwahl", p.prefix_label)

    def test_unknown_country_falls_back_to_us_profile(self) -> None:
        p = get_number_search_profile("ZZ")  # not real
        self.assertEqual(p.prefix_param, "filter[national_destination_code]")

    def test_all_profiles_have_label(self) -> None:
        for country in ("US", "CA", "GB", "AU", "NZ", "DE", "FR", "IE"):
            p = get_number_search_profile(country)
            self.assertTrue(p.prefix_label, f"{country} profile missing prefix_label")


class TelnyxClientNumberSearchSpecification(unittest.TestCase):
    """telnyx_client.search_available_phone_numbers sends country-correct filter params."""

    def _make_telnyx_response(self, phone: str) -> dict:
        return {
            "data": [
                {
                    "phone_number": phone,
                    "region_information": [{"region_name": "Test Region"}],
                    "cost_information": {"monthly_cost": "1.00"},
                }
            ]
        }

    @patch("app.voice.telnyx_client._request")
    def test_uk_search_sends_locality_filter_not_ndc(self, mock_req: MagicMock) -> None:
        """For GB a prefix must go through filter[locality], NOT filter[national_destination_code]."""
        mock_req.return_value = self._make_telnyx_response("+447911123456")

        from app.voice import telnyx_client
        results = telnyx_client.search_available_phone_numbers("GB", prefix="London")

        self.assertEqual(len(results), 1)
        _, kwargs = mock_req.call_args
        params = kwargs.get("params", {})
        self.assertIn("filter[locality]", params)
        self.assertEqual(params["filter[locality]"], "London")
        self.assertNotIn("filter[national_destination_code]", params)

    @patch("app.voice.telnyx_client._request")
    def test_us_search_sends_ndc_filter(self, mock_req: MagicMock) -> None:
        mock_req.return_value = self._make_telnyx_response("+16145551234")

        from app.voice import telnyx_client
        results = telnyx_client.search_available_phone_numbers("US", prefix="614")

        self.assertEqual(len(results), 1)
        _, kwargs = mock_req.call_args
        params = kwargs.get("params", {})
        self.assertIn("filter[national_destination_code]", params)
        self.assertEqual(params["filter[national_destination_code]"], "614")

    @patch("app.voice.telnyx_client._request")
    def test_au_search_sends_ndc_filter(self, mock_req: MagicMock) -> None:
        mock_req.return_value = self._make_telnyx_response("+61212345678")

        from app.voice import telnyx_client
        telnyx_client.search_available_phone_numbers("AU", prefix="02")

        _, kwargs = mock_req.call_args
        params = kwargs.get("params", {})
        self.assertIn("filter[national_destination_code]", params)
        self.assertEqual(params["filter[national_destination_code]"], "02")

    @patch("app.voice.telnyx_client._request")
    def test_nz_search_ignores_prefix_silently(self, mock_req: MagicMock) -> None:
        """NZ has no Telnyx prefix filter; prefix param must not appear in the request."""
        mock_req.return_value = self._make_telnyx_response("+6491234567")

        from app.voice import telnyx_client
        telnyx_client.search_available_phone_numbers("NZ", prefix="09")

        _, kwargs = mock_req.call_args
        params = kwargs.get("params", {})
        self.assertNotIn("filter[national_destination_code]", params)
        self.assertNotIn("filter[locality]", params)

    @patch("app.voice.telnyx_client._request")
    def test_country_code_always_sent_correctly(self, mock_req: MagicMock) -> None:
        """filter[country_code] must always match the business country."""
        mock_req.return_value = self._make_telnyx_response("+447911000000")

        from app.voice import telnyx_client
        telnyx_client.search_available_phone_numbers("GB")

        _, kwargs = mock_req.call_args
        params = kwargs.get("params", {})
        self.assertEqual(params.get("filter[country_code]"), "GB")

    @patch("app.voice.telnyx_client._request")
    def test_no_prefix_does_not_add_any_filter_key(self, mock_req: MagicMock) -> None:
        """Calling without a prefix must not inject any prefix filter key."""
        mock_req.return_value = self._make_telnyx_response("+16145551234")

        from app.voice import telnyx_client
        telnyx_client.search_available_phone_numbers("US")

        _, kwargs = mock_req.call_args
        params = kwargs.get("params", {})
        self.assertNotIn("filter[national_destination_code]", params)
        self.assertNotIn("filter[locality]", params)


class SupportedCountriesSpecification(unittest.TestCase):
    """get_supported_countries must not leak internal region tokens."""

    def test_eu_pseudo_code_not_in_supported_countries(self) -> None:
        """'EU' is an internal region key, not a real country — must never appear."""
        from app.domain.telecom import get_supported_countries
        codes = {c["code"] for c in get_supported_countries()}
        self.assertNotIn("EU", codes)

    def test_all_returned_codes_are_two_letter_iso(self) -> None:
        from app.domain.telecom import get_supported_countries
        for entry in get_supported_countries():
            self.assertEqual(len(entry["code"]), 2, f"Non-ISO code: {entry['code']}")


class PhoneProvisioningStatusSpecification(unittest.TestCase):
    """PhoneProvisioningService.status returns correct can_search logic."""

    @patch("app.services.phone_provisioning_service.telnyx_client.is_phone_provisioning_configured", return_value=True)
    def test_can_search_false_when_already_provisioned(self, _cfg) -> None:
        """A provisioned business cannot provision again; can_search must be False."""
        from app.services.phone_provisioning_service import PhoneProvisioningService
        business = MagicMock()
        business.phone_provisioned = True
        business.phone_number = "+447911123456"
        business.country = "GB"
        status = PhoneProvisioningService.status(business)
        self.assertFalse(status["can_search"])
        self.assertFalse(status["manual_fallback_allowed"])

    @patch("app.services.phone_provisioning_service.telnyx_client.is_phone_provisioning_configured", return_value=True)
    def test_can_search_true_when_configured_and_not_provisioned(self, _cfg) -> None:
        from app.services.phone_provisioning_service import PhoneProvisioningService
        business = MagicMock()
        business.phone_provisioned = False
        business.phone_number = None
        business.country = "US"
        status = PhoneProvisioningService.status(business)
        self.assertTrue(status["can_search"])
        self.assertTrue(status["manual_fallback_allowed"])

    @patch("app.services.phone_provisioning_service.telnyx_client.is_phone_provisioning_configured", return_value=False)
    def test_can_search_false_when_platform_not_configured(self, _cfg) -> None:
        from app.services.phone_provisioning_service import PhoneProvisioningService
        business = MagicMock()
        business.phone_provisioned = False
        business.phone_number = None
        business.country = "US"
        status = PhoneProvisioningService.status(business)
        self.assertFalse(status["can_search"])


class PhoneProvisioningServiceSearchSpecification(unittest.TestCase):
    """PhoneProvisioningService.search_available passes prefix to telnyx_client correctly."""

    @patch("app.services.phone_provisioning_service.telnyx_client.is_phone_provisioning_configured", return_value=True)
    @patch("app.services.phone_provisioning_service.telnyx_client.search_available_phone_numbers")
    def test_gb_business_search_passes_prefix_not_area_code(self, mock_search, _cfg) -> None:
        from app.services.phone_provisioning_service import PhoneProvisioningService

        business = MagicMock()
        business.country = "GB"
        mock_search.return_value = [{"phone_number": "+447911123456", "region": None, "cost": None}]

        PhoneProvisioningService.search_available(business, prefix="London")

        mock_search.assert_called_once_with("GB", prefix="London", limit=10)

    @patch("app.services.phone_provisioning_service.telnyx_client.is_phone_provisioning_configured", return_value=True)
    @patch("app.services.phone_provisioning_service.telnyx_client.search_available_phone_numbers")
    def test_us_business_search_passes_prefix(self, mock_search, _cfg) -> None:
        from app.services.phone_provisioning_service import PhoneProvisioningService

        business = MagicMock()
        business.country = "US"
        mock_search.return_value = []

        PhoneProvisioningService.search_available(business, prefix="614")

        mock_search.assert_called_once_with("US", prefix="614", limit=10)


if __name__ == "__main__":
    unittest.main()
