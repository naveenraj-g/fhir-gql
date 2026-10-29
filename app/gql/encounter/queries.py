"""
Query fields for the Encounter resource — one canonical, genuinely FHIR
R4-shaped Encounter regardless of which connector (internal, medplum, ...)
is actually active. Mirrors app.gql.organization.queries/.../
app.gql.appointment_response.queries exactly — see those modules and
app.gql.organization's package docstring for the overall idea.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_encounter_translator
from app.fhir.schemas.encounter import FhirEncounterResponse
from app.gql.context import get_container
from app.gql.encounter.types.response import FhirEncounterType
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


@strawberry.type(description="Query fields for the Encounter resource.")
class FhirEncounterQuery:
    """Query fields for the Encounter resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single Encounter by its FHIR resource id, in genuine FHIR R4 shape. Requires the `encounter:read` permission."
    )
    @translate_errors
    async def get_fhir_encounter(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> FhirEncounterType:
        """Fetch a single Encounter by FHIR id — mirrors GET /Encounter/{id}."""
        actor = require_gql_permission(info, "encounter", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_encounter_translator()
        raw = await connector.get(
            translator.item_path(id), accept=translator.accept, actor=actor
        )
        data = translator.from_wire(raw)
        return FhirEncounterType.from_pydantic(
            FhirEncounterResponse.model_validate(data)
        )

    @strawberry.field(
        description=(
            "Search Encounters, in genuine FHIR R4 shape, with a subset of "
            "the FHIR R4 Encounter search parameters "
            "(https://hl7.org/fhir/R4/encounter.html#search) — status, "
            "identifier, subject, class, type, service-provider, part-of "
            "— plus limit/offset pagination. Requires the `encounter:read` "
            "permission."
        )
    )
    @translate_errors
    async def get_fhir_encounters(
        self,
        info: strawberry.types.Info,
        status: Annotated[
            str | None,
            strawberry.argument(
                description=(
                    "planned | arrived | triaged | in-progress | onleave | "
                    "finished | cancelled | entered-in-error | unknown."
                )
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            strawberry.argument(
                description="Exact match on a business identifier value."
            ),
        ] = None,
        subject: Annotated[
            str | None,
            strawberry.argument(
                description="FHIR reference string, e.g. 'Patient/999'."
            ),
        ] = None,
        class_code: Annotated[
            str | None,
            strawberry.argument(
                name="class",
                description="Exact match on the Encounter.class code.",
            ),
        ] = None,
        type_code: Annotated[
            str | None,
            strawberry.argument(
                name="type",
                description="Exact match on a coded Encounter.type.",
            ),
        ] = None,
        service_provider: Annotated[
            str | None,
            strawberry.argument(
                name="serviceProvider",
                description="FHIR reference string, e.g. 'Organization/190001'.",
            ),
        ] = None,
        part_of: Annotated[
            str | None,
            strawberry.argument(
                name="partOf",
                description="FHIR reference string, e.g. 'Encounter/20001'.",
            ),
        ] = None,
        limit: Annotated[
            int, strawberry.argument(description="Max results (default 50).")
        ] = 50,
        offset: Annotated[
            int, strawberry.argument(description="Pagination offset (default 0).")
        ] = 0,
    ) -> list[FhirEncounterType]:
        """Search Encounters — mirrors GET /Encounter?status=...&subject=..."""
        actor_user = require_gql_permission(info, "encounter", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_encounter_translator()
        params = translator.list_params(
            status,
            identifier,
            subject,
            class_code,
            type_code,
            service_provider,
            part_of,
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
            FhirEncounterType.from_pydantic(FhirEncounterResponse.model_validate(r))
            for r in resources
        ]
