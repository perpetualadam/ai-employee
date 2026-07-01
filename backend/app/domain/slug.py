"""Public URL slug rules for customer-facing chat."""

import re

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MAX_SLUG_LEN = 64


def slugify_business_name(name: str) -> str:
    """Convert a business name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        slug = "business"
    return slug[:_MAX_SLUG_LEN]


def is_valid_public_slug(slug: str) -> bool:
    return bool(slug) and len(slug) <= _MAX_SLUG_LEN and _SLUG_RE.match(slug) is not None
