"""
Query fields for the ServiceRequest resource — one canonical, genuinely
FHIR R4-shaped ServiceRequest regardless of which connector (internal,
medplum, ...) is actually active. Mirrors
app.gql.questionnaire_response.queries exactly.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_service_request_translator
from app.fhir.schemas.service_request import FhirServiceRequestResponse
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.service_request.types.response import FhirServiceRequestType


def _entries_from_bundle(bundle: dict) -> list[dict]:
    if bundle.get("resourceType") == "Bundle":
        return [entry["resource"] for entry in bundle.get("entry") or []]
    return [bundle]


@strawberry.type(description="Query fields for the ServiceRequest resource.")
class FhirServiceRequestQuery:
    """Query fields for the ServiceRequest resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single ServiceRequest by its FHIR resource id, in genuine FHIR R4 shape. Requires the `service_request:read` permission."
    )
    @translate_errors
    async def get_fhir_service_request(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> FhirServiceRequestType:
        """Fetch a single ServiceRequest by FHIR id — mirrors GET /ServiceRequest/{id}."""
        actor = require_gql_permission(info, "service_request", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_service_request_translator()
        raw = await connector.get(translator.item_path(id), accept=translator.accept, actor=actor)
        data = translator.from_wire(raw)
        return FhirServiceRequestType.from_pydantic(FhirServiceRequestResponse.model_validate(data))

    @strawberry.field(
        description=(
            "Search ServiceRequests, in genuine FHIR R4 shape, with a subset "
            "of the FHIR R4 ServiceRequest search parameters "
            "(https://hl7.org/fhir/R4/servicerequest.html#search) — status, "
            "intent, subject, identifier — plus limit/offset pagination. "
            "ServiceRequest is a default (gateway-trusted) resource on "
            "fhir-server, so `tenantId`/`userId` are explicit, client-"
            "suppliable filters here. Requires the `service_request:read` "
            "permission."
        )
    )
    @translate_errors
    async def get_fhir_service_requests(
        self,
        info: strawberry.types.Info,
        status: Annotated[
            str | None,
            strawberry.argument(description="draft | active | on-hold | revoked | completed | entered-in-error | unknown."),
        ] = None,
        intent: Annotated[
            str | None,
            strawberry.argument(description="proposal | plan | directive | order | original-order | reflex-order | filler-order | instance-order | option."),
        ] = None,
        subject: Annotated[
            str | None, strawberry.argument(description="Exact match on the subject reference string.")
        ] = None,
        identifier: Annotated[
            str | None, strawberry.argument(description="Exact match on a business identifier value.")
        ] = None,
        tenant_id: Annotated[
            str | None, strawberry.argument(description="Gateway-forwarded tenant/account ID filter.")
        ] = None,
        user_id: Annotated[
            str | None, strawberry.argument(description="Gateway-forwarded end-user ID filter.")
        ] = None,
        limit: Annotated[int, strawberry.argument(description="Max results (default 50).")] = 50,
        offset: Annotated[int, strawberry.argument(description="Pagination offset (default 0).")] = 0,
    ) -> list[FhirServiceRequestType]:
        """Search ServiceRequests — mirrors GET /ServiceRequest?status=...&subject=..."""
        actor = require_gql_permission(info, "service_request", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_service_request_translator()
        params = translator.list_params(status, intent, subject, identifier, tenant_id, user_id, limit, offset)
        raw = await connector.get(translator.list_path(), params=params, accept=translator.accept, actor=actor)
        resources = _entries_from_bundle(translator.from_wire(raw))
        return [
            FhirServiceRequestType.from_pydantic(FhirServiceRequestResponse.model_validate(r)) for r in resources
        ]
