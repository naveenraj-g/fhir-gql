"""
API router for FHIR PractitionerRole resources.

Exposes CRUD endpoints under /practitioner-roles:
    GET    /practitioner-roles/booking         — enriched list for booking UIs
    POST   /practitioner-roles/                — create a new PractitionerRole
    GET    /practitioner-roles/{resource_id}   — fetch a single PractitionerRole by ID
    GET    /practitioner-roles/                — paginated list with filters
    PATCH  /practitioner-roles/{resource_id}   — partial update (scalar fields only)
    DELETE /practitioner-roles/{resource_id}   — permanent delete

Route ordering is critical: /booking must appear before /{resource_id} so
FastAPI does not attempt to cast the literal string "booking" as an integer.

Unlike Practitioner, PractitionerRole accepts all child arrays (identifier,
code, specialty, location, healthcare_service, characteristic,
communication, contact, availability, endpoint) directly in the create
body — there are no dedicated sub-resource routes, and none of these arrays
are patchable.

Content negotiation:
  Accept: application/json         → plain snake_case JSON (default)
  Accept: application/fhir+json    → FHIR R4 resource / Bundle

RBAC: all endpoints require the "practitioner_role" permission resource.

Reference validation: `practitioner`, `organization`, and each
`location[]`/`healthcare_service[]` entry are validated for existence and
tenant match on create — see app/services/practitioner_role_service.py's docstring.
"""

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.auth.models import AuthUser
from app.auth.rbac import require_permission
from app.core.content_negotiation import format_paginated_response, format_response, get_accept_header
from app.core.schema_utils import inline_schema
from app.di.dependencies.practitioner_role import get_practitioner_role_service
from app.schemas.practitioner_role.fhir_schemas import FhirBundleResponse, FhirPractitionerRoleResponse
from app.schemas.practitioner_role.input import (
    ListPractitionerRolesSchema,
    PractitionerRoleCreateSchema,
    PractitionerRolePatchSchema,
)
from app.schemas.practitioner_role.response import (
    PaginatedPractitionerRoleBookingResponse,
    PaginatedPractitionerRoleResponse,
    PractitionerRoleResponse,
)
from app.services.practitioner_role_service import PractitionerRoleService

router = APIRouter(prefix="/practitioner-roles", tags=["PractitionerRoles"])

# ── Shared error response dicts ───────────────────────────────────────────────
_ERR_NOT_FOUND = {404: {"description": "PractitionerRole not found"}}
_ERR_VALIDATION = {422: {"description": "Validation error"}}

# ── Dual-format success response dicts for OpenAPI documentation ───────────────

_SINGLE_201 = {
    201: {
        "description": "PractitionerRole created successfully",
        "content": {
            "application/json": {"schema": inline_schema(PractitionerRoleResponse.model_json_schema())},
            "application/fhir+json": {"schema": inline_schema(FhirPractitionerRoleResponse.model_json_schema())},
        },
    }
}

_SINGLE_200 = {
    200: {
        "description": "PractitionerRole retrieved/updated successfully",
        "content": {
            "application/json": {"schema": inline_schema(PractitionerRoleResponse.model_json_schema())},
            "application/fhir+json": {"schema": inline_schema(FhirPractitionerRoleResponse.model_json_schema())},
        },
    }
}

_LIST_200 = {
    200: {
        "description": "Paginated list of PractitionerRoles",
        "content": {
            "application/json": {"schema": inline_schema(PaginatedPractitionerRoleResponse.model_json_schema())},
            "application/fhir+json": {"schema": inline_schema(FhirBundleResponse.model_json_schema())},
        },
    }
}

_BOOKING_LIST_200 = {
    200: {
        "description": "Paginated list of practitioners enriched for booking UIs",
        "content": {
            "application/json": {"schema": inline_schema(PaginatedPractitionerRoleBookingResponse.model_json_schema())},
            "application/fhir+json": {"schema": inline_schema(FhirBundleResponse.model_json_schema())},
        },
    }
}


@router.get(
    "/booking",
    operation_id="list_practitioner_roles_for_booking",
    summary="List practitioners available for appointment booking",
    description=(
        "Returns active PractitionerRole resources enriched with the linked Practitioner's name, "
        "gender, photo, and qualifications, plus enriched Location/HealthcareService data — "
        "everything a booking UI needs in one call. Filter by `specialty_code` (e.g. a SNOMED "
        "code) and/or `day_of_week`. Send `Accept: application/fhir+json` for a FHIR R4 Bundle."
    ),
    responses={**_BOOKING_LIST_200},
    dependencies=[Depends(require_permission("practitioner_role", "read"))],
)
async def list_practitioner_roles_for_booking(
    request: Request,
    specialty_code: str | None = None,
    day_of_week: str | None = None,
    org_id: str | None = None,
    active: bool = True,
    limit: int = 50,
    offset: int = 0,
    actor: AuthUser = Depends(require_permission("practitioner_role", "read")),
    service: PractitionerRoleService = Depends(get_practitioner_role_service),
) -> JSONResponse:
    """Return practitioners enriched for booking UIs. Proxies to the fhir-server's /practitioner-roles/booking endpoint."""
    data = await service.list_for_booking(
        active=active,
        specialty_code=specialty_code,
        day_of_week=day_of_week,
        org_id=org_id,
        limit=limit,
        offset=offset,
        accept=get_accept_header(request),
    )
    return format_paginated_response(data, request)


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    operation_id="create_practitioner_role",
    summary="Create a PractitionerRole",
    description=(
        "Creates a new PractitionerRole — the role a Practitioner plays at an Organization and "
        "Location, including specialties, availability, and characteristics. Child arrays can be "
        "included directly in the create body. If `practitioner`/`organization` are set, each "
        "must reference an existing resource in the caller's own tenant; each `location[]`/"
        "`healthcare_service[]` entry is validated the same way. `created_by` is stamped "
        "automatically from the caller's JWT. Send `Accept: application/fhir+json` for FHIR R4 format."
    ),
    responses={**_SINGLE_201, **_ERR_VALIDATION, **_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("practitioner_role", "create"))],
)
async def create_practitioner_role(
    dto: PractitionerRoleCreateSchema,
    request: Request,
    actor: AuthUser = Depends(require_permission("practitioner_role", "create")),
    service: PractitionerRoleService = Depends(get_practitioner_role_service),
) -> JSONResponse:
    """Create a new PractitionerRole. Forwards Accept header for content negotiation."""
    data = await service.create(dto, actor, accept=get_accept_header(request))
    return format_response(data, request)


@router.get(
    "/{resource_id}",
    operation_id="get_practitioner_role",
    summary="Get a PractitionerRole by ID",
    description=(
        "Retrieves a single PractitionerRole by its public integer ID, including all child arrays. "
        "Send `Accept: application/fhir+json` to receive the resource in FHIR R4 format."
    ),
    responses={**_SINGLE_200, **_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("practitioner_role", "read"))],
)
async def get_practitioner_role(
    resource_id: int,
    request: Request,
    actor: AuthUser = Depends(require_permission("practitioner_role", "read")),
    service: PractitionerRoleService = Depends(get_practitioner_role_service),
) -> JSONResponse:
    """Fetch a single PractitionerRole by ID. Forwards Accept header for content negotiation."""
    data = await service.get_by_id(resource_id, actor, accept=get_accept_header(request))
    return format_response(data, request)


@router.get(
    "/",
    operation_id="list_practitioner_roles",
    summary="List PractitionerRoles",
    description=(
        "Returns a paginated list of PractitionerRoles. Filter by `active`, `practitioner_id`, "
        "`user_id`, or `org_id`. Use `limit`/`offset` for pagination. "
        "Send `Accept: application/fhir+json` to receive results as a FHIR Bundle searchset."
    ),
    responses={**_LIST_200},
    dependencies=[Depends(require_permission("practitioner_role", "read"))],
)
async def list_practitioner_roles(
    request: Request,
    filters: ListPractitionerRolesSchema = Depends(),
    actor: AuthUser = Depends(require_permission("practitioner_role", "read")),
    service: PractitionerRoleService = Depends(get_practitioner_role_service),
) -> JSONResponse:
    """List PractitionerRoles with optional filters."""
    data = await service.list(filters, actor, accept=get_accept_header(request))
    return format_paginated_response(data, request)


@router.patch(
    "/{resource_id}",
    operation_id="update_practitioner_role",
    summary="Partially update a PractitionerRole",
    description=(
        "Updates `active`, `period_start`, `period_end`, or `availability_exceptions` on a "
        "PractitionerRole. At least one field must be provided. Child arrays cannot be patched — "
        "delete and re-create to correct those. Send `Accept: application/fhir+json` for FHIR R4 format."
    ),
    responses={**_SINGLE_200, **_ERR_NOT_FOUND, **_ERR_VALIDATION},
    dependencies=[Depends(require_permission("practitioner_role", "update"))],
)
async def update_practitioner_role(
    resource_id: int,
    dto: PractitionerRolePatchSchema,
    request: Request,
    actor: AuthUser = Depends(require_permission("practitioner_role", "update")),
    service: PractitionerRoleService = Depends(get_practitioner_role_service),
) -> JSONResponse:
    """Partially update a PractitionerRole. Forwards Accept header for content negotiation."""
    data = await service.update(resource_id, dto, actor, accept=get_accept_header(request))
    return format_response(data, request)


@router.delete(
    "/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_practitioner_role",
    summary="Delete a PractitionerRole",
    description=(
        "Permanently deletes the PractitionerRole and all its associated child records. This "
        "operation is irreversible."
    ),
    responses={**_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("practitioner_role", "delete"))],
)
async def delete_practitioner_role(
    resource_id: int,
    actor: AuthUser = Depends(require_permission("practitioner_role", "delete")),
    service: PractitionerRoleService = Depends(get_practitioner_role_service),
) -> None:
    """Delete a PractitionerRole. No content negotiation — DELETE returns 204 with no body."""
    await service.delete(resource_id, actor)
