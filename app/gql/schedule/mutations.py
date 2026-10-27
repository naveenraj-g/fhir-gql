"""
Mutation fields for the Schedule resource — same genuinely FHIR R4-shaped
input/output regardless of which connector (internal, medplum, ...) is
actually active; each connector's translator maps this shape onto its own
write conventions. Mirrors app.gql.organization.mutations/
app.gql.location.mutations/app.gql.healthcare_service.mutations/
app.gql.practitioner.mutations/app.gql.practitioner_role.mutations exactly
— see those modules and app.gql.organization's package docstring, and
app.connectors.base.ScheduleWireTranslator's docstring for why write
translation is NOT a pass-through for `internal` the way reads are.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_schedule_translator
from app.fhir.schemas.schedule import FhirScheduleResponse
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.schedule.types.input import FhirScheduleInput
from app.gql.schedule.types.response import FhirScheduleType


@strawberry.type(description="Mutation fields for the Schedule resource.")
class FhirScheduleMutation:
    """Mutation fields for the Schedule resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description=(
            "Create a new Schedule from a genuine FHIR R4 payload. "
            "Requires the `schedule:create` permission."
        )
    )
    @translate_errors
    async def create_fhir_schedule(
        self,
        info: strawberry.types.Info,
        input: Annotated[
            FhirScheduleInput,
            strawberry.argument(description="The Schedule to create, in FHIR R4 shape."),
        ],
    ) -> FhirScheduleType:
        """Create a new Schedule — mirrors POST /Schedule."""
        actor = require_gql_permission(info, "schedule", "create")
        connector = get_container(info).core.fhir_client()
        translator = active_schedule_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.post(
            translator.list_path(),
            translator.to_wire_create(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirScheduleType.from_pydantic(
            FhirScheduleResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Partially update a Schedule from a genuine FHIR R4 payload — "
            "only supplied fields are written. Requires the "
            "`schedule:update` permission."
        )
    )
    @translate_errors
    async def update_fhir_schedule(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
        input: Annotated[
            FhirScheduleInput,
            strawberry.argument(description="Fields to update, in FHIR R4 shape."),
        ],
    ) -> FhirScheduleType:
        """Update a Schedule by FHIR id — mirrors PATCH /Schedule/{id}."""
        actor = require_gql_permission(info, "schedule", "update")
        connector = get_container(info).core.fhir_client()
        translator = active_schedule_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.patch(
            translator.item_path(id),
            translator.to_wire_patch(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirScheduleType.from_pydantic(
            FhirScheduleResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Permanently delete a Schedule by its FHIR resource id. "
            "Irreversible. Requires the `schedule:delete` permission. "
            "Returns true on success."
        )
    )
    @translate_errors
    async def delete_fhir_schedule(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> bool:
        """Delete a Schedule by FHIR id — mirrors DELETE /Schedule/{id}."""
        actor = require_gql_permission(info, "schedule", "delete")
        connector = get_container(info).core.fhir_client()
        translator = active_schedule_translator()
        await connector.delete(translator.item_path(id), actor=actor)
        return True
