"""
API router for FHIR Organization resources.

Exposes CRUD endpoints under /organizations:
    POST   /organizations/                    — register a new Organization
    GET    /organizations/me                 — get Organizations for the current user
    GET    /organizations/{organization_id}  — fetch a single Organization by ID
    GET    /organizations/                    — paginated list with filters
    PATCH  /organizations/{organization_id}  — partial update (scalar fields only)
    DELETE /organizations/{organization_id}  — permanent delete

Route ordering is critical: /me must appear before /{organization_id} so
FastAPI does not attempt to cast the literal string "me" as an integer —
same reasoning as app/routers/patient.py.

Content negotiation:
  Accept: application/json         → plain snake_case JSON (default)
  Accept: application/fhir+json    → FHIR R4 resource / Bundle

RBAC: all endpoints require the "org" permission resource (matching the
sibling project's naming convention this feature was ported from).

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
    ListOrgsSchema,
    MeOrgsSchema,
    PatchOrgSchema,
    RegisterOrgSchema,
)
from app.schemas.organization.response import OrgResponse, PaginatedOrgResponse
from app.services.organization_service import OrganizationsService

router = APIRouter(prefix="/organizations", tags=["Organizations"])

# ── Shared error response dicts ───────────────────────────────────────────────
_ERR_NOT_FOUND = {404: {"description": "Organization not found"}}
_ERR_CONFLICT = {409: {"description": "Organization with that name already exists"}}
_ERR_VALIDATION = {422: {"description": "Validation error"}}

# ── Dual-format success response dicts for OpenAPI documentation ───────────────
# inline_schema() resolves Pydantic $defs/$ref so sub-model references don't
# break when embedded in the OpenAPI responses dict (Swagger UI resolver limit).

_SINGLE_201 = {
    201: {
        "description": "Organization created successfully",
        "content": {
            "application/json": {
                "schema": inline_schema(OrgResponse.model_json_schema())
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
                "schema": inline_schema(OrgResponse.model_json_schema())
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
                "schema": inline_schema(PaginatedOrgResponse.model_json_schema())
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
        "Creates a new Organization. "
        "Enforces that `name` and `type` are provided (FHIR leaves these optional). "
        "Deduplicates by name — returns 409 if an organization with the same name already exists. "
        "If `partof` is provided, it must reference an existing organization in the caller's own "
        "tenant — returns 404 otherwise. "
        "`created_by` is stamped automatically from the caller's JWT — do not supply it. "
        "Send `Accept: application/fhir+json` to receive the created resource in FHIR R4 format."
    ),
    responses={**_SINGLE_201, **_ERR_CONFLICT, **_ERR_VALIDATION, **_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("org", "create"))],
)
async def register_organization(
    dto: RegisterOrgSchema,
    request: Request,
    actor: AuthUser = Depends(require_permission("org", "create")),
    service: OrganizationsService = Depends(get_organization_service),
) -> JSONResponse:
    """Register a new Organization. Forwards Accept header for content negotiation."""
    data = await service.register(dto, actor, accept=get_accept_header(request))
    return format_response(data, request)


@router.get(
    "/me",
    operation_id="get_my_organizations",
    summary="Get Organizations for the current user",
    description=(
        "Returns Organizations scoped to the calling user's JWT identity. "
        "`user_id` and `org_id` are derived from the token — the caller cannot override them. "
        "Supports `active` filter and `limit`/`offset` pagination. "
        "Send `Accept: application/fhir+json` to receive results as a FHIR Bundle searchset."
    ),
    responses={**_LIST_200},
    dependencies=[Depends(require_permission("org", "read"))],
)
async def get_my_organizations(
    request: Request,
    filters: MeOrgsSchema = Depends(),
    actor: AuthUser = Depends(require_permission("org", "read")),
    service: OrganizationsService = Depends(get_organization_service),
) -> JSONResponse:
    """List Organizations owned by the current user, scoped server-side by JWT claims."""
    data = await service.get_me(filters, actor, accept=get_accept_header(request))
    return format_paginated_response(data, request)


@router.get(
    "/{organization_id}",
    operation_id="get_organization",
    summary="Get an Organization by ID",
    description=(
        "Retrieves a single Organization by its public integer ID, scoped to the caller's "
        "organization. Send `Accept: application/fhir+json` to receive the resource in FHIR R4 format."
    ),
    responses={**_SINGLE_200, **_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("org", "read"))],
)
async def get_organization(
    organization_id: int,
    request: Request,
    actor: AuthUser = Depends(require_permission("org", "read")),
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
    dependencies=[Depends(require_permission("org", "read"))],
)
async def list_organizations(
    request: Request,
    filters: ListOrgsSchema = Depends(),
    actor: AuthUser = Depends(require_permission("org", "read")),
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
    dependencies=[Depends(require_permission("org", "update"))],
)
async def update_organization(
    organization_id: int,
    dto: PatchOrgSchema,
    request: Request,
    actor: AuthUser = Depends(require_permission("org", "update")),
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
    dependencies=[Depends(require_permission("org", "delete"))],
)
async def delete_organization(
    organization_id: int,
    actor: AuthUser = Depends(require_permission("org", "delete")),
    service: OrganizationsService = Depends(get_organization_service),
) -> None:
    """Delete an Organization. No content negotiation — DELETE returns 204 with no body."""
    await service.delete(organization_id, actor)
