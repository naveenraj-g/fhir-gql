from datetime import datetime
from typing import Optional

import strawberry

from app.gql.context import get_container
from app.gql.enums import SlotStatusEnum
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.slot.types.types import PaginatedSlotType, SlotType
from app.schemas.slot.input import ListSlotsSchema
from app.schemas.slot.response import PaginatedSlotResponse, SlotResponse


def _to_slot_type(data: dict) -> SlotType:
    """Shared conversion: raw fhir-server dict -> validated SlotResponse -> SlotType."""
    return SlotType.from_pydantic(SlotResponse.model_validate(data))


def _to_paginated_slot_type(data: dict) -> PaginatedSlotType:
    """Shared conversion: raw fhir-server dict -> validated PaginatedSlotResponse -> PaginatedSlotType."""
    return PaginatedSlotType.from_pydantic(PaginatedSlotResponse.model_validate(data))


@strawberry.type(description="Query fields for the Slot resource.")
class SlotQuery:
    """Query fields for the Slot resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(description="Fetch a single Slot by its integer ID. Requires the `slot:read` permission.")
    @translate_errors
    async def slot(self, info: strawberry.types.Info, slot_id: int) -> SlotType:
        """Fetch a single Slot by its integer ID — mirrors GET /slots/{id}."""
        actor = require_gql_permission(info, "slot", "read")
        service = get_container(info).slot.slot_service()
        data = await service.get_by_id(slot_id, actor)
        return _to_slot_type(data)

    @strawberry.field(
        description=(
            "List Slots, optionally filtered by `status`, `scheduleId`, `startAfter`/`startBefore`, "
            "`userId`, or `orgId`, with `limit`/`offset` pagination (default limit 20, max 200). "
            "Requires the `slot:read` permission."
        )
    )
    @translate_errors
    async def slots(
        self,
        info: strawberry.types.Info,
        status: Optional[SlotStatusEnum] = None,  # type: ignore[valid-type]
        schedule_id: Optional[int] = None,
        start_after: Optional[datetime] = None,
        start_before: Optional[datetime] = None,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedSlotType:
        """List Slots with optional filters — mirrors GET /slots/."""
        actor = require_gql_permission(info, "slot", "read")
        service = get_container(info).slot.slot_service()
        filters = ListSlotsSchema(
            status=status,
            schedule_id=schedule_id,
            start_after=start_after,
            start_before=start_before,
            user_id=user_id,
            org_id=org_id,
            limit=limit,
            offset=offset,
        )
        data = await service.list(filters, actor)
        return _to_paginated_slot_type(data)
