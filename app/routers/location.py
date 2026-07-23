"""
API router for FHIR Location resources.

Exposes CRUD endpoints under /locations:
    POST   /locations/                 — create a new Location
    GET    /locations/{location_id}   — fetch a single Location by ID
    GET    /locations/                 — paginated list with filters
    PATCH  /locations/{location_id}   — partial update
    DELETE /locations/{location_id}   — permanent delete

Unlike Patient/Organization, Location has no `/me` endpoint — a Location is
a place, not something scoped to "the caller's own record."

Content negotiation:
  Accept: application/json         → plain snake_case JSON (default)
  Accept: application/fhir+json    → FHIR R4 resource / Bundle

RBAC: all endpoints require the "location" permission resource.

Tenant scoping and reference validation: get_by_id/update/delete are scoped
to the caller's org_id, and `part_of`/`managing_organization` are validated
for existence, tenant match, and (for `part_of`) circular-hierarchy
prevention — see app/services/location_service.py's docstring.
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
from app.di.dependencies.location import get_location_service
from app.schemas.location.fhir_schemas import FhirBundleResponse, FhirLocationResponse
from app.schemas.location.input import (
    ListLocationsSchema,
    LocationCreateSchema,
    LocationPatchSchema,
)
from app.schemas.location.response import LocationResponse, PaginatedLocationResponse
from app.services.location_service import LocationService

router = APIRouter(prefix="/locations", tags=["Locations"])

# ── Shared error response dicts ───────────────────────────────────────────────
_ERR_NOT_FOUND = {404: {"description": "Location not found"}}
_ERR_VALIDATION = {422: {"description": "Validation error"}}
_ERR_CONFLICT = {409: {"description": "Would create a circular Location hierarchy"}}

# ── Dual-format success response dicts for OpenAPI documentation ───────────────

_SINGLE_201 = {
    201: {
        "description": "Location created successfully",
        "content": {
            "application/json": {
                "schema": inline_schema(LocationResponse.model_json_schema())
            },
            "application/fhir+json": {
                "schema": inline_schema(FhirLocationResponse.model_json_schema())
            },
        },
    }
}

_SINGLE_200 = {
    200: {
        "description": "Location retrieved/updated successfully",
        "content": {
            "application/json": {
                "schema": inline_schema(LocationResponse.model_json_schema())
            },
            "application/fhir+json": {
                "schema": inline_schema(FhirLocationResponse.model_json_schema())
            },
        },
    }
}

_LIST_200 = {
    200: {
        "description": "Paginated list of Locations",
        "content": {
            "application/json": {
                "schema": inline_schema(PaginatedLocationResponse.model_json_schema())
            },
            "application/fhir+json": {
                "schema": inline_schema(FhirBundleResponse.model_json_schema())
            },
        },
    }
}


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    operation_id="create_location",
    summary="Create a Location",
    description=(
        "Creates a new Location. Supply `user_id` and `org_id` for tenant scoping. "
        "If `managing_organization` is provided, it must reference an existing organization "
        "in the caller's own tenant. If `part_of` is provided, it must reference an existing "
        "Location in the caller's own tenant. "
        "`created_by` is stamped automatically from the caller's JWT — do not supply it. "
        "Send `Accept: application/fhir+json` to receive the created resource in FHIR R4 format."
    ),
    responses={**_SINGLE_201, **_ERR_VALIDATION, **_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("location", "create"))],
)
async def create_location(
    dto: LocationCreateSchema,
    request: Request,
    actor: AuthUser = Depends(require_permission("location", "create")),
    service: LocationService = Depends(get_location_service),
) -> JSONResponse:
    """Create a new Location. Forwards Accept header for content negotiation."""
    data = await service.create(dto, actor, accept=get_accept_header(request))
    return format_response(data, request)


@router.get(
    "/{location_id}",
    operation_id="get_location",
    summary="Get a Location by ID",
    description=(
        "Retrieves a single Location by its public integer ID, scoped to the caller's "
        "organization. Send `Accept: application/fhir+json` to receive the resource in FHIR R4 format."
    ),
    responses={**_SINGLE_200, **_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("location", "read"))],
)
async def get_location(
    location_id: int,
    request: Request,
    actor: AuthUser = Depends(require_permission("location", "read")),
    service: LocationService = Depends(get_location_service),
) -> JSONResponse:
    """Fetch a single Location by ID. Forwards Accept header for content negotiation."""
    data = await service.get_by_id(
        location_id, actor, accept=get_accept_header(request)
    )
    return format_response(data, request)


@router.get(
    "/",
    operation_id="list_locations",
    summary="List Locations",
    description=(
        "Returns a paginated list of Locations. Filter by `org_id` (tenant scoping) and "
        "`status` (active | suspended | inactive). Use `limit` and `offset` for pagination. "
        "Send `Accept: application/fhir+json` to receive results as a FHIR Bundle searchset."
    ),
    responses={**_LIST_200},
    dependencies=[Depends(require_permission("location", "read"))],
)
async def list_locations(
    request: Request,
    filters: ListLocationsSchema = Depends(),
    actor: AuthUser = Depends(require_permission("location", "read")),
    service: LocationService = Depends(get_location_service),
) -> JSONResponse:
    """List Locations with optional filters."""
    data = await service.list(filters, actor, accept=get_accept_header(request))
    return format_paginated_response(data, request)


@router.patch(
    "/{location_id}",
    operation_id="update_location",
    summary="Partially update a Location",
    description=(
        "Updates specific scalar fields on a Location. At least one field must be provided. "
        "Array sub-resources (identifiers, types, telecoms, hours_of_operation, endpoints) are "
        "not patchable — delete and re-create to correct those. "
        "`part_of` (re-parenting) and `managing_organization` are patchable here, unlike "
        "Organization's immutable `partof` — both are re-validated for existence and tenant "
        "match, and `part_of` is additionally checked to avoid creating a circular hierarchy "
        "(409). Scoped to the caller's organization. "
        "Send `Accept: application/fhir+json` to receive the updated resource in FHIR R4 format."
    ),
    responses={**_SINGLE_200, **_ERR_NOT_FOUND, **_ERR_VALIDATION, **_ERR_CONFLICT},
    dependencies=[Depends(require_permission("location", "update"))],
)
async def update_location(
    location_id: int,
    dto: LocationPatchSchema,
    request: Request,
    actor: AuthUser = Depends(require_permission("location", "update")),
    service: LocationService = Depends(get_location_service),
) -> JSONResponse:
    """Partially update a Location. Forwards Accept header for content negotiation."""
    data = await service.update(
        location_id, dto, actor, accept=get_accept_header(request)
    )
    return format_response(data, request)


@router.delete(
    "/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_location",
    summary="Delete a Location",
    description=(
        "Permanently deletes the Location and all its associated child records, scoped to "
        "the caller's organization. This operation is irreversible."
    ),
    responses={**_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("location", "delete"))],
)
async def delete_location(
    location_id: int,
    actor: AuthUser = Depends(require_permission("location", "delete")),
    service: LocationService = Depends(get_location_service),
) -> None:
    """Delete a Location. No content negotiation — DELETE returns 204 with no body."""
    await service.delete(location_id, actor)
