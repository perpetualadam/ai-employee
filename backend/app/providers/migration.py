"""Provider migration — future number/business moves between CPaaS vendors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderMigrationPlan:
    business_id: str
    from_provider: str
    to_provider: str
    steps: list[str]
    supported: bool
    notes: str


class ProviderMigrationService:
    """
    Future-facing migration orchestrator.

    Business services call this service — never vendor SDKs directly — so migration
    workflows can be added without changing call sites.
    """

    def plan_number_migration(
        self,
        *,
        business_id: str,
        phone_number: str,
        from_provider: str,
        to_provider: str,
    ) -> ProviderMigrationPlan:
        steps = [
            "Verify destination provider supports country and number type",
            "Purchase or port number on destination provider",
            "Reconfigure voice and SMS webhooks",
            "Update PhoneNumber.provider ownership records",
            "Run parallel verification window",
            "Release number on source provider when stable",
        ]
        return ProviderMigrationPlan(
            business_id=business_id,
            from_provider=from_provider,
            to_provider=to_provider,
            steps=steps,
            supported=False,
            notes=f"Migration planning scaffold for {phone_number}; execution not yet implemented.",
        )

    def plan_business_migration(
        self,
        *,
        business_id: str,
        from_provider: str,
        to_provider: str,
    ) -> dict[str, Any]:
        return {
            "business_id": business_id,
            "from_provider": from_provider,
            "to_provider": to_provider,
            "status": "planned",
            "supported": False,
            "actions": [
                "Update business.provider_config overrides",
                "Re-provision or port all active numbers",
                "Re-submit regulatory bundles where required",
                "Rebind webhook endpoints",
            ],
        }
