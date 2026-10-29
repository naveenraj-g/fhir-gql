"""
Mutation fields for the Appointment resource — same genuinely FHIR
R4-shaped input/output regardless of which connector (internal, medplum,
...) is actually active; each connector's translator maps this shape onto
its own write conventions. Mirrors app.gql.organization.mutations/.../
app.gql.slot.mutations exactly — see those modules and
app.gql.organization's package docstring, and
app.connectors.base.AppointmentWireTranslator's docstring for why write
translation is NOT a pass-through for `internal` the way reads are.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_appointment_translator
from app.fhir.schemas.appointment import FhirAppointmentResponse
from app.gql.appointment.types.input import FhirAppointmentInput
from app.gql.appointment.types.response import FhirAppointmentType
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission


@strawberry.type(description="Mutation fields for the Appointment resource.")
class FhirAppointmentMutation:
    """Mutation fields for the Appointment resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description=(
            "Create a new Appointment from a genuine FHIR R4 payload. "
            "Requires the `appointment:create` permission."
        )
    )
    @translate_errors
    async def create_fhir_appointment(
        self,
        info: strawberry.types.Info,
        input: Annotated[
            FhirAppointmentInput,
            strawberry.argument(
                description="The Appointment to create, in FHIR R4 shape."
            ),
        ],
    ) -> FhirAppointmentType:
        """Create a new Appointment — mirrors POST /Appointment."""
        actor = require_gql_permission(info, "appointment", "create")
        connector = get_container(info).core.fhir_client()
        translator = active_appointment_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.post(
            translator.list_path(),
            translator.to_wire_create(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirAppointmentType.from_pydantic(
            FhirAppointmentResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Partially update an Appointment from a genuine FHIR R4 "
            "payload — only supplied fields are written. Requires the "
            "`appointment:update` permission."
        )
    )
    @translate_errors
    async def update_fhir_appointment(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
        input: Annotated[
            FhirAppointmentInput,
            strawberry.argument(description="Fields to update, in FHIR R4 shape."),
        ],
    ) -> FhirAppointmentType:
        """Update an Appointment by FHIR id — mirrors PATCH /Appointment/{id}."""
        actor = require_gql_permission(info, "appointment", "update")
        connector = get_container(info).core.fhir_client()
        translator = active_appointment_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.patch(
            translator.item_path(id),
            translator.to_wire_patch(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirAppointmentType.from_pydantic(
            FhirAppointmentResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Permanently delete an Appointment by its FHIR resource id. "
            "Irreversible. Requires the `appointment:delete` permission. "
            "Returns true on success."
        )
    )
    @translate_errors
    async def delete_fhir_appointment(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> bool:
        """Delete an Appointment by FHIR id — mirrors DELETE /Appointment/{id}."""
        actor = require_gql_permission(info, "appointment", "delete")
        connector = get_container(info).core.fhir_client()
        translator = active_appointment_translator()
        await connector.delete(translator.item_path(id), actor=actor)
        return True
