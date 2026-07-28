import strawberry

from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.slot.types.input import SlotCreateInput, SlotGenerateInput, SlotPatchInput
from app.gql.slot.types.types import SlotGenerateResultType, SlotType
from app.schemas.slot.response import SlotGenerateResponse, SlotResponse


def _to_slot_type(data: dict) -> SlotType:
    """Shared conversion: raw fhir-server dict -> validated SlotResponse -> SlotType."""
    return SlotType.from_pydantic(SlotResponse.model_validate(data))


def _to_generate_result_type(data: dict) -> SlotGenerateResultType:
    """Shared conversion: raw generation-result dict -> validated SlotGenerateResponse -> SlotGenerateResultType."""
    return SlotGenerateResultType.from_pydantic(SlotGenerateResponse.model_validate(data))


@strawberry.type(description="Mutation fields for the Slot resource.")
class SlotMutation:
    """Mutation fields for the Slot resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description=(
            "Create a single Slot manually. `schedule` must reference an existing Schedule in "
            "the caller's own tenant. If `serviceCategory`/`serviceType`/`specialty` are "
            "omitted, they default from the parent Schedule's own stored values. `createdBy` is "
            "stamped automatically from the caller's JWT. Requires the `slot:create` permission."
        )
    )
    @translate_errors
    async def create_slot(self, info: strawberry.types.Info, input: SlotCreateInput) -> SlotType:
        """Create a new Slot — mirrors POST /slots/, including schedule validation and service-field defaulting in SlotService."""
        actor = require_gql_permission(info, "slot", "create")
        service = get_container(info).slot.slot_service()
        dto = input.to_pydantic()
        data = await service.create(dto, actor)
        return _to_slot_type(data)

    @strawberry.mutation(
        description=(
            "Partially update a Slot's `status`, `start`, `end`, `overbooked`, `comment`, or "
            "`appointmentType*` fields. `schedule` and sub-resource arrays are not patchable "
            "here (delete and re-create). `updatedBy` is stamped automatically from the "
            "caller's JWT. Requires the `slot:update` permission."
        )
    )
    @translate_errors
    async def update_slot(self, info: strawberry.types.Info, slot_id: int, input: SlotPatchInput) -> SlotType:
        """Partially update a Slot — mirrors PATCH /slots/{id}."""
        actor = require_gql_permission(info, "slot", "update")
        service = get_container(info).slot.slot_service()
        dto = input.to_pydantic()
        data = await service.update(slot_id, dto, actor)
        return _to_slot_type(data)

    @strawberry.mutation(
        description=(
            "Permanently delete a Slot. Irreversible. Requires the `slot:delete` permission. "
            "Returns true on success."
        )
    )
    @translate_errors
    async def delete_slot(self, info: strawberry.types.Info, slot_id: int) -> bool:
        """Delete a Slot — mirrors DELETE /slots/{id}. Returns true on success."""
        actor = require_gql_permission(info, "slot", "delete")
        service = get_container(info).slot.slot_service()
        await service.delete(slot_id, actor)
        return True

    @strawberry.mutation(
        description=(
            "Availability-aware bulk Slot generation. The Schedule's actor must be a "
            "PractitionerRole with declared `availability` — Slots are only created inside its "
            "declared weekly hours, for matching days within `generationStart`/`generationEnd`, "
            "excluding declared leave periods and any window overlapping an already-existing "
            "Slot (safe to re-call to extend a date range). Requires the `slot:create` permission."
        )
    )
    @translate_errors
    async def generate_slots(self, info: strawberry.types.Info, input: SlotGenerateInput) -> SlotGenerateResultType:
        """Bulk-generate Slots for a Schedule — mirrors POST /slots/generate."""
        actor = require_gql_permission(info, "slot", "create")
        service = get_container(info).slot.slot_service()
        dto = input.to_pydantic()
        result = await service.generate(dto, actor)
        return _to_generate_result_type(result)
