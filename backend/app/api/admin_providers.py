"""Admin provider management — capabilities, health, metrics, and connection tests."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security_policy import verify_internal_secret
from app.plugins.manager import get_plugin_manager
from app.providers.factory import get_factory, get_registry
from app.providers.metrics import get_provider_metrics
from app.providers.migration import ProviderMigrationService
from app.providers.services import ProviderService

router = APIRouter(prefix="/admin/providers", tags=["admin-providers"])


@router.get("/management")
def provider_management_dashboard(_: None = Depends(verify_internal_secret)) -> dict:
    registry = get_registry()
    return {
        "installed": registry.discover(),
        "registry": {service.value: registry.list_registered(service) for service in ProviderService},
        "health": get_factory().health_check(),
        "metrics": get_provider_metrics().all_snapshots(),
    }


@router.post("/test/{service}/{provider_name}")
def test_provider_connection(
    service: str,
    provider_name: str,
    _: None = Depends(verify_internal_secret),
) -> dict:
    try:
        provider_service = ProviderService(service)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown service") from exc

    registry = get_registry()
    provider = registry.get(provider_service, provider_name)
    health = provider.health(service=provider_service.value)
    caps = provider.get_capabilities()
    return {
        "service": provider_service.value,
        "provider": provider_name,
        "configured": provider.is_configured(),
        "healthy": health.healthy,
        "health": health.__dict__,
        "capabilities": caps.to_dict(),
        "supported_features": sorted(caps.supported_features()),
    }


@router.get("/migration/plan")
def preview_migration_plan(
    business_id: str,
    from_provider: str,
    to_provider: str,
    phone_number: str | None = None,
    _: None = Depends(verify_internal_secret),
) -> dict:
    service = ProviderMigrationService()
    if phone_number:
        plan = service.plan_number_migration(
            business_id=business_id,
            phone_number=phone_number,
            from_provider=from_provider,
            to_provider=to_provider,
        )
        return plan.__dict__
    return service.plan_business_migration(
        business_id=business_id,
        from_provider=from_provider,
        to_provider=to_provider,
    )


@router.get("/plugins")
def plugin_management_dashboard(_: None = Depends(verify_internal_secret)) -> dict:
    return get_plugin_manager().admin_snapshot()
