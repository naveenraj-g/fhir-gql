import strawberry

from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.schedule.types.input import ScheduleCreateInput, SchedulePatchInput
from app.gql.schedule.types.types import ScheduleType
from app.schemas.schedule.response import ScheduleResponse


def _to_schedule_type(data: dict) -> ScheduleType:
    """Shared conversion: raw fhir-server dict -> validated ScheduleResponse -> ScheduleType."""
    return ScheduleType.from_pydantic(ScheduleResponse.model_validate(data))


@strawberry.type(description="Mutation fields for the Schedule resource.")
class ScheduleMutation:
    """Mutation fields for the Schedule resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description=(
            "Create a new Schedule. `actor` is required (at least one entry, including at least "
            "one PractitionerRole or HealthcareService) — `serviceCategory`/`serviceType`/"
            "`specialty` are derived automatically from those actors, not accepted as input. A "
            "Schedule belongs to at most one provider: at most one Practitioner/PractitionerRole "
            "actor is allowed, and Patient actors cannot be mixed with provider actors. "
            "`createdBy` is stamped automatically from the caller's JWT. Requires the "
            "`schedule:create` permission."
        )
    )
    @translate_errors
    async def create_schedule(self, info: strawberry.types.Info, input: ScheduleCreateInput) -> ScheduleType:
        """Create a new Schedule — mirrors POST /schedules/, including actor validation and service-field derivation in ScheduleService."""
        actor = require_gql_permission(info, "schedule", "create")
        service = get_container(info).schedule.schedule_service()
        dto = input.to_pydantic()
        data = await service.create(dto, actor)
        return _to_schedule_type(data)

    @strawberry.mutation(
        description=(
            "Partially update a Schedule's `active`, `comment`, `planningHorizonStart`, or "
            "`planningHorizonEnd` fields. `actor` and the derived serviceCategory/serviceType/"
            "specialty arrays are not patchable here (delete and re-create). `updatedBy` is "
            "stamped automatically from the caller's JWT. Requires the `schedule:update` permission."
        )
    )
    @translate_errors
    async def update_schedule(self, info: strawberry.types.Info, schedule_id: int, input: SchedulePatchInput) -> ScheduleType:
        """Partially update a Schedule — mirrors PATCH /schedules/{id}."""
        actor = require_gql_permission(info, "schedule", "update")
        service = get_container(info).schedule.schedule_service()
        dto = input.to_pydantic()
        data = await service.update(schedule_id, dto, actor)
        return _to_schedule_type(data)

    @strawberry.mutation(
        description=(
            "Permanently delete a Schedule and all its associated Slots. Irreversible. Requires "
            "the `schedule:delete` permission. Returns true on success."
        )
    )
    @translate_errors
    async def delete_schedule(self, info: strawberry.types.Info, schedule_id: int) -> bool:
        """Delete a Schedule — mirrors DELETE /schedules/{id}. Returns true on success."""
        actor = require_gql_permission(info, "schedule", "delete")
        service = get_container(info).schedule.schedule_service()
        await service.delete(schedule_id, actor)
        return True
