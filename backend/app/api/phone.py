"""Per-tenant phone number provisioning endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import get_user_primary_business
from app.database import get_db
from app.dependencies.providers import get_phone_number_service, get_verification_service
from app.domain.telecom import get_number_search_profile
from app.models import Business
from app.models.enums import DocumentType
from app.providers.exceptions import ProviderError
from app.schemas import (
    PhoneProvisionRequest,
    PhoneProvisionResponse,
    PhoneProvisioningStatusResponse,
    PhoneSearchResponse,
    VerificationDocumentResponse,
    VerificationStatusResponse,
    VerificationSubmitRequest,
)
from app.services.phone_number_service import PhoneNumberService
from app.services.verification_service import VerificationService
from app.utils.errors import http_exception_from_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/business/phone", tags=["phone"])

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/jpg",
    }
)


@router.get("/status", response_model=PhoneProvisioningStatusResponse)
def phone_status(
    business: Business = Depends(get_user_primary_business),
    service: PhoneNumberService = Depends(get_phone_number_service),
) -> PhoneProvisioningStatusResponse:
    return PhoneProvisioningStatusResponse(**service.status(business))


@router.get("/available", response_model=PhoneSearchResponse)
def search_phone_numbers(
    prefix: str | None = Query(
        default=None,
        max_length=20,
        description="Optional prefix to narrow the search (area code, NDC, city name, etc.)",
    ),
    limit: int = Query(default=10, ge=1, le=25),
    number_type: str | None = Query(
        default=None,
        max_length=32,
        description="Number type, e.g. mobile or local (UK defaults to mobile)",
    ),
    business: Business = Depends(get_user_primary_business),
    service: PhoneNumberService = Depends(get_phone_number_service),
) -> PhoneSearchResponse:
    try:
        numbers = service.search_available(
            business,
            prefix=prefix,
            limit=limit,
            number_type=number_type,
        )
    except ProviderError as exc:
        raise http_exception_from_provider(exc) from exc

    profile = get_number_search_profile(business.country)
    effective_type = number_type or profile.default_phone_number_type
    prefix_supported = profile.prefix_param is not None and not (
        business.country.upper() == "GB" and effective_type == "mobile"
    )
    return PhoneSearchResponse(
        country=business.country,
        numbers=numbers,
        prefix_label=profile.prefix_label,
        prefix_example=profile.prefix_example,
        prefix_supported=prefix_supported,
        number_type=effective_type,
        number_type_options=[
            {"value": value, "label": label}
            for value, label in profile.available_phone_number_types
        ],
    )


@router.post("/provision", response_model=PhoneProvisionResponse)
def provision_phone_number(
    body: PhoneProvisionRequest,
    business: Business = Depends(get_user_primary_business),
    service: PhoneNumberService = Depends(get_phone_number_service),
) -> PhoneProvisionResponse:
    try:
        result = service.provision(business, body.phone_number)
    except ProviderError as exc:
        raise http_exception_from_provider(exc) from exc
    return PhoneProvisionResponse(**result)


@router.get("/verification/requirements")
def verification_requirements(
    business: Business = Depends(get_user_primary_business),
    verification: VerificationService = Depends(get_verification_service),
) -> dict:
    return verification.get_requirements(business.country)


@router.get("/verification/status", response_model=VerificationStatusResponse)
def verification_status(
    business: Business = Depends(get_user_primary_business),
    verification: VerificationService = Depends(get_verification_service),
) -> VerificationStatusResponse:
    profile = verification.get_profile(business.id, business.country)
    documents = verification.list_documents(business.id)
    return VerificationStatusResponse(
        country_code=profile.country_code,
        status=profile.status.value,
        provider_end_user_id=profile.provider_end_user_id,
        provider_bundle_id=profile.provider_bundle_id,
        last_checked=profile.last_checked.isoformat() if profile.last_checked else None,
        uploaded_documents=[
            VerificationDocumentResponse(
                id=doc.id,
                document_type=doc.document_type.value,
                verification_status=doc.verification_status.value,
                storage_key=doc.storage_key,
                provider_document_id=doc.provider_document_id,
                created_at=doc.created_at,
            )
            for doc in documents
        ],
    )


@router.get("/verification/documents", response_model=list[VerificationDocumentResponse])
def list_verification_documents(
    business: Business = Depends(get_user_primary_business),
    verification: VerificationService = Depends(get_verification_service),
) -> list[VerificationDocumentResponse]:
    return [
        VerificationDocumentResponse(
            id=doc.id,
            document_type=doc.document_type.value,
            verification_status=doc.verification_status.value,
            storage_key=doc.storage_key,
            provider_document_id=doc.provider_document_id,
            created_at=doc.created_at,
        )
        for doc in verification.list_documents(business.id)
    ]


@router.post("/verification/documents", response_model=VerificationDocumentResponse)
async def upload_verification_document(
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    business: Business = Depends(get_user_primary_business),
    verification: VerificationService = Depends(get_verification_service),
) -> VerificationDocumentResponse:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a PDF or JPEG/PNG image.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty.")
    if len(file_bytes) > MAX_DOCUMENT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File must be 10 MB or smaller.",
        )

    filename = (file.filename or "document").replace("\\", "/").split("/")[-1][:200]
    try:
        doc = verification.upload_document(
            business_id=business.id,
            country_code=business.country,
            document_type=document_type,
            file_bytes=file_bytes,
            filename=filename,
            content_type=file.content_type or "application/octet-stream",
        )
    except ProviderError as exc:
        raise http_exception_from_provider(exc) from exc

    logger.info(
        "Verification document uploaded",
        extra={"business_id": business.id, "document_type": document_type.value, "doc_id": doc.id},
    )
    return VerificationDocumentResponse(
        id=doc.id,
        document_type=doc.document_type.value,
        verification_status=doc.verification_status.value,
        storage_key=doc.storage_key,
        provider_document_id=doc.provider_document_id,
        created_at=doc.created_at,
    )


@router.post("/verification/submit", response_model=VerificationStatusResponse)
def submit_verification(
    body: VerificationSubmitRequest,
    business: Business = Depends(get_user_primary_business),
    verification: VerificationService = Depends(get_verification_service),
) -> VerificationStatusResponse:
    end_user_payload = {
        "business_name": body.business_name,
        "contact_email": body.contact_email,
        "address": body.address,
        "country_code": business.country,
    }
    try:
        profile = verification.submit_verification(
            business_id=business.id,
            country_code=business.country,
            end_user_payload=end_user_payload,
        )
    except ProviderError as exc:
        raise http_exception_from_provider(exc) from exc

    documents = verification.list_documents(business.id)
    return VerificationStatusResponse(
        country_code=profile.country_code,
        status=profile.status.value,
        provider_end_user_id=profile.provider_end_user_id,
        provider_bundle_id=profile.provider_bundle_id,
        last_checked=profile.last_checked.isoformat() if profile.last_checked else None,
        uploaded_documents=[
            VerificationDocumentResponse(
                id=doc.id,
                document_type=doc.document_type.value,
                verification_status=doc.verification_status.value,
                storage_key=doc.storage_key,
                provider_document_id=doc.provider_document_id,
                created_at=doc.created_at,
            )
            for doc in documents
        ],
    )
