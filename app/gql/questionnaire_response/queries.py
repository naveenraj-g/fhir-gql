"""
Query fields for the QuestionnaireResponse resource — one canonical,
genuinely FHIR R4-shaped QuestionnaireResponse regardless of which
connector (internal, medplum, ...) is actually active. Mirrors
app.gql.questionnaire.queries exactly — see that module and
app.gql.organization's package docstring for the overall idea.

QuestionnaireResponse is a default (gateway-trusted) resource on
fhir-server (see app.connectors.internal.translators.questionnaire_response's
module docstring) — this gateway's own `questionnaire_response:read`
permission check still applies regardless; that's a GraphQL-boundary
authorization concern, separate from whether fhir-server itself also
re-checks the JWT.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_questionnaire_response_translator
from app.fhir.schemas.questionnaire_response import FhirQuestionnaireResponseResponse
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.questionnaire_response.types.response import FhirQuestionnaireResponseType


def _entries_from_bundle(bundle: dict) -> list[dict]:
    """A FHIR search response is a Bundle regardless of backend — pull out
    each entry's resource. Falls back to treating the response itself as a
    single resource if it isn't a Bundle (defensive; both of today's
    connectors always return a Bundle for a collection GET)."""
    if bundle.get("resourceType") == "Bundle":
        return [entry["resource"] for entry in bundle.get("entry") or []]
    return [bundle]


@strawberry.type(description="Query fields for the QuestionnaireResponse resource.")
class FhirQuestionnaireResponseQuery:
    """Query fields for the QuestionnaireResponse resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single QuestionnaireResponse by its FHIR resource id, in genuine FHIR R4 shape. Requires the `questionnaire_response:read` permission."
    )
    @translate_errors
    async def get_fhir_questionnaire_response(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> FhirQuestionnaireResponseType:
        """Fetch a single QuestionnaireResponse by FHIR id — mirrors GET /QuestionnaireResponse/{id}."""
        actor = require_gql_permission(info, "questionnaire_response", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_questionnaire_response_translator()
        raw = await connector.get(
            translator.item_path(id), accept=translator.accept, actor=actor
        )
        data = translator.from_wire(raw)
        return FhirQuestionnaireResponseType.from_pydantic(
            FhirQuestionnaireResponseResponse.model_validate(data)
        )

    @strawberry.field(
        description=(
            "Search QuestionnaireResponses, in genuine FHIR R4 shape, with a "
            "subset of the FHIR R4 QuestionnaireResponse search parameters "
            "(https://hl7.org/fhir/R4/questionnaireresponse.html#search) — "
            "status, questionnaire, subject, identifier — plus limit/offset "
            "pagination. QuestionnaireResponse is a default (gateway-trusted) "
            "resource on fhir-server, so `tenantId`/`userId` are explicit, "
            "client-suppliable filters here, unlike an auth-rollout resource's "
            "org-derived scoping. Requires the `questionnaire_response:read` "
            "permission."
        )
    )
    @translate_errors
    async def get_fhir_questionnaire_responses(
        self,
        info: strawberry.types.Info,
        status: Annotated[
            str | None,
            strawberry.argument(description="in-progress | completed | amended | entered-in-error | stopped."),
        ] = None,
        questionnaire: Annotated[
            str | None,
            strawberry.argument(description="Exact match on the canonical Questionnaire reference."),
        ] = None,
        subject: Annotated[
            str | None, strawberry.argument(description="Exact match on the subject reference string.")
        ] = None,
        identifier: Annotated[
            str | None,
            strawberry.argument(description="Exact match on the business identifier value."),
        ] = None,
        tenant_id: Annotated[
            str | None,
            strawberry.argument(description="Gateway-forwarded tenant/account ID filter."),
        ] = None,
        user_id: Annotated[
            str | None,
            strawberry.argument(description="Gateway-forwarded end-user ID filter."),
        ] = None,
        limit: Annotated[
            int, strawberry.argument(description="Max results (default 50).")
        ] = 50,
        offset: Annotated[
            int, strawberry.argument(description="Pagination offset (default 0).")
        ] = 0,
    ) -> list[FhirQuestionnaireResponseType]:
        """Search QuestionnaireResponses — mirrors GET /QuestionnaireResponse?status=...&subject=..."""
        actor = require_gql_permission(info, "questionnaire_response", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_questionnaire_response_translator()
        params = translator.list_params(
            status, questionnaire, subject, identifier, tenant_id, user_id, limit, offset
        )
        raw = await connector.get(
            translator.list_path(), params=params, accept=translator.accept, actor=actor
        )
        resources = _entries_from_bundle(translator.from_wire(raw))
        return [
            FhirQuestionnaireResponseType.from_pydantic(FhirQuestionnaireResponseResponse.model_validate(r))
            for r in resources
        ]
