"""
Query fields for the AppointmentResponse resource — one canonical,
genuinely FHIR R4-shaped AppointmentResponse regardless of which connector
(internal, medplum, ...) is actually active. Mirrors
app.gql.organization.queries/.../app.gql.appointment.queries exactly —
see those modules and app.gql.organization's package docstring for the
overall idea.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_appointment_response_translator
from app.fhir.schemas.appointment_response import FhirAppointmentResponseResponse
from app.gql.appointment_response.types.response import FhirAppointmentResponseType
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission


def _entries_from_bundle(bundle: dict) -> list[dict]:
    """A FHIR search response is a Bundle regardless of backend — pull out
    each entry's resource. Falls back to treating the response itself as a
    single resource if it isn't a Bundle (defensive; both of today's
    connectors always return a Bundle for a collection GET)."""
    if bundle.get("resourceType") == "Bundle":
        return [entry["resource"] for entry in bundle.get("entry") or []]
    return [bundle]


@strawberry.type(description="Query fields for the AppointmentResponse resource.")
class FhirAppointmentResponseQuery:
    """Query fields for the AppointmentResponse resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single AppointmentResponse by its FHIR resource id, in genuine FHIR R4 shape. Requires the `appointment_response:read` permission."
    )
    @translate_errors
    async def get_fhir_appointment_response(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> FhirAppointmentResponseType:
        """Fetch a single AppointmentResponse by FHIR id — mirrors GET /AppointmentResponse/{id}."""
        actor = require_gql_permission(info, "appointment_response", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_appointment_response_translator()
        raw = await connector.get(
            translator.item_path(id), accept=translator.accept, actor=actor
        )
        data = translator.from_wire(raw)
        return FhirAppointmentResponseType.from_pydantic(
            FhirAppointmentResponseResponse.model_validate(data)
        )

    @strawberry.field(
        description=(
            "Search AppointmentResponses, in genuine FHIR R4 shape, with a "
            "subset of the FHIR R4 AppointmentResponse search parameters "
            "(https://hl7.org/fhir/R4/appointmentresponse.html#search) — "
            "identifier, appointment, actor, part-status — plus "
            "limit/offset pagination. Requires the "
            "`appointment_response:read` permission."
        )
    )
    @translate_errors
    async def get_fhir_appointment_responses(
        self,
        info: strawberry.types.Info,
        identifier: Annotated[
            str | None,
            strawberry.argument(
                description="Exact match on a business identifier value."
            ),
        ] = None,
        appointment: Annotated[
            str | None,
            strawberry.argument(
                description="FHIR reference string, e.g. 'Appointment/40001'."
            ),
        ] = None,
        actor: Annotated[
            str | None,
            strawberry.argument(
                description="FHIR reference string, e.g. 'Practitioner/30001'."
            ),
        ] = None,
        part_status: Annotated[
            str | None,
            strawberry.argument(
                name="partStatus",
                description="accepted | declined | tentative | needs-action.",
            ),
        ] = None,
        limit: Annotated[
            int, strawberry.argument(description="Max results (default 50).")
        ] = 50,
        offset: Annotated[
            int, strawberry.argument(description="Pagination offset (default 0).")
        ] = 0,
    ) -> list[FhirAppointmentResponseType]:
        """Search AppointmentResponses — mirrors GET /AppointmentResponse?appointment=...&actor=..."""
        actor_user = require_gql_permission(info, "appointment_response", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_appointment_response_translator()
        params = translator.list_params(
            identifier, appointment, actor, part_status, limit, offset
        )
        raw = await connector.get(
            translator.list_path(),
            params=params,
            accept=translator.accept,
            actor=actor_user,
        )
        resources = _entries_from_bundle(translator.from_wire(raw))
        return [
            FhirAppointmentResponseType.from_pydantic(
                FhirAppointmentResponseResponse.model_validate(r)
            )
            for r in resources
        ]
