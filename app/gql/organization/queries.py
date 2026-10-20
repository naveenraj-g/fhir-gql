"""
Query fields for the Organization resource — one canonical, genuinely
FHIR R4-shaped Organization regardless of which connector (internal,
medplum, ...) is actually active. See app.gql.organization's package
docstring for the overall idea.
"""

from typing import Annotated

import strawberry

from app.connectors.internal.schemas.organization.fhir_schemas import FhirOrgResponse
from app.connectors.translator_registry import active_organization_translator
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.organization.types.response import FhirOrganizationType
from app.gql.permissions import require_gql_permission


def _entries_from_bundle(bundle: dict) -> list[dict]:
    """A FHIR search response is a Bundle regardless of backend — pull out
    each entry's resource. Falls back to treating the response itself as a
    single resource if it isn't a Bundle (defensive; both of today's
    connectors always return a Bundle for a collection GET)."""
    if bundle.get("resourceType") == "Bundle":
        return [entry["resource"] for entry in bundle.get("entry") or []]
    return [bundle]


@strawberry.type(description="Query fields for the Organization resource.")
class FhirOrganizationQuery:
    """Query fields for the Organization resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single Organization by its FHIR resource id, in genuine FHIR R4 shape. Requires the `organization:read` permission."
    )
    @translate_errors
    async def get_fhir_organization(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> FhirOrganizationType:
        """Fetch a single Organization by FHIR id — mirrors GET /Organization/{id}."""
        actor = require_gql_permission(info, "organization", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_organization_translator()
        raw = await connector.get(
            translator.item_path(id), accept=translator.accept, actor=actor
        )
        data = translator.from_wire(raw)
        return FhirOrganizationType.from_pydantic(FhirOrgResponse.model_validate(data))

    @strawberry.field(
        description=(
            "Search Organizations, in genuine FHIR R4 shape, with simple "
            "name/active filters and limit/offset pagination. Requires the "
            "`organization:read` permission."
        )
    )
    @translate_errors
    async def get_fhir_organizations(
        self,
        info: strawberry.types.Info,
        name: Annotated[
            str | None,
            strawberry.argument(description="Filter by Organization.name."),
        ] = None,
        active: Annotated[
            bool | None,
            strawberry.argument(description="Filter by Organization.active."),
        ] = None,
        limit: Annotated[
            int, strawberry.argument(description="Max results (default 50).")
        ] = 50,
        offset: Annotated[
            int, strawberry.argument(description="Pagination offset (default 0).")
        ] = 0,
    ) -> list[FhirOrganizationType]:
        """Search Organizations — mirrors GET /Organization?name=...&active=..."""
        actor = require_gql_permission(info, "organization", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_organization_translator()
        params = translator.list_params(name, active, limit, offset)
        raw = await connector.get(
            translator.list_path(),
            params=params,
            accept=translator.accept,
            actor=actor,
        )
        resources = _entries_from_bundle(translator.from_wire(raw))
        return [
            FhirOrganizationType.from_pydantic(FhirOrgResponse.model_validate(r))
            for r in resources
        ]
