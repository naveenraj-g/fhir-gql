"""
Query fields for the Appointment resource — one canonical, genuinely FHIR
R4-shaped Appointment regardless of which connector (internal, medplum,
...) is actually active. Mirrors app.gql.organization.queries/.../
app.gql.slot.queries exactly — see those modules and
app.gql.organization's package docstring for the overall idea.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_appointment_translator
from app.fhir.schemas.appointment import FhirAppointmentResponse
from app.gql.appointment.types.response import FhirAppointmentType
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


@strawberry.type(description="Query fields for the Appointment resource.")
class FhirAppointmentQuery:
    """Query fields for the Appointment resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single Appointment by its FHIR resource id, in genuine FHIR R4 shape. Requires the `appointment:read` permission."
    )
    @translate_errors
    async def get_fhir_appointment(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> FhirAppointmentType:
        """Fetch a single Appointment by FHIR id — mirrors GET /Appointment/{id}."""
        actor = require_gql_permission(info, "appointment", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_appointment_translator()
        raw = await connector.get(
            translator.item_path(id), accept=translator.accept, actor=actor
        )
        data = translator.from_wire(raw)
        return FhirAppointmentType.from_pydantic(
            FhirAppointmentResponse.model_validate(data)
        )

    @strawberry.field(
        description=(
            "Search Appointments, in genuine FHIR R4 shape, with a subset of "
            "the FHIR R4 Appointment search parameters "
            "(https://hl7.org/fhir/R4/appointment.html#search) — identifier, "
            "actor, slot, service-category, service-type, specialty, status "
            "— plus limit/offset pagination. Requires the `appointment:read` "
            "permission."
        )
    )
    @translate_errors
    async def get_fhir_appointments(
        self,
        info: strawberry.types.Info,
        status: Annotated[
            str | None,
            strawberry.argument(
                description=(
                    "proposed | pending | booked | arrived | fulfilled | "
                    "cancelled | noshow | entered-in-error | checked-in | "
                    "waitlist."
                )
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            strawberry.argument(
                description="Exact match on a business identifier value."
            ),
        ] = None,
        service_category: Annotated[
            str | None,
            strawberry.argument(
                name="serviceCategory",
                description="Exact match on a coded service category.",
            ),
        ] = None,
        service_type: Annotated[
            str | None,
            strawberry.argument(
                name="serviceType",
                description="Exact match on a coded service type.",
            ),
        ] = None,
        specialty: Annotated[
            str | None,
            strawberry.argument(description="Exact match on a coded specialty."),
        ] = None,
        actor: Annotated[
            str | None,
            strawberry.argument(
                description="FHIR reference string, e.g. 'Practitioner/30001'."
            ),
        ] = None,
        slot: Annotated[
            str | None,
            strawberry.argument(
                description="FHIR reference string, e.g. 'Slot/220001'."
            ),
        ] = None,
        limit: Annotated[
            int, strawberry.argument(description="Max results (default 50).")
        ] = 50,
        offset: Annotated[
            int, strawberry.argument(description="Pagination offset (default 0).")
        ] = 0,
    ) -> list[FhirAppointmentType]:
        """Search Appointments — mirrors GET /Appointment?status=...&actor=..."""
        actor_user = require_gql_permission(info, "appointment", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_appointment_translator()
        params = translator.list_params(
            status,
            identifier,
            service_category,
            service_type,
            specialty,
            actor,
            slot,
            limit,
            offset,
        )
        raw = await connector.get(
            translator.list_path(),
            params=params,
            accept=translator.accept,
            actor=actor_user,
        )
        resources = _entries_from_bundle(translator.from_wire(raw))
        return [
            FhirAppointmentType.from_pydantic(FhirAppointmentResponse.model_validate(r))
            for r in resources
        ]
