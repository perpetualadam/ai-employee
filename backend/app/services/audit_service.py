"""Audit logging for compliance-sensitive actions."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    @staticmethod
    def log_event(
        db: Session,
        *,
        action: str,
        resource: str,
        user_id: str | None = None,
        business_id: str | None = None,
        ip_address: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            business_id=business_id,
            action=action,
            resource=resource,
            ip_address=ip_address,
            metadata_json=metadata or {},
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        logger.info(
            "Audit event recorded",
            extra={
                "audit_action": action,
                "audit_resource": resource,
                "user_id": user_id,
                "business_id": business_id,
            },
        )
        return entry
