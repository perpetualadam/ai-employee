"""Specification: public customer web chat and voice handoff."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

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

        taken = MagicMock()
        taken.public_slug = "joe-plumbing"
        db.query.return_value.filter.return_value.first.side_effect = [taken, None]

        slug = BusinessSlugService.ensure_unique_slug(db, business, base="Joe Plumbing")
        self.assertEqual(slug, "joe-plumbing-2")
