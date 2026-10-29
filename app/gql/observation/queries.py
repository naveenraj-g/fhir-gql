"""
Query fields for the Observation resource — one canonical, genuinely
FHIR R4-shaped Observation regardless of which connector (internal,
medplum, ...) is actually active. Mirrors
app.gql.medication_request.queries exactly.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_observation_translator
from app.fhir.schemas.observation import FhirObservationResponse
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.observation.types.response import FhirObservationType
from app.gql.permissions import require_gql_permission


def _entries_from_bundle(bundle: dict) -> list[dict]:
    if bundle.get("resourceType") == "Bundle":
        return [entry["resource"] for entry in bundle.get("entry") or []]
    return [bundle]


@strawberry.type(description="Query fields for the Observation resource.")
class FhirObservationQuery:
    """Query fields for the Observation resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single Observation by its FHIR resource id, in genuine FHIR R4 shape. Requires the `observation:read` permission."
    )
    @translate_errors
    async def get_fhir_observation(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> FhirObservationType:
        """Fetch a single Observation by FHIR id — mirrors GET /Observation/{id}."""
        actor = require_gql_permission(info, "observation", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_observation_translator()
        raw = await connector.get(translator.item_path(id), accept=translator.accept, actor=actor)
        data = translator.from_wire(raw)
        return FhirObservationType.from_pydantic(FhirObservationResponse.model_validate(data))

    @strawberry.field(
        description=(
            "Search Observations, in genuine FHIR R4 shape, with a subset "
            "of the FHIR R4 Observation search parameters "
            "(https://hl7.org/fhir/R4/observation.html#search) — status, "
            "subject, identifier — plus limit/offset pagination. "
            "Always scoped to the caller's own org, derived from the "
            "forwarded JWT — not a client-suppliable filter. Requires "
            "the `observation:read` permission."
        )
    )
    @translate_errors
    async def get_fhir_observations(
        self,
        info: strawberry.types.Info,
        status: Annotated[
            str | None,
            strawberry.argument(description="registered | preliminary | final | amended | corrected | cancelled | entered-in-error | unknown."),
        ] = None,
        subject: Annotated[
            str | None, strawberry.argument(description="Exact match on the subject reference string.")
        ] = None,
        identifier: Annotated[
            str | None, strawberry.argument(description="Exact match on a business identifier value.")
        ] = None,
        limit: Annotated[int, strawberry.argument(description="Max results (default 50).")] = 50,
        offset: Annotated[int, strawberry.argument(description="Pagination offset (default 0).")] = 0,
    ) -> list[FhirObservationType]:
        """Search Observations — mirrors GET /Observation?status=...&subject=..."""
        actor = require_gql_permission(info, "observation", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_observation_translator()
        params = translator.list_params(status, subject, identifier, limit, offset)
        raw = await connector.get(translator.list_path(), params=params, accept=translator.accept, actor=actor)
        resources = _entries_from_bundle(translator.from_wire(raw))
        return [FhirObservationType.from_pydantic(FhirObservationResponse.model_validate(r)) for r in resources]
