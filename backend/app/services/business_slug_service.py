"""Assign and resolve unique public slugs per business."""

from sqlalchemy.orm import Session

from app.domain.slug import is_valid_public_slug, slugify_business_name
from app.models import Business


class BusinessSlugService:
    @staticmethod
    def ensure_unique_slug(db: Session, business: Business, *, base: str | None = None) -> str:
        """Set business.public_slug to a unique value if missing or regenerate from base."""
        seed = slugify_business_name(base or business.name)
        candidate = seed
        suffix = 2
        while BusinessSlugService._slug_taken(db, candidate, exclude_id=business.id):
            candidate = f"{seed}-{suffix}"[:64]
            suffix += 1
        business.public_slug = candidate
        db.commit()
        db.refresh(business)
        return candidate

    @staticmethod
    def resolve_by_slug(db: Session, slug: str) -> Business | None:
        if not is_valid_public_slug(slug):
            return None
        return db.query(Business).filter(Business.public_slug == slug).first()

    @staticmethod
    def _slug_taken(db: Session, slug: str, *, exclude_id: str | None = None) -> bool:
        query = db.query(Business).filter(Business.public_slug == slug)
        if exclude_id:
            query = query.filter(Business.id != exclude_id)
        return query.first() is not None
