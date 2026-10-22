"""
Query fields for the Location resource — one canonical, genuinely FHIR
R4-shaped Location regardless of which connector (internal, medplum, ...)
is actually active. Mirrors app.gql.organization.queries exactly — see
that module and app.gql.organization's package docstring for the overall
idea.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_location_translator
from app.fhir.schemas.location import FhirLocationResponse
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.location.types.response import FhirLocationType
from app.gql.permissions import require_gql_permission


def _entries_from_bundle(bundle: dict) -> list[dict]:
    """A FHIR search response is a Bundle regardless of backend — pull out
    each entry's resource. Falls back to treating the response itself as a
    single resource if it isn't a Bundle (defensive; both of today's
    connectors always return a Bundle for a collection GET)."""
    if bundle.get("resourceType") == "Bundle":
        return [entry["resource"] for entry in bundle.get("entry") or []]
    return [bundle]


@strawberry.type(description="Query fields for the Location resource.")
class FhirLocationQuery:
    """Query fields for the Location resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single Location by its FHIR resource id, in genuine FHIR R4 shape. Requires the `location:read` permission."
    )
    @translate_errors
    async def get_fhir_location(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> FhirLocationType:
        """Fetch a single Location by FHIR id — mirrors GET /Location/{id}."""
        actor = require_gql_permission(info, "location", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_location_translator()
        raw = await connector.get(
            translator.item_path(id), accept=translator.accept, actor=actor
        )
        data = translator.from_wire(raw)
        return FhirLocationType.from_pydantic(FhirLocationResponse.model_validate(data))

    @strawberry.field(
        description=(
            "Search Locations, in genuine FHIR R4 shape, with every FHIR "
            "R4 Location search parameter "
            "(https://hl7.org/fhir/R4/location.html#search) — address, "
            "address-city, address-country, address-postalcode, "
            "address-state, address-use, endpoint, identifier, name, near, "
            "operational-status, organization, partof, status, type — plus "
            "limit/offset pagination. Requires the `location:read` "
            "permission."
        )
    )
    @translate_errors
    async def get_fhir_locations(
        self,
        info: strawberry.types.Info,
        name: Annotated[
            str | None,
            strawberry.argument(
                description="Partial match against Location.name or any alias."
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            strawberry.argument(
                description="Exact match on a business identifier value."
            ),
        ] = None,
        status: Annotated[
            str | None,
            strawberry.argument(description="active | suspended | inactive."),
        ] = None,
        operational_status: Annotated[
            str | None,
            strawberry.argument(
                name="operationalStatus",
                description="Exact match on the operational status code (e.g. 'U' for Unoccupied).",
            ),
        ] = None,
        type: Annotated[
            str | None,
            strawberry.argument(
                name="type",
                description="Exact match on a coded function performed at the location (e.g. 'HOSP').",
            ),
        ] = None,
        address: Annotated[
            str | None,
            strawberry.argument(
                description="Partial match against any Address sub-field (line, city, district, state, country, postalCode, text)."
            ),
        ] = None,
        address_city: Annotated[
            str | None,
            strawberry.argument(description="Filter by address city — partial match."),
        ] = None,
        address_state: Annotated[
            str | None,
            strawberry.argument(description="Filter by address state — partial match."),
        ] = None,
        address_postal_code: Annotated[
            str | None,
            strawberry.argument(
                description="Filter by address postal code — exact match."
            ),
        ] = None,
        address_country: Annotated[
            str | None,
            strawberry.argument(
                description="Filter by address country — partial match."
            ),
        ] = None,
        address_use: Annotated[
            str | None,
            strawberry.argument(description="home | work | temp | old | billing."),
        ] = None,
        organization: Annotated[
            str | None,
            strawberry.argument(
                description="Managing organization, as a FHIR reference string, e.g. 'Organization/190001'."
            ),
        ] = None,
        partof: Annotated[
            str | None,
            strawberry.argument(
                description="Containing location, as a FHIR reference string, e.g. 'Location/230001'."
            ),
        ] = None,
        endpoint: Annotated[
            str | None,
            strawberry.argument(
                description="FHIR reference string, e.g. 'Endpoint/1'."
            ),
        ] = None,
        near: Annotated[
            str | None,
            strawberry.argument(
                description="Radius search against Location.position, as '[latitude]|[longitude]|[distance]|[units]' — e.g. '42.25475478|-83.6945691|11.20|km'."
            ),
        ] = None,
        limit: Annotated[
            int, strawberry.argument(description="Max results (default 50).")
        ] = 50,
        offset: Annotated[
            int, strawberry.argument(description="Pagination offset (default 0).")
        ] = 0,
    ) -> list[FhirLocationType]:
        """Search Locations — mirrors GET /Location?name=...&status=..."""
        actor = require_gql_permission(info, "location", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_location_translator()
        params = translator.list_params(
            name,
            identifier,
            status,
            operational_status,
            type,
            address,
            address_city,
            address_state,
            address_postal_code,
            address_country,
            address_use,
            organization,
            partof,
            endpoint,
            near,
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
            FhirLocationType.from_pydantic(FhirLocationResponse.model_validate(r))
            for r in resources
        ]
