"""Specification: public customer web chat and voice handoff."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.domain.slug import is_valid_public_slug, slugify_business_name
from app.services.business_slug_service import BusinessSlugService


class PublicSlugSpecification(unittest.TestCase):
    def test_slugify_business_name(self) -> None:
        self.assertEqual(slugify_business_name("Joe Blob's Plumbing"), "joe-blob-s-plumbing")
        self.assertTrue(is_valid_public_slug("joes-plumbing"))

    def test_ensure_unique_slug_avoids_collision(self) -> None:
        db = MagicMock()
        business = MagicMock()
        business.id = "biz-1"
        business.name = "Joe Plumbing"
        business.public_slug = None

        with patch.object(
            BusinessSlugService,
            "_slug_taken",
            side_effect=[True, False],
        ) as taken_mock:
            slug = BusinessSlugService.ensure_unique_slug(db, business, base="Joe Plumbing")

        self.assertEqual(slug, "joe-plumbing-2")
        taken_mock.assert_any_call(db, "joe-plumbing", exclude_id="biz-1")
        taken_mock.assert_any_call(db, "joe-plumbing-2", exclude_id="biz-1")
