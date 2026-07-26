"""HttpOnly cookie authentication tests."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from fastapi import Response
from jose import jwt

from app.core.auth_cookies import AUTH_COOKIE_NAME, clear_auth_cookie, set_auth_cookie
from app.core.deps import resolve_access_token
from app.core.security import create_access_token


class AuthCookieSpecification(unittest.TestCase):
    def test_set_auth_cookie_is_httponly(self) -> None:
        response = Response()
        with patch("app.core.auth_cookies.get_settings") as settings_mock:
            settings_mock.return_value.debug = True
            settings_mock.return_value.access_token_expire_minutes = 60
            set_auth_cookie(response, "token-value")

        cookie = response.headers.get("set-cookie", "")
        self.assertIn(AUTH_COOKIE_NAME, cookie)
        self.assertIn("httponly", cookie.lower())

    def test_clear_auth_cookie_expires_session(self) -> None:
        response = Response()
        with patch("app.core.auth_cookies.get_settings") as settings_mock:
            settings_mock.return_value.debug = True
            clear_auth_cookie(response)

        cookie = response.headers.get("set-cookie", "")
        self.assertIn(f"{AUTH_COOKIE_NAME}=", cookie)

    def test_resolve_access_token_prefers_bearer_header(self) -> None:
        request = MagicMock()
        request.cookies = {AUTH_COOKIE_NAME: "cookie-token"}
        credentials = MagicMock()
        credentials.credentials = "bearer-token"

        token = resolve_access_token(request, credentials)
        self.assertEqual(token, "bearer-token")

    def test_resolve_access_token_falls_back_to_cookie(self) -> None:
        request = MagicMock()
        request.cookies = {AUTH_COOKIE_NAME: "cookie-token"}

        token = resolve_access_token(request, None)
        self.assertEqual(token, "cookie-token")

    def test_create_access_token_round_trips(self) -> None:
        with patch("app.core.security.settings") as settings_mock:
            settings_mock.secret_key = "test-secret-key-for-jwt-signing"
            settings_mock.algorithm = "HS256"
            settings_mock.access_token_expire_minutes = 60
            token = create_access_token("user-123")
            payload = jwt.decode(token, settings_mock.secret_key, algorithms=["HS256"])
            self.assertEqual(payload["sub"], "user-123")


if __name__ == "__main__":
    unittest.main()
