"""
API router for FHIR Slot resources.

Exposes CRUD endpoints under /slots, plus availability-aware bulk generation:
    POST   /slots/generate    — bulk-generate Slots from a Schedule's PractitionerRole availability
    POST   /slots/            — create a single Slot manually
    GET    /slots/{slot_id}   — fetch a single Slot by ID
    GET    /slots/            — paginated list with filters
    PATCH  /slots/{slot_id}   — partial update (scalar fields only)
    DELETE /slots/{slot_id}   — permanent delete

Route ordering is critical: /generate must appear before /{slot_id} so
FastAPI does not attempt to cast the literal string "generate" as an integer.

Content negotiation:
  Accept: application/json         → plain snake_case JSON (default)
  Accept: application/fhir+json    → FHIR R4 resource / Bundle (not applicable to /generate,
                                      which always returns a plain generation-result summary)

RBAC: all endpoints require the "slot" permission resource.

Reference validation and defaults: `schedule` is validated for existence
and tenant match on manual create; `service_category`/`service_type`/
`specialty` default from the parent Schedule's own stored values when
omitted — see app/services/slot_service.py's docstring for the full
generate() algorithm.
"""

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.auth.models import AuthUser
from app.auth.rbac import require_permission
from app.core.content_negotiation import format_paginated_response, format_response, get_accept_header
from app.core.schema_utils import inline_schema
from app.di.dependencies.slot import get_slot_service
from app.schemas.slot.fhir_schemas import FhirBundleResponse, FhirSlotResponse
from app.schemas.slot.input import ListSlotsSchema, SlotCreateSchema, SlotGenerateSchema, SlotPatchSchema
from app.schemas.slot.response import PaginatedSlotResponse, SlotGenerateResponse, SlotResponse
from app.services.slot_service import SlotService

router = APIRouter(prefix="/slots", tags=["Slots"])

# ── Shared error response dicts ───────────────────────────────────────────────
_ERR_NOT_FOUND = {404: {"description": "Slot or Schedule not found"}}
_ERR_VALIDATION = {422: {"description": "Validation error"}}

# ── Dual-format success response dicts for OpenAPI documentation ───────────────

_SINGLE_201 = {
    201: {
        "description": "Slot created successfully",
        "content": {
            "application/json": {"schema": inline_schema(SlotResponse.model_json_schema())},
            "application/fhir+json": {"schema": inline_schema(FhirSlotResponse.model_json_schema())},
        },
    }
}

_SINGLE_200 = {
    200: {
        "description": "Slot retrieved/updated successfully",
        "content": {
            "application/json": {"schema": inline_schema(SlotResponse.model_json_schema())},
            "application/fhir+json": {"schema": inline_schema(FhirSlotResponse.model_json_schema())},
        },
    }
}

_LIST_200 = {
    200: {
        "description": "Paginated list of Slots",
        "content": {
            "application/json": {"schema": inline_schema(PaginatedSlotResponse.model_json_schema())},
            "application/fhir+json": {"schema": inline_schema(FhirBundleResponse.model_json_schema())},
        },
    }
}

_GENERATE_200 = {
    200: {
        "description": "Slot generation result",
        "content": {"application/json": {"schema": inline_schema(SlotGenerateResponse.model_json_schema())}},
    }
}


@router.post(
    "/generate",
    operation_id="generate_slots",
    summary="Bulk-generate Slots from a Schedule's availability",
    description=(
        "Availability-aware bulk Slot generation. The Schedule's provider actor must be a "
        "PractitionerRole with at least one `availability[].available_times` entry declared — "
        "Slots are only created inside those declared weekly windows, for matching days within "
        "`generation_start`/`generation_end`, excluding declared `not_available_times` periods "
        "and any window that overlaps an already-existing Slot (safe to re-call to extend a "
        "date range). `generation_start`/`generation_end` are clamped/validated against the "
        "Schedule's own `planning_horizon`. `service_category`/`service_type`/`specialty` "
        "default from the Schedule's own stored values unless overridden here."
    ),
    responses={**_GENERATE_200, **_ERR_VALIDATION, **_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("slot", "create"))],
)
async def generate_slots(
    dto: SlotGenerateSchema,
    actor: AuthUser = Depends(require_permission("slot", "create")),
    service: SlotService = Depends(get_slot_service),
) -> dict:
    """Bulk-generate Slots for a Schedule. Returns a plain JSON generation-result summary (no content negotiation)."""
    return await service.generate(dto, actor)


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    operation_id="create_slot",
    summary="Create a Slot",
    description=(
        "Creates a single Slot manually. `schedule` must reference an existing Schedule in the "
        "caller's own tenant. If `service_category`/`service_type`/`specialty` are omitted, they "
        "default from the parent Schedule's own stored values. `created_by` is stamped "
        "automatically from the caller's JWT. Send `Accept: application/fhir+json` to receive "
        "the result in FHIR R4 format."
    ),
    responses={**_SINGLE_201, **_ERR_VALIDATION, **_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("slot", "create"))],
)
async def create_slot(
    dto: SlotCreateSchema,
    request: Request,
    actor: AuthUser = Depends(require_permission("slot", "create")),
    service: SlotService = Depends(get_slot_service),
) -> JSONResponse:
    """Create a new Slot. Forwards Accept header for content negotiation."""
    data = await service.create(dto, actor, accept=get_accept_header(request))
    return format_response(data, request)


@router.get(
    "/{slot_id}",
    operation_id="get_slot",
    summary="Get a Slot by ID",
    description=(
        "Retrieves a single Slot by its public integer ID. "
        "Send `Accept: application/fhir+json` to receive the resource in FHIR R4 format."
    ),
    responses={**_SINGLE_200, **_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("slot", "read"))],
)
async def get_slot(
    slot_id: int,
    request: Request,
    actor: AuthUser = Depends(require_permission("slot", "read")),
    service: SlotService = Depends(get_slot_service),
) -> JSONResponse:
    """Fetch a single Slot by ID. Forwards Accept header for content negotiation."""
    data = await service.get_by_id(slot_id, actor, accept=get_accept_header(request))
    return format_response(data, request)


@router.get(
    "/",
    operation_id="list_slots",
    summary="List Slots",
    description=(
        "Returns a paginated list of Slots. Filter by `status`, `schedule_id`, `start_after`/"
        "`start_before`, `user_id`, or `org_id`. Use `limit`/`offset` for pagination. "
        "Send `Accept: application/fhir+json` to receive results as a FHIR Bundle searchset."
    ),
    responses={**_LIST_200},
    dependencies=[Depends(require_permission("slot", "read"))],
)
async def list_slots(
    request: Request,
    filters: ListSlotsSchema = Depends(),
    actor: AuthUser = Depends(require_permission("slot", "read")),
    service: SlotService = Depends(get_slot_service),
) -> JSONResponse:
    """List Slots with optional filters."""
    data = await service.list(filters, actor, accept=get_accept_header(request))
    return format_paginated_response(data, request)


@router.patch(
    "/{slot_id}",
    operation_id="update_slot",
    summary="Partially update a Slot",
    description=(
        "Updates `status`, `start`, `end`, `overbooked`, `comment`, or `appointment_type_*` on a "
        "Slot. At least one field must be provided. `schedule` and the sub-resource arrays "
        "cannot be patched — delete and re-create to change those. Send "
        "`Accept: application/fhir+json` for FHIR R4 format."
    ),
    responses={**_SINGLE_200, **_ERR_NOT_FOUND, **_ERR_VALIDATION},
    dependencies=[Depends(require_permission("slot", "update"))],
)
async def update_slot(
    slot_id: int,
    dto: SlotPatchSchema,
    request: Request,
    actor: AuthUser = Depends(require_permission("slot", "update")),
    service: SlotService = Depends(get_slot_service),
) -> JSONResponse:
    """Partially update a Slot. Forwards Accept header for content negotiation."""
    data = await service.update(slot_id, dto, actor, accept=get_accept_header(request))
    return format_response(data, request)


@router.delete(
    "/{slot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_slot",
    summary="Delete a Slot",
    description="Permanently deletes the Slot. This operation is irreversible.",
    responses={**_ERR_NOT_FOUND},
    dependencies=[Depends(require_permission("slot", "delete"))],
)
async def delete_slot(
    slot_id: int,
    actor: AuthUser = Depends(require_permission("slot", "delete")),
    service: SlotService = Depends(get_slot_service),
) -> None:
    """Delete a Slot. No content negotiation — DELETE returns 204 with no body."""
    await service.delete(slot_id, actor)
