"""
API router for FHIR HealthcareService resources.

Exposes CRUD endpoints under /healthcare-services:
    POST   /healthcare-services/                — create a new HealthcareService
    GET    /healthcare-services/{service_id}    — fetch a single HealthcareService by ID
    GET    /healthcare-services/                — paginated list with filters
    PATCH  /healthcare-services/{service_id}    — partial update (scalar/photo fields only)
    DELETE /healthcare-services/{service_id}    — permanent delete

No `/me` endpoint — a HealthcareService describes a service a facility
offers, not something scoped to "the caller's own record" (matches Location).

Content negotiation:
  Accept: application/json         → plain snake_case JSON (default)
  Accept: application/fhir+json    → FHIR R4 resource / Bundle

RBAC: all endpoints require the "healthcare_service" permission resource.

Reference validation: `provided_by`, `location[]`, and `coverage_area[]` are
validated for existence and tenant match on create — see
app/services/healthcare_service_service.py's docstring. get_by_id/update/
delete are scoped to the caller's org_id.
"""

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.auth.models import AuthUser
from app.auth.rbac import require_permission
from app.core.content_negotiation import format_paginated_response, format_response, get_accept_header
from app.core.schema_utils import inline_schema
from app.di.dependencies.healthcare_service import get_healthcare_service_service
from app.schemas.healthcare_service.fhir_schemas import FhirBundleResponse, FhirHealthcareServiceResponse
from app.schemas.healthcare_service.input import (
    HealthcareServiceCreateSchema,
    HealthcareServicePatchSchema,
    ListHealthcareServicesSchema,
)
from app.schemas.healthcare_service.response import HealthcareServiceResponse, PaginatedHealthcareServiceResponse
from app.services.healthcare_service_service import HealthcareServiceService

router = APIRouter(prefix="/healthcare-services", tags=["HealthcareServices"])

# ── Shared error response dicts ───────────────────────────────────────────────
_ERR_NOT_FOUND = {404: {"description": "HealthcareService not found"}}
_ERR_VALIDATION = {422: {"description": "Validation error"}}

# ── Dual-format success response dicts for OpenAPI documentation ───────────────

_SINGLE_201 = {
    201: {
        "description": "HealthcareService created successfully",
        "content": {
            "application/json": {"schema": inline_schema(HealthcareServiceResponse.model_json_schema())},
            "application/fhir+json": {"schema": inline_schema(FhirHealthcareServiceResponse.model_json_schema())},
        },
    }
}

_SINGLE_200 = {
    200: {
        "description": "HealthcareService retrieved/updated successfully",
        "content": {
            "application/json": {"schema": inline_schema(HealthcareServiceResponse.model_json_schema())},
            "application/fhir+json": {"schema": inline_schema(FhirHealthcareServiceResponse.model_json_schema())},
        },
    }
}

_LIST_200 = {
    200: {
        "description": "Paginated list of HealthcareServices",
        "content": {
            "application/json": {"schema": inline_schema(PaginatedHealthcareServiceResponse.model_json_schema())},
            "application/fhir+json": {"schema": inline_schema(FhirBundleResponse.model_json_schema())},
        },
    }
}


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    operation_id="create_healthcare_service",
    summary="Create a HealthcareService",
    description=(
        "Creates a new HealthcareService. If `provided_by` is set, it must reference an existing "
        "organization in the caller's own tenant. If `location`/`coverage_area` entries are set, "
        "each must reference an existing Location in the caller's own tenant. "
        "`created_by` is stamped automatically from the caller's JWT — do not supply it. "
        "Send `Accept: application/fhir+json` to receive the created resource in FHIR R4 format."
    ),
    responses={**_SINGLE_201, **_ERR_VALIDATION, **_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("healthcare_service", "create"))],
)
async def create_healthcare_service(
    dto: HealthcareServiceCreateSchema,
    request: Request,
    actor: AuthUser = Depends(require_permission("healthcare_service", "create")),
    service: HealthcareServiceService = Depends(get_healthcare_service_service),
) -> JSONResponse:
    """Create a new HealthcareService. Forwards Accept header for content negotiation."""
    data = await service.create(dto, actor, accept=get_accept_header(request))
    return format_response(data, request)


@router.get(
    "/{service_id}",
    operation_id="get_healthcare_service",
    summary="Get a HealthcareService by ID",
    description=(
        "Retrieves a single HealthcareService by its public integer ID, scoped to the caller's "
        "organization. Send `Accept: application/fhir+json` to receive the resource in FHIR R4 format."
    ),
    responses={**_SINGLE_200, **_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("healthcare_service", "read"))],
)
async def get_healthcare_service(
    service_id: int,
    request: Request,
    actor: AuthUser = Depends(require_permission("healthcare_service", "read")),
    service: HealthcareServiceService = Depends(get_healthcare_service_service),
) -> JSONResponse:
    """Fetch a single HealthcareService by ID. Forwards Accept header for content negotiation."""
    data = await service.get_by_id(service_id, actor, accept=get_accept_header(request))
    return format_response(data, request)


@router.get(
    "/",
    operation_id="list_healthcare_services",
    summary="List HealthcareServices",
    description=(
        "Returns a paginated list of HealthcareServices. Filter by `name` (case-insensitive "
        "substring) and `active` status. Use `limit` and `offset` for pagination. "
        "Send `Accept: application/fhir+json` to receive results as a FHIR Bundle searchset."
    ),
    responses={**_LIST_200},
    dependencies=[Depends(require_permission("healthcare_service", "read"))],
)
async def list_healthcare_services(
    request: Request,
    filters: ListHealthcareServicesSchema = Depends(),
    actor: AuthUser = Depends(require_permission("healthcare_service", "read")),
    service: HealthcareServiceService = Depends(get_healthcare_service_service),
) -> JSONResponse:
    """List HealthcareServices with optional filters."""
    data = await service.list(filters, actor, accept=get_accept_header(request))
    return format_paginated_response(data, request)


@router.patch(
    "/{service_id}",
    operation_id="update_healthcare_service",
    summary="Partially update a HealthcareService",
    description=(
        "Updates scalar and photo_* fields on a HealthcareService. At least one field must be "
        "provided. `provided_by`, `location`, `coverage_area`, and every array sub-resource are "
        "not patchable — delete and re-create to correct those. Scoped to the caller's "
        "organization. Send `Accept: application/fhir+json` to receive the updated resource in "
        "FHIR R4 format."
    ),
    responses={**_SINGLE_200, **_ERR_NOT_FOUND, **_ERR_VALIDATION},
    dependencies=[Depends(require_permission("healthcare_service", "update"))],
)
async def update_healthcare_service(
    service_id: int,
    dto: HealthcareServicePatchSchema,
    request: Request,
    actor: AuthUser = Depends(require_permission("healthcare_service", "update")),
    service: HealthcareServiceService = Depends(get_healthcare_service_service),
) -> JSONResponse:
    """Partially update a HealthcareService. Forwards Accept header for content negotiation."""
    data = await service.update(service_id, dto, actor, accept=get_accept_header(request))
    return format_response(data, request)


@router.delete(
    "/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_healthcare_service",
    summary="Delete a HealthcareService",
    description=(
        "Permanently deletes the HealthcareService and all its associated child records, scoped "
        "to the caller's organization. This operation is irreversible."
    ),
    responses={**_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("healthcare_service", "delete"))],
)
async def delete_healthcare_service(
    service_id: int,
    actor: AuthUser = Depends(require_permission("healthcare_service", "delete")),
    service: HealthcareServiceService = Depends(get_healthcare_service_service),
) -> None:
    """Delete a HealthcareService. No content negotiation — DELETE returns 204 with no body."""
    await service.delete(service_id, actor)
