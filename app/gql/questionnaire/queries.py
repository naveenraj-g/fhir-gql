"""
Query fields for the Questionnaire resource — one canonical, genuinely
FHIR R4-shaped Questionnaire regardless of which connector (internal,
medplum, ...) is actually active. Mirrors app.gql.encounter.queries
exactly — see that module and app.gql.organization's package docstring
for the overall idea.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_questionnaire_translator
from app.fhir.schemas.questionnaire import FhirQuestionnaireResponse
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.questionnaire.types.response import FhirQuestionnaireType


def _entries_from_bundle(bundle: dict) -> list[dict]:
    """A FHIR search response is a Bundle regardless of backend — pull out
    each entry's resource. Falls back to treating the response itself as a
    single resource if it isn't a Bundle (defensive; both of today's
    connectors always return a Bundle for a collection GET)."""
    if bundle.get("resourceType") == "Bundle":
        return [entry["resource"] for entry in bundle.get("entry") or []]
    return [bundle]


@strawberry.type(description="Query fields for the Questionnaire resource.")
class FhirQuestionnaireQuery:
    """Query fields for the Questionnaire resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single Questionnaire by its FHIR resource id, in genuine FHIR R4 shape. Requires the `questionnaire:read` permission."
    )
    @translate_errors
    async def get_fhir_questionnaire(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> FhirQuestionnaireType:
        """Fetch a single Questionnaire by FHIR id — mirrors GET /Questionnaire/{id}."""
        actor = require_gql_permission(info, "questionnaire", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_questionnaire_translator()
        raw = await connector.get(
            translator.item_path(id), accept=translator.accept, actor=actor
        )
        data = translator.from_wire(raw)
        return FhirQuestionnaireType.from_pydantic(
            FhirQuestionnaireResponse.model_validate(data)
        )

    @strawberry.field(
        description=(
            "Search Questionnaires, in genuine FHIR R4 shape, with a subset "
            "of the FHIR R4 Questionnaire search parameters "
            "(https://hl7.org/fhir/R4/questionnaire.html#search) — status, "
            "url, name, title, publisher, identifier — plus limit/offset "
            "pagination. Always scoped to the caller's own org, derived "
            "from the forwarded JWT — not a client-suppliable filter. "
            "Requires the `questionnaire:read` permission."
        )
    )
    @translate_errors
    async def get_fhir_questionnaires(
        self,
        info: strawberry.types.Info,
        status: Annotated[
            str | None,
            strawberry.argument(description="draft | active | retired | unknown."),
        ] = None,
        url: Annotated[
            str | None,
            strawberry.argument(description="Exact match on the canonical url."),
        ] = None,
        name: Annotated[
            str | None, strawberry.argument(description="Substring match on name.")
        ] = None,
        title: Annotated[
            str | None, strawberry.argument(description="Substring match on title.")
        ] = None,
        publisher: Annotated[
            str | None,
            strawberry.argument(description="Substring match on publisher."),
        ] = None,
        identifier: Annotated[
            str | None,
            strawberry.argument(
                description="Exact match on a business identifier value."
            ),
        ] = None,
        limit: Annotated[
            int, strawberry.argument(description="Max results (default 50).")
        ] = 50,
        offset: Annotated[
            int, strawberry.argument(description="Pagination offset (default 0).")
        ] = 0,
    ) -> list[FhirQuestionnaireType]:
        """Search Questionnaires — mirrors GET /Questionnaire?status=...&name=..."""
        actor = require_gql_permission(info, "questionnaire", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_questionnaire_translator()
        params = translator.list_params(
            status, url, name, title, publisher, identifier, limit, offset
        )
        raw = await connector.get(
            translator.list_path(), params=params, accept=translator.accept, actor=actor
        )
        resources = _entries_from_bundle(translator.from_wire(raw))
        return [
            FhirQuestionnaireType.from_pydantic(FhirQuestionnaireResponse.model_validate(r))
            for r in resources
        ]
