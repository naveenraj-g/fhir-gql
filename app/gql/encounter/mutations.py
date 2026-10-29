"""
Mutation fields for the Encounter resource — same genuinely FHIR
R4-shaped input/output regardless of which connector (internal, medplum,
...) is actually active; each connector's translator maps this shape onto
its own write conventions. Mirrors app.gql.organization.mutations/.../
app.gql.appointment_response.mutations exactly — see those modules and
app.gql.organization's package docstring, and
app.connectors.base.EncounterWireTranslator's docstring for why write
translation is NOT a pass-through for `internal` the way reads are.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_encounter_translator
from app.fhir.schemas.encounter import FhirEncounterResponse
from app.gql.context import get_container
from app.gql.encounter.types.input import FhirEncounterInput
from app.gql.encounter.types.response import FhirEncounterType
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission


@strawberry.type(description="Mutation fields for the Encounter resource.")
class FhirEncounterMutation:
    """Mutation fields for the Encounter resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description=(
            "Create a new Encounter from a genuine FHIR R4 payload. "
            "Requires the `encounter:create` permission."
        )
    )
    @translate_errors
    async def create_fhir_encounter(
        self,
        info: strawberry.types.Info,
        input: Annotated[
            FhirEncounterInput,
            strawberry.argument(
                description="The Encounter to create, in FHIR R4 shape."
            ),
        ],
    ) -> FhirEncounterType:
        """Create a new Encounter — mirrors POST /Encounter."""
        actor = require_gql_permission(info, "encounter", "create")
        connector = get_container(info).core.fhir_client()
        translator = active_encounter_translator()
        # by_alias=True: FhirEncounterInput's `class_` field (Python
        # reserves `class`) is aliased back to the real FHIR key `class`
        # before either translator ever sees the dict.
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json", by_alias=True)
        raw = await connector.post(
            translator.list_path(),
            translator.to_wire_create(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirEncounterType.from_pydantic(
            FhirEncounterResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Partially update an Encounter from a genuine FHIR R4 payload "
            "— only supplied fields are written. Requires the "
            "`encounter:update` permission."
        )
    )
    @translate_errors
    async def update_fhir_encounter(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
        input: Annotated[
            FhirEncounterInput,
            strawberry.argument(description="Fields to update, in FHIR R4 shape."),
        ],
    ) -> FhirEncounterType:
        """Update an Encounter by FHIR id — mirrors PATCH /Encounter/{id}."""
        actor = require_gql_permission(info, "encounter", "update")
        connector = get_container(info).core.fhir_client()
        translator = active_encounter_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json", by_alias=True)
        raw = await connector.patch(
            translator.item_path(id),
            translator.to_wire_patch(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirEncounterType.from_pydantic(
            FhirEncounterResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Permanently delete an Encounter by its FHIR resource id. "
            "Irreversible. Requires the `encounter:delete` permission. "
            "Returns true on success."
        )
    )
    @translate_errors
    async def delete_fhir_encounter(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> bool:
        """Delete an Encounter by FHIR id — mirrors DELETE /Encounter/{id}."""
        actor = require_gql_permission(info, "encounter", "delete")
        connector = get_container(info).core.fhir_client()
        translator = active_encounter_translator()
        await connector.delete(translator.item_path(id), actor=actor)
        return True
