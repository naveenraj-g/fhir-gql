"""
Query fields for the PractitionerRole resource — one canonical, genuinely
FHIR R4-shaped PractitionerRole regardless of which connector (internal,
medplum, ...) is actually active. Mirrors app.gql.organization.queries/
app.gql.location.queries/app.gql.healthcare_service.queries/
app.gql.practitioner.queries exactly — see those modules and
app.gql.organization's package docstring for the overall idea.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_practitioner_role_translator
from app.fhir.schemas.practitioner_role import FhirPractitionerRoleResponse
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.practitioner_role.types.response import FhirPractitionerRoleType


def _entries_from_bundle(bundle: dict) -> list[dict]:
    """A FHIR search response is a Bundle regardless of backend — pull out
    each entry's resource. Falls back to treating the response itself as a
    single resource if it isn't a Bundle (defensive; both of today's
    connectors always return a Bundle for a collection GET)."""
    if bundle.get("resourceType") == "Bundle":
        return [entry["resource"] for entry in bundle.get("entry") or []]
    return [bundle]


@strawberry.type(description="Query fields for the PractitionerRole resource.")
class FhirPractitionerRoleQuery:
    """Query fields for the PractitionerRole resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single PractitionerRole by its FHIR resource id, in genuine FHIR R4 shape. Requires the `practitioner_role:read` permission."
    )
    @translate_errors
    async def get_fhir_practitioner_role(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> FhirPractitionerRoleType:
        """Fetch a single PractitionerRole by FHIR id — mirrors GET /PractitionerRole/{id}."""
        actor = require_gql_permission(info, "practitioner_role", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_practitioner_role_translator()
        raw = await connector.get(
            translator.item_path(id), accept=translator.accept, actor=actor
        )
        data = translator.from_wire(raw)
        return FhirPractitionerRoleType.from_pydantic(
            FhirPractitionerRoleResponse.model_validate(data)
        )

    @strawberry.field(
        description=(
            "Search PractitionerRoles, in genuine FHIR R4 shape, with every "
            "FHIR R4 PractitionerRole search parameter "
            "(https://hl7.org/fhir/R4/practitionerrole.html#search) except "
            "`date`/`email`/`phone` — active, code (role), endpoint, "
            "identifier, location, organization, practitioner, service "
            "(healthcareService), specialty — plus limit/offset pagination. "
            "Requires the `practitioner_role:read` permission."
        )
    )
    @translate_errors
    async def get_fhir_practitioner_roles(
        self,
        info: strawberry.types.Info,
        active: Annotated[
            bool | None,
            strawberry.argument(description="Filter by active status."),
        ] = None,
        identifier: Annotated[
            str | None,
            strawberry.argument(
                description="Exact match on a business identifier value."
            ),
        ] = None,
        code: Annotated[
            str | None,
            strawberry.argument(
                name="role", description="Exact match on a coded practitioner role."
            ),
        ] = None,
        specialty: Annotated[
            str | None,
            strawberry.argument(description="Exact match on a coded specialty."),
        ] = None,
        practitioner: Annotated[
            str | None,
            strawberry.argument(
                description="FHIR reference string to the Practitioner, e.g. 'Practitioner/30001'."
            ),
        ] = None,
        organization: Annotated[
            str | None,
            strawberry.argument(
                description="FHIR reference string to the Organization, e.g. 'Organization/190001'."
            ),
        ] = None,
        location: Annotated[
            str | None,
            strawberry.argument(
                description="FHIR reference string, e.g. 'Location/230001'."
            ),
        ] = None,
        healthcare_service: Annotated[
            str | None,
            strawberry.argument(
                name="service",
                description="FHIR reference string, e.g. 'HealthcareService/150001'.",
            ),
        ] = None,
        endpoint: Annotated[
            str | None,
            strawberry.argument(
                description="FHIR reference string, e.g. 'Endpoint/1'."
            ),
        ] = None,
        limit: Annotated[
            int, strawberry.argument(description="Max results (default 50).")
        ] = 50,
        offset: Annotated[
            int, strawberry.argument(description="Pagination offset (default 0).")
        ] = 0,
    ) -> list[FhirPractitionerRoleType]:
        """Search PractitionerRoles — mirrors GET /PractitionerRole?active=...&role=..."""
        actor = require_gql_permission(info, "practitioner_role", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_practitioner_role_translator()
        params = translator.list_params(
            active,
            identifier,
            code,
            specialty,
            practitioner,
            organization,
            location,
            healthcare_service,
            endpoint,
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
            FhirPractitionerRoleType.from_pydantic(
                FhirPractitionerRoleResponse.model_validate(r)
            )
            for r in resources
        ]
