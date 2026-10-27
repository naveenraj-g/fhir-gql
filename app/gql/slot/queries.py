"""
Query fields for the Slot resource — one canonical, genuinely FHIR
R4-shaped Slot regardless of which connector (internal, medplum, ...) is
actually active. Mirrors app.gql.organization.queries/
app.gql.location.queries/app.gql.healthcare_service.queries/
app.gql.practitioner.queries/app.gql.practitioner_role.queries/
app.gql.schedule.queries exactly — see those modules and
app.gql.organization's package docstring for the overall idea.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_slot_translator
from app.fhir.schemas.slot import FhirSlotResponse
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.slot.types.response import FhirSlotType


def _entries_from_bundle(bundle: dict) -> list[dict]:
    """A FHIR search response is a Bundle regardless of backend — pull out
    each entry's resource. Falls back to treating the response itself as a
    single resource if it isn't a Bundle (defensive; both of today's
    connectors always return a Bundle for a collection GET)."""
    if bundle.get("resourceType") == "Bundle":
        return [entry["resource"] for entry in bundle.get("entry") or []]
    return [bundle]


@strawberry.type(description="Query fields for the Slot resource.")
class FhirSlotQuery:
    """Query fields for the Slot resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single Slot by its FHIR resource id, in genuine FHIR R4 shape. Requires the `slot:read` permission."
    )
    @translate_errors
    async def get_fhir_slot(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> FhirSlotType:
        """Fetch a single Slot by FHIR id — mirrors GET /Slot/{id}."""
        actor = require_gql_permission(info, "slot", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_slot_translator()
        raw = await connector.get(
            translator.item_path(id), accept=translator.accept, actor=actor
        )
        data = translator.from_wire(raw)
        return FhirSlotType.from_pydantic(FhirSlotResponse.model_validate(data))

    @strawberry.field(
        description=(
            "Search Slots, in genuine FHIR R4 shape, with every FHIR R4 "
            "Slot search parameter (https://hl7.org/fhir/R4/slot.html#search) "
            "except `start` — identifier, schedule, service-category, "
            "service-type, specialty, status — plus limit/offset "
            "pagination. Requires the `slot:read` permission."
        )
    )
    @translate_errors
    async def get_fhir_slots(
        self,
        info: strawberry.types.Info,
        status: Annotated[
            str | None,
            strawberry.argument(
                description="busy | free | busy-unavailable | busy-tentative | entered-in-error."
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
        schedule: Annotated[
            str | None,
            strawberry.argument(
                description="FHIR reference string, e.g. 'Schedule/200001'."
            ),
        ] = None,
        limit: Annotated[
            int, strawberry.argument(description="Max results (default 50).")
        ] = 50,
        offset: Annotated[
            int, strawberry.argument(description="Pagination offset (default 0).")
        ] = 0,
    ) -> list[FhirSlotType]:
        """Search Slots — mirrors GET /Slot?status=...&schedule=..."""
        actor = require_gql_permission(info, "slot", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_slot_translator()
        params = translator.list_params(
            status,
            identifier,
            service_category,
            service_type,
            specialty,
            schedule,
            limit,
            offset,
        )
        raw = await connector.get(
            translator.list_path(),
            params=params,
            accept=translator.accept,
            actor=actor,
        )
        resources = _entries_from_bundle(translator.from_wire(raw))
        return [
            FhirSlotType.from_pydantic(FhirSlotResponse.model_validate(r))
            for r in resources
        ]
