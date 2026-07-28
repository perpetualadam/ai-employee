"""Vonage regulatory / compliance adapter — Applications + Media (+ TFN when provided)."""

from __future__ import annotations

import logging
from typing import Any

from app.config import get_settings
from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, vonage_regulatory
from app.providers.exceptions import ProviderUnavailableError
from app.providers.regulatory import RegulatoryProvider
from app.voice import vonage_client

logger = logging.getLogger(__name__)

_TFN_COUNTRIES = frozenset({"US", "CA"})
_STATUS_APPROVED = frozenset({"approved", "active", "verified", "registered", "complete"})
_STATUS_REJECTED = frozenset({"rejected", "failed", "denied"})


def _parse_bundle_id(bundle_id: str) -> tuple[str, str | None]:
    if ":" in bundle_id:
        end_user_id, country = bundle_id.split(":", 1)
        return end_user_id, country.upper() or None
    return bundle_id, None


def _media_items_for_bundle(bundle_id: str) -> list[dict[str, Any]]:
    page = vonage_client.list_media(page_size=100, page_index=0)
    embedded = page.get("_embedded") or {}
    items = embedded.get("media") or page.get("media") or []
    return [item for item in items if (item.get("metadata_primary") or "") == bundle_id]


def _normalize_status(raw: str | None) -> str:
    status = (raw or "pending-review").lower().replace("_", "-")
    if status in _STATUS_APPROVED:
        return "approved"
    if status in _STATUS_REJECTED:
        return "rejected"
    if status in {"submitted", "pending-review", "pending", "in-review", "draft"}:
        return "pending-review"
    return status or "pending-review"


class VonageRegulatoryProvider(RegulatoryProvider):
    """
    Maps Telnyx-style regulatory ports onto Vonage Applications + Media APIs.

    - End users → Voice Applications (durable external identity)
    - Documents → Media upload + metadata (attach/submit are real Media API calls)
    - Optional US/CA Toll-Free registration when ``payload["tfn"]`` is supplied
    """

    @property
    def provider_name(self) -> str:
        return "vonage"

    def is_configured(self) -> bool:
        return vonage_client.is_vonage_configured()

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(vonage_regulatory(), self, service="regulatory")

    def _require(self) -> None:
        if not self.is_configured():
            raise ProviderUnavailableError(provider=self.provider_name)

    def create_end_user(self, *, business_id: str, payload: dict[str, Any]) -> ProviderResult:
        self._require()
        tfn_payload = payload.get("tfn")
        country = str(payload.get("country_code") or "").upper()
        if isinstance(tfn_payload, dict) and country in _TFN_COUNTRIES:
            body = {**tfn_payload}
            body.setdefault("status", "DRAFT")
            record = vonage_client.create_tfn_registration(body)
            return ProviderResult(
                provider=self.provider_name,
                external_id=record.get("id"),
                data={**record, "business_id": business_id, "kind": "tfn_registration"},
            )

        settings = get_settings()
        name = str(
            payload.get("friendly_name")
            or payload.get("business_name")
            or f"business-{business_id}"
        )
        answer_url = f"{settings.public_api_url.rstrip('/')}/api/v1/voice/inbound"
        event_url = f"{settings.public_api_url.rstrip('/')}/api/v1/voice/status"
        record = vonage_client.create_application(
            name=name,
            answer_url=answer_url,
            event_url=event_url,
        )
        return ProviderResult(
            provider=self.provider_name,
            external_id=record.get("id"),
            data={**record, "business_id": business_id, "kind": "application"},
        )

    def upload_document(self, *, file_bytes: bytes, filename: str, content_type: str) -> ProviderResult:
        self._require()
        record = vonage_client.upload_media(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
        )
        media_id = record.get("id") or filename
        # Tag upload for later bundle attachment / status queries.
        try:
            vonage_client.update_media_info(
                media_id,
                title=filename,
                description="regulatory-document",
                metadata_secondary="uploaded",
            )
        except Exception as exc:  # noqa: BLE001 — upload succeeded; metadata is best-effort
            logger.info(
                "Vonage media metadata update after upload failed",
                extra={"media_id": media_id, "error": str(exc)},
            )
        return ProviderResult(
            provider=self.provider_name,
            external_id=media_id,
            data=record,
        )

    def create_regulatory_bundle(self, *, country_code: str, end_user_id: str) -> ProviderResult:
        self._require()
        country = country_code.upper()
        # TFN registrations are themselves the compliance bundle.
        try:
            tfn = vonage_client.get_tfn_registration(end_user_id)
            if tfn.get("id"):
                return ProviderResult(
                    provider=self.provider_name,
                    external_id=tfn.get("id"),
                    data={**tfn, "country_code": country, "kind": "tfn_registration"},
                )
        except Exception:  # noqa: BLE001 — fall through to application bundle
            pass

        record = vonage_client.get_application(end_user_id) if end_user_id else {}
        bundle_id = f"{end_user_id}:{country}"
        return ProviderResult(
            provider=self.provider_name,
            external_id=bundle_id,
            data={
                "bundle_id": bundle_id,
                "country_code": country,
                "application": record,
                "kind": "application_bundle",
                "status": "draft",
            },
        )

    def attach_document(self, *, bundle_id: str, document_id: str) -> ProviderResult:
        self._require()
        end_user_id, _country = _parse_bundle_id(bundle_id)

        # Prefer TFN registration PATCH with opt-in image URLs when the bundle is a TFN id.
        if ":" not in bundle_id:
            try:
                media = vonage_client.get_media_info(document_id)
                media_url = f"https://api.nexmo.com/v3/media/{document_id}"
                existing = vonage_client.get_tfn_registration(bundle_id)
                opt_in = dict(existing.get("opt_in") or {})
                images = list(opt_in.get("images") or [])
                images.append({"url": media_url})
                opt_in["images"] = images
                opt_in.setdefault("workflow", "Other")
                opt_in.setdefault(
                    "workflow_description",
                    "Regulatory documents uploaded via API and attached to this registration.",
                )
                record = vonage_client.update_tfn_registration(bundle_id, {"opt_in": opt_in})
                vonage_client.update_media_info(
                    document_id,
                    public=True,
                    metadata_primary=bundle_id,
                    metadata_secondary="attached",
                    description=f"attached-to:{bundle_id}",
                    title=media.get("original_file_name") or document_id,
                )
                return ProviderResult(
                    provider=self.provider_name,
                    external_id=bundle_id,
                    data={**record, "document_id": document_id, "attached": True},
                )
            except Exception as exc:  # noqa: BLE001 — fall through to media attach
                logger.info(
                    "Vonage TFN attach failed; using media metadata attach",
                    extra={"bundle_id": bundle_id, "error": str(exc)},
                )

        # Application-backed bundle: verify end user + stamp media metadata (real API).
        if end_user_id:
            vonage_client.get_application(end_user_id)
        media = vonage_client.get_media_info(document_id)
        record = vonage_client.update_media_info(
            document_id,
            public=True,
            metadata_primary=bundle_id,
            metadata_secondary="attached",
            description=f"attached-to:{bundle_id}",
            title=media.get("original_file_name") or document_id,
        )
        return ProviderResult(
            provider=self.provider_name,
            external_id=bundle_id,
            data={
                "bundle_id": bundle_id,
                "document_id": document_id,
                "attached": True,
                "media": record,
            },
        )

    def submit_bundle(self, bundle_id: str) -> ProviderResult:
        self._require()
        end_user_id, _country = _parse_bundle_id(bundle_id)

        if ":" not in bundle_id:
            try:
                record = vonage_client.update_tfn_registration(
                    bundle_id,
                    {"status": "SUBMITTED"},
                )
                for item in _media_items_for_bundle(bundle_id):
                    media_id = item.get("id")
                    if media_id:
                        vonage_client.update_media_info(
                            media_id,
                            metadata_primary=bundle_id,
                            metadata_secondary="pending-review",
                        )
                return ProviderResult(
                    provider=self.provider_name,
                    external_id=bundle_id,
                    data={**record, "status": _normalize_status(record.get("status") or "SUBMITTED")},
                )
            except Exception as exc:  # noqa: BLE001 — fall through to application submit
                logger.info(
                    "Vonage TFN submit failed; using application/media submit",
                    extra={"bundle_id": bundle_id, "error": str(exc)},
                )

        attached = _media_items_for_bundle(bundle_id)
        updated_docs: list[dict[str, Any]] = []
        for item in attached:
            media_id = item.get("id")
            if not media_id:
                continue
            updated_docs.append(
                vonage_client.update_media_info(
                    media_id,
                    metadata_primary=bundle_id,
                    metadata_secondary="pending-review",
                )
            )

        application: dict[str, Any] = {}
        if end_user_id:
            application = vonage_client.get_application(end_user_id)
            name = str(application.get("name") or end_user_id)
            if not name.startswith("[pending-review]"):
                try:
                    # Applications PUT replaces the resource; preserve capabilities/webhooks.
                    application = vonage_client.update_application(
                        end_user_id,
                        payload={**application, "name": f"[pending-review] {name}"},
                    )
                except Exception as exc:  # noqa: BLE001 — document submit still succeeded
                    logger.info(
                        "Vonage application rename on submit failed",
                        extra={"application_id": end_user_id, "error": str(exc)},
                    )

        return ProviderResult(
            provider=self.provider_name,
            external_id=bundle_id,
            data={
                "bundle_id": bundle_id,
                "status": "pending-review",
                "documents": updated_docs,
                "application": application,
                "attached_count": len(updated_docs),
            },
        )

    def get_bundle_status(self, bundle_id: str) -> ProviderResult:
        self._require()
        end_user_id, _country = _parse_bundle_id(bundle_id)

        if ":" not in bundle_id:
            try:
                record = vonage_client.get_tfn_registration(bundle_id)
                status = _normalize_status(record.get("status"))
                return ProviderResult(
                    provider=self.provider_name,
                    external_id=bundle_id,
                    data={**record, "status": status},
                )
            except Exception as exc:  # noqa: BLE001 — fall through
                logger.info(
                    "Vonage TFN status probe failed",
                    extra={"bundle_id": bundle_id, "error": str(exc)},
                )

        record: dict[str, Any] = {"bundle_id": bundle_id, "status": "pending-review"}
        try:
            if end_user_id:
                record["application"] = vonage_client.get_application(end_user_id)
            docs = _media_items_for_bundle(bundle_id)
            record["documents"] = docs
            statuses = {
                _normalize_status(item.get("metadata_secondary"))
                for item in docs
                if item.get("metadata_secondary")
            }
            if "rejected" in statuses:
                record["status"] = "rejected"
            elif docs and statuses and statuses <= {"approved"}:
                record["status"] = "approved"
            elif docs:
                record["status"] = "pending-review"
            elif record.get("application"):
                name = str((record["application"] or {}).get("name") or "")
                record["status"] = "pending-review" if "[pending-review]" in name else "draft"
        except Exception as exc:  # noqa: BLE001 — surface provider status without crashing callers
            logger.info(
                "Vonage bundle status probe failed",
                extra={"bundle_id": bundle_id, "error": str(exc)},
            )
            record["status"] = "pending-review"
        return ProviderResult(provider=self.provider_name, external_id=bundle_id, data=record)

    def get_end_user_status(self, end_user_id: str) -> ProviderResult:
        self._require()
        try:
            record = vonage_client.get_tfn_registration(end_user_id)
            return ProviderResult(
                provider=self.provider_name,
                external_id=end_user_id,
                data={**record, "status": _normalize_status(record.get("status"))},
            )
        except Exception:  # noqa: BLE001 — application end users are the default
            record = vonage_client.get_application(end_user_id)
            return ProviderResult(
                provider=self.provider_name,
                external_id=end_user_id,
                data=record,
            )
