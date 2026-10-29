"""
Mutation fields for the AppointmentResponse resource — same genuinely
FHIR R4-shaped input/output regardless of which connector (internal,
medplum, ...) is actually active; each connector's translator maps this
shape onto its own write conventions. Mirrors
app.gql.organization.mutations/.../app.gql.appointment.mutations exactly
— see those modules and app.gql.organization's package docstring, and
app.connectors.base.AppointmentResponseWireTranslator's docstring for why
write translation is NOT a pass-through for `internal` the way reads are.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_appointment_response_translator
from app.fhir.schemas.appointment_response import FhirAppointmentResponseResponse
from app.gql.appointment_response.types.input import FhirAppointmentResponseInput
from app.gql.appointment_response.types.response import FhirAppointmentResponseType
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission


@strawberry.type(description="Mutation fields for the AppointmentResponse resource.")
class FhirAppointmentResponseMutation:
    """Mutation fields for the AppointmentResponse resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description=(
            "Create a new AppointmentResponse from a genuine FHIR R4 "
            "payload. Requires the `appointment_response:create` "
            "permission."
        )
    )
    @translate_errors
    async def create_fhir_appointment_response(
        self,
        info: strawberry.types.Info,
        input: Annotated[
            FhirAppointmentResponseInput,
            strawberry.argument(
                description="The AppointmentResponse to create, in FHIR R4 shape."
            ),
        ],
    ) -> FhirAppointmentResponseType:
        """Create a new AppointmentResponse — mirrors POST /AppointmentResponse."""
        actor = require_gql_permission(info, "appointment_response", "create")
        connector = get_container(info).core.fhir_client()
        translator = active_appointment_response_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.post(
            translator.list_path(),
            translator.to_wire_create(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirAppointmentResponseType.from_pydantic(
            FhirAppointmentResponseResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Partially update an AppointmentResponse from a genuine FHIR "
            "R4 payload — only supplied fields are written. Requires the "
            "`appointment_response:update` permission."
        )
    )
    @translate_errors
    async def update_fhir_appointment_response(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
        input: Annotated[
            FhirAppointmentResponseInput,
            strawberry.argument(description="Fields to update, in FHIR R4 shape."),
        ],
    ) -> FhirAppointmentResponseType:
        """Update an AppointmentResponse by FHIR id — mirrors PATCH /AppointmentResponse/{id}."""
        actor = require_gql_permission(info, "appointment_response", "update")
        connector = get_container(info).core.fhir_client()
        translator = active_appointment_response_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.patch(
            translator.item_path(id),
            translator.to_wire_patch(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirAppointmentResponseType.from_pydantic(
            FhirAppointmentResponseResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Permanently delete an AppointmentResponse by its FHIR "
            "resource id. Irreversible. Requires the "
            "`appointment_response:delete` permission. Returns true on "
            "success."
        )
    )
    @translate_errors
    async def delete_fhir_appointment_response(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> bool:
        """Delete an AppointmentResponse by FHIR id — mirrors DELETE /AppointmentResponse/{id}."""
        actor = require_gql_permission(info, "appointment_response", "delete")
        connector = get_container(info).core.fhir_client()
        translator = active_appointment_response_translator()
        await connector.delete(translator.item_path(id), actor=actor)
        return True
