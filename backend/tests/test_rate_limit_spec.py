"""Rate limit storage configuration tests."""

from __future__ import annotations

import unittest

from app.core.rate_limit_storage import rate_limit_storage_uri


class RateLimitStorageSpecification(unittest.TestCase):
    def test_defaults_to_memory_without_redis_url(self) -> None:
        self.assertEqual(rate_limit_storage_uri(""), "memory://")
        self.assertEqual(rate_limit_storage_uri("   "), "memory://")

    def test_uses_redis_when_configured(self) -> None:
        self.assertEqual(
            rate_limit_storage_uri("redis://redis:6379/0"),
            "redis://redis:6379/0",
        )


if __name__ == "__main__":
    unittest.main()
