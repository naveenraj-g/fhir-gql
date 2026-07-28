"""
API router for FHIR Schedule resources.

Exposes CRUD endpoints under /schedules:
    POST   /schedules/                — create a new Schedule
    GET    /schedules/{schedule_id}   — fetch a single Schedule by ID
    GET    /schedules/                — paginated list with filters
    PATCH  /schedules/{schedule_id}   — partial update (scalar fields only)
    DELETE /schedules/{schedule_id}   — permanent delete

Unlike the sibling project this was ported from, `serviceCategory`/
`serviceType`/`specialty` are NOT accepted on create — they're derived by
ScheduleService from whichever PractitionerRole/HealthcareService actors
are attached, and `actor` is required (at least one entry, including at
least one PractitionerRole or HealthcareService). A Schedule belongs to at
most one provider: at most one Practitioner/PractitionerRole actor is
allowed, and Patient actors can't be mixed with provider actors — see
app/services/schedule_service.py's docstring for the full reasoning.

Content negotiation:
  Accept: application/json         → plain snake_case JSON (default)
  Accept: application/fhir+json    → FHIR R4 resource / Bundle

RBAC: all endpoints require the "schedule" permission resource.
"""

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.auth.models import AuthUser
from app.auth.rbac import require_permission
from app.core.content_negotiation import format_paginated_response, format_response, get_accept_header
from app.core.schema_utils import inline_schema
from app.di.dependencies.schedule import get_schedule_service
from app.schemas.schedule.fhir_schemas import FhirBundleResponse, FhirScheduleResponse
from app.schemas.schedule.input import ListSchedulesSchema, ScheduleCreateSchema, SchedulePatchSchema
from app.schemas.schedule.response import PaginatedScheduleResponse, ScheduleResponse
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedules", tags=["Schedules"])

# ── Shared error response dicts ───────────────────────────────────────────────
_ERR_NOT_FOUND = {404: {"description": "Schedule not found"}}
_ERR_VALIDATION = {422: {"description": "Validation error"}}

# ── Dual-format success response dicts for OpenAPI documentation ───────────────

_SINGLE_201 = {
    201: {
        "description": "Schedule created successfully",
        "content": {
            "application/json": {"schema": inline_schema(ScheduleResponse.model_json_schema())},
            "application/fhir+json": {"schema": inline_schema(FhirScheduleResponse.model_json_schema())},
        },
    }
}

_SINGLE_200 = {
    200: {
        "description": "Schedule retrieved/updated successfully",
        "content": {
            "application/json": {"schema": inline_schema(ScheduleResponse.model_json_schema())},
            "application/fhir+json": {"schema": inline_schema(FhirScheduleResponse.model_json_schema())},
        },
    }
}

_LIST_200 = {
    200: {
        "description": "Paginated list of Schedules",
        "content": {
            "application/json": {"schema": inline_schema(PaginatedScheduleResponse.model_json_schema())},
            "application/fhir+json": {"schema": inline_schema(FhirBundleResponse.model_json_schema())},
        },
    }
}


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    operation_id="create_schedule",
    summary="Create a Schedule",
    description=(
        "Creates a new Schedule. `actor` is required — at least one entry, and at least one "
        "must be a `PractitionerRole` or `HealthcareService` reference, since `serviceCategory`/"
        "`serviceType`/`specialty` are NOT accepted here; they're derived automatically from "
        "those actors' own category/type/specialty data. A Schedule belongs to at most one "
        "provider: at most one `Practitioner`/`PractitionerRole` actor is allowed, and `Patient` "
        "actors cannot be mixed with provider actors. Every actor reference is validated for "
        "existence and tenant match where this project has a client for its type "
        "(Practitioner, PractitionerRole, Location, HealthcareService, Patient); "
        "`RelatedPerson`/`Device` references are accepted unvalidated. `created_by` is stamped "
        "automatically from the caller's JWT. Send `Accept: application/fhir+json` to receive "
        "the result in FHIR R4 format."
    ),
    responses={**_SINGLE_201, **_ERR_VALIDATION, **_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("schedule", "create"))],
)
async def create_schedule(
    dto: ScheduleCreateSchema,
    request: Request,
    actor: AuthUser = Depends(require_permission("schedule", "create")),
    service: ScheduleService = Depends(get_schedule_service),
) -> JSONResponse:
    """Create a new Schedule. Forwards Accept header for content negotiation."""
    data = await service.create(dto, actor, accept=get_accept_header(request))
    return format_response(data, request)


@router.get(
    "/{schedule_id}",
    operation_id="get_schedule",
    summary="Get a Schedule by ID",
    description=(
        "Retrieves a single Schedule by its public integer ID. "
        "Send `Accept: application/fhir+json` to receive the resource in FHIR R4 format."
    ),
    responses={**_SINGLE_200, **_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("schedule", "read"))],
)
async def get_schedule(
    schedule_id: int,
    request: Request,
    actor: AuthUser = Depends(require_permission("schedule", "read")),
    service: ScheduleService = Depends(get_schedule_service),
) -> JSONResponse:
    """Fetch a single Schedule by ID. Forwards Accept header for content negotiation."""
    data = await service.get_by_id(schedule_id, actor, accept=get_accept_header(request))
    return format_response(data, request)


@router.get(
    "/",
    operation_id="list_schedules",
    summary="List Schedules",
    description=(
        "Returns a paginated list of Schedules. Filter by `active` status. Use `limit`/`offset` "
        "for pagination. Send `Accept: application/fhir+json` to receive results as a FHIR "
        "Bundle searchset."
    ),
    responses={**_LIST_200},
    dependencies=[Depends(require_permission("schedule", "read"))],
)
async def list_schedules(
    request: Request,
    filters: ListSchedulesSchema = Depends(),
    actor: AuthUser = Depends(require_permission("schedule", "read")),
    service: ScheduleService = Depends(get_schedule_service),
) -> JSONResponse:
    """List Schedules with optional filters."""
    data = await service.list(filters, actor, accept=get_accept_header(request))
    return format_paginated_response(data, request)


@router.patch(
    "/{schedule_id}",
    operation_id="update_schedule",
    summary="Partially update a Schedule",
    description=(
        "Updates `active`, `comment`, `planning_horizon_start`, or `planning_horizon_end` on a "
        "Schedule. At least one field must be provided. `actor` and the derived "
        "`service_category`/`service_type`/`specialty` arrays cannot be patched — delete and "
        "re-create to change those. Send `Accept: application/fhir+json` for FHIR R4 format."
    ),
    responses={**_SINGLE_200, **_ERR_NOT_FOUND, **_ERR_VALIDATION},
    dependencies=[Depends(require_permission("schedule", "update"))],
)
async def update_schedule(
    schedule_id: int,
    dto: SchedulePatchSchema,
    request: Request,
    actor: AuthUser = Depends(require_permission("schedule", "update")),
    service: ScheduleService = Depends(get_schedule_service),
) -> JSONResponse:
    """Partially update a Schedule. Forwards Accept header for content negotiation."""
    data = await service.update(schedule_id, dto, actor, accept=get_accept_header(request))
    return format_response(data, request)


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_schedule",
    summary="Delete a Schedule",
    description="Permanently deletes the Schedule and all its associated Slots. This operation is irreversible.",
    responses={**_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("schedule", "delete"))],
)
async def delete_schedule(
    schedule_id: int,
    actor: AuthUser = Depends(require_permission("schedule", "delete")),
    service: ScheduleService = Depends(get_schedule_service),
) -> None:
    """Delete a Schedule. No content negotiation — DELETE returns 204 with no body."""
    await service.delete(schedule_id, actor)
