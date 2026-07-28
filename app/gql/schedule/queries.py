from typing import Optional

import strawberry

from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.schedule.types.types import PaginatedScheduleType, ScheduleType
from app.schemas.schedule.input import ListSchedulesSchema
from app.schemas.schedule.response import PaginatedScheduleResponse, ScheduleResponse


def _to_schedule_type(data: dict) -> ScheduleType:
    """Shared conversion: raw fhir-server dict -> validated ScheduleResponse -> ScheduleType."""
    return ScheduleType.from_pydantic(ScheduleResponse.model_validate(data))


def _to_paginated_schedule_type(data: dict) -> PaginatedScheduleType:
    """Shared conversion: raw fhir-server dict -> validated PaginatedScheduleResponse -> PaginatedScheduleType."""
    return PaginatedScheduleType.from_pydantic(PaginatedScheduleResponse.model_validate(data))


@strawberry.type(description="Query fields for the Schedule resource.")
class ScheduleQuery:
    """Query fields for the Schedule resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single Schedule by its integer ID, including all sub-resource arrays. Requires the `schedule:read` permission."
    )
    @translate_errors
    async def schedule(self, info: strawberry.types.Info, schedule_id: int) -> ScheduleType:
        """Fetch a single Schedule by its integer ID — mirrors GET /schedules/{id}."""
        actor = require_gql_permission(info, "schedule", "read")
        service = get_container(info).schedule.schedule_service()
        data = await service.get_by_id(schedule_id, actor)
        return _to_schedule_type(data)

    @strawberry.field(
        description=(
            "List Schedules, optionally filtered by `active` status, with `limit`/`offset` "
            "pagination (default limit 20, max 200). Requires the `schedule:read` permission."
        )
    )
    @translate_errors
    async def schedules(
        self,
        info: strawberry.types.Info,
        active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedScheduleType:
        """List Schedules with optional filters — mirrors GET /schedules/."""
        actor = require_gql_permission(info, "schedule", "read")
        service = get_container(info).schedule.schedule_service()
        filters = ListSchedulesSchema(active=active, limit=limit, offset=offset)
        data = await service.list(filters, actor)
        return _to_paginated_schedule_type(data)
