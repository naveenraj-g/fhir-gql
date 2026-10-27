"""
Mutation fields for the Slot resource — same genuinely FHIR R4-shaped
input/output regardless of which connector (internal, medplum, ...) is
actually active; each connector's translator maps this shape onto its own
write conventions. Mirrors app.gql.organization.mutations/
app.gql.location.mutations/app.gql.healthcare_service.mutations/
app.gql.practitioner.mutations/app.gql.practitioner_role.mutations/
app.gql.schedule.mutations exactly — see those modules and
app.gql.organization's package docstring, and
app.connectors.base.SlotWireTranslator's docstring for why write
translation is NOT a pass-through for `internal` the way reads are.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_slot_translator
from app.fhir.schemas.slot import FhirSlotResponse
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.slot.types.input import FhirSlotInput
from app.gql.slot.types.response import FhirSlotType


@strawberry.type(description="Mutation fields for the Slot resource.")
class FhirSlotMutation:
    """Mutation fields for the Slot resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description=(
            "Create a new Slot from a genuine FHIR R4 payload. Requires "
            "the `slot:create` permission."
        )
    )
    @translate_errors
    async def create_fhir_slot(
        self,
        info: strawberry.types.Info,
        input: Annotated[
            FhirSlotInput,
            strawberry.argument(description="The Slot to create, in FHIR R4 shape."),
        ],
    ) -> FhirSlotType:
        """Create a new Slot — mirrors POST /Slot."""
        actor = require_gql_permission(info, "slot", "create")
        connector = get_container(info).core.fhir_client()
        translator = active_slot_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.post(
            translator.list_path(),
            translator.to_wire_create(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirSlotType.from_pydantic(
            FhirSlotResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Partially update a Slot from a genuine FHIR R4 payload — "
            "only supplied fields are written. Requires the "
            "`slot:update` permission."
        )
    )
    @translate_errors
    async def update_fhir_slot(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
        input: Annotated[
            FhirSlotInput,
            strawberry.argument(description="Fields to update, in FHIR R4 shape."),
        ],
    ) -> FhirSlotType:
        """Update a Slot by FHIR id — mirrors PATCH /Slot/{id}."""
        actor = require_gql_permission(info, "slot", "update")
        connector = get_container(info).core.fhir_client()
        translator = active_slot_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.patch(
            translator.item_path(id),
            translator.to_wire_patch(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirSlotType.from_pydantic(
            FhirSlotResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Permanently delete a Slot by its FHIR resource id. "
            "Irreversible. Requires the `slot:delete` permission. Returns "
            "true on success."
        )
    )
    @translate_errors
    async def delete_fhir_slot(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> bool:
        """Delete a Slot by FHIR id — mirrors DELETE /Slot/{id}."""
        actor = require_gql_permission(info, "slot", "delete")
        connector = get_container(info).core.fhir_client()
        translator = active_slot_translator()
        await connector.delete(translator.item_path(id), actor=actor)
        return True
