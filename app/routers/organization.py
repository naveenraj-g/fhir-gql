"""
API router for FHIR Organization resources.

Exposes CRUD endpoints under /organizations:
    POST   /organizations/                    — register a new Organization
    GET    /organizations/{organization_id}  — fetch a single Organization by ID
    GET    /organizations/                    — paginated list with filters
    PATCH  /organizations/{organization_id}  — partial update (scalar fields only)
    DELETE /organizations/{organization_id}  — permanent delete

Unlike Patient/Practitioner there is no /me route — fhir-server's
Organization has no user_id at all (a shared tenant-level entity, not scoped
to an individual end-user), so there's no "my own organizations" concept.

Content negotiation:
  Accept: application/json         → plain snake_case JSON (default)
  Accept: application/fhir+json    → FHIR R4 resource / Bundle

RBAC: all endpoints require the "organization" permission resource,
matching fhir-server's own RBAC scope naming exactly.

Tenant scoping: get_by_id/update/delete are scoped to the caller's org_id by
OrganizationsService (404 if the resource belongs to a different org) — see
that module's docstring for why this differs from Patient's equivalent
by-id operations.
"""

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.auth.models import AuthUser
from app.auth.rbac import require_permission
from app.core.content_negotiation import (
    format_paginated_response,
    format_response,
    get_accept_header,
)
from app.core.schema_utils import inline_schema
from app.di.dependencies.organization import get_organization_service
from app.schemas.organization.fhir_schemas import FhirBundleResponse, FhirOrgResponse
from app.schemas.organization.input import (
    ListOrganizationsSchema,
    OrganizationCreateSchema,
    OrganizationPatchSchema,
)
from app.schemas.organization.response import OrganizationResponse, PaginatedOrganizationResponse
from app.services.organization_service import OrganizationsService

router = APIRouter(prefix="/organizations", tags=["Organizations"])

# ── Shared error response dicts ───────────────────────────────────────────────
_ERR_NOT_FOUND = {404: {"description": "Organization not found"}}
_ERR_VALIDATION = {422: {"description": "Validation error"}}

# ── Dual-format success response dicts for OpenAPI documentation ───────────────
# inline_schema() resolves Pydantic $defs/$ref so sub-model references don't
# break when embedded in the OpenAPI responses dict (Swagger UI resolver limit).

_SINGLE_201 = {
    201: {
        "description": "Organization created successfully",
        "content": {
            "application/json": {
                "schema": inline_schema(OrganizationResponse.model_json_schema())
            },
            "application/fhir+json": {
                "schema": inline_schema(FhirOrgResponse.model_json_schema())
            },
        },
    }
}

_SINGLE_200 = {
    200: {
        "description": "Organization retrieved/updated successfully",
        "content": {
            "application/json": {
                "schema": inline_schema(OrganizationResponse.model_json_schema())
            },
            "application/fhir+json": {
                "schema": inline_schema(FhirOrgResponse.model_json_schema())
            },
        },
    }
}

_LIST_200 = {
    200: {
        "description": "Paginated list of Organizations",
        "content": {
            "application/json": {
                "schema": inline_schema(PaginatedOrganizationResponse.model_json_schema())
            },
            "application/fhir+json": {
                "schema": inline_schema(FhirBundleResponse.model_json_schema())
            },
        },
    }
}


# ── Core endpoints ────────────────────────────────────────────────────────────


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    operation_id="register_organization",
    summary="Register a new Organization",
    description=(
        "Creates a new Organization and any combination of its sub-resources "
        "(identifier, type, alias, telecom, address, contact, endpoint) atomically in one "
        "request. If `partof` is provided, fhir-server validates it exists, belongs to the "
        "caller's own tenant, and wouldn't create a circular hierarchy — 404/422 otherwise. "
        "`org_id`/`created_by` are stamped automatically from the caller's JWT — do not supply "
        "them (not accepted fields at all). "
        "Send `Accept: application/fhir+json` to receive the created resource in FHIR R4 format."
    ),
    responses={**_SINGLE_201, **_ERR_VALIDATION, **_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("organization", "create"))],
)
async def register_organization(
    dto: OrganizationCreateSchema,
    request: Request,
    actor: AuthUser = Depends(require_permission("organization", "create")),
    service: OrganizationsService = Depends(get_organization_service),
) -> JSONResponse:
    """Register a new Organization. Forwards Accept header for content negotiation."""
    data = await service.create(dto, actor, accept=get_accept_header(request))
    return format_response(data, request)


@router.get(
    "/{organization_id}",
    operation_id="get_organization",
    summary="Get an Organization by ID",
    description=(
        "Retrieves a single Organization by its public integer ID, scoped to the caller's "
        "organization. Send `Accept: application/fhir+json` to receive the resource in FHIR R4 format."
    ),
    responses={**_SINGLE_200, **_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("organization", "read"))],
)
async def get_organization(
    organization_id: int,
    request: Request,
    actor: AuthUser = Depends(require_permission("organization", "read")),
    service: OrganizationsService = Depends(get_organization_service),
) -> JSONResponse:
    """Fetch a single Organization by ID. Forwards Accept header for content negotiation."""
    data = await service.get_by_id(
        organization_id, actor, accept=get_accept_header(request)
    )
    return format_response(data, request)


@router.get(
    "/",
    operation_id="list_organizations",
    summary="List Organizations",
    description=(
        "Returns a paginated list of Organizations. "
        "Filter by `name` (case-insensitive substring) and `active` status. "
        "Use `limit` and `offset` for pagination. "
        "Send `Accept: application/fhir+json` to receive results as a FHIR Bundle searchset."
    ),
    responses={**_LIST_200},
    dependencies=[Depends(require_permission("organization", "read"))],
)
async def list_organizations(
    request: Request,
    filters: ListOrganizationsSchema = Depends(),
    actor: AuthUser = Depends(require_permission("organization", "read")),
    service: OrganizationsService = Depends(get_organization_service),
) -> JSONResponse:
    """List Organizations with optional filters."""
    data = await service.list(filters, actor, accept=get_accept_header(request))
    return format_paginated_response(data, request)


@router.patch(
    "/{organization_id}",
    operation_id="update_organization",
    summary="Partially update an Organization",
    description=(
        "Patchable fields: `active`, `name`, `partof_display`. "
        "Child arrays (identifier, type, alias, telecom, address, contact, endpoint) "
        "are not patchable — delete and re-create to correct those. "
        "At least one field must be provided. Scoped to the caller's organization. "
        "Send `Accept: application/fhir+json` to receive the updated resource in FHIR R4 format."
    ),
    responses={**_SINGLE_200, **_ERR_NOT_FOUND, **_ERR_VALIDATION},
    dependencies=[Depends(require_permission("organization", "update"))],
)
async def update_organization(
    organization_id: int,
    dto: OrganizationPatchSchema,
    request: Request,
    actor: AuthUser = Depends(require_permission("organization", "update")),
    service: OrganizationsService = Depends(get_organization_service),
) -> JSONResponse:
    """Partially update an Organization. Forwards Accept header for content negotiation."""
    data = await service.update(
        organization_id, dto, actor, accept=get_accept_header(request)
    )
    return format_response(data, request)


@router.delete(
    "/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_organization",
    summary="Delete an Organization",
    description=(
        "Permanently deletes the Organization and all its associated child records, "
        "scoped to the caller's organization. This operation is irreversible."
    ),
    responses={**_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("organization", "delete"))],
)
async def delete_organization(
    organization_id: int,
    actor: AuthUser = Depends(require_permission("organization", "delete")),
    service: OrganizationsService = Depends(get_organization_service),
) -> None:
    """Delete an Organization. No content negotiation — DELETE returns 204 with no body."""
    await service.delete(organization_id, actor)
