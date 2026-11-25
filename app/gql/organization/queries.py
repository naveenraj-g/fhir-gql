"""
Query fields for the Organization resource — one canonical, genuinely
FHIR R4-shaped Organization regardless of which connector (internal,
medplum, ...) is actually active. See app.gql.organization's package
docstring for the overall idea.

Search follows FHIR R4 search (https://www.hl7.org/fhir/R4/search.html) —
both backends implement it, so the arguments mean the same thing on either:

- Every FHIR R4 Organization search parameter
  (https://www.hl7.org/fhir/R4/organization.html#search) is a typed
  argument, named per the FHIR GraphQL convention (`-` -> `_`, here then
  camelCased: `address-city` -> `addressCity`), plus `_id` (`id`) and
  `_lastUpdated` (`lastUpdated`). Values use FHIR value syntax unchanged:
  comma = OR, `system|code` for tokens, `ge2024-01-01` for dates.
- `params` reaches everything else — modifiers (`name:exact`), chains
  (`partof.name`), `_summary`, `_elements`, or repeating a parameter to AND it.
- Paging/sorting/includes are their own arguments (`count`, `offset`,
  `sort`, `total`, `include`, `revinclude`).

Two queries share all of that:
- `searchFhirOrganizations` returns the whole searchset (total, includes,
  paging, warnings) as FhirOrganizationSearchResult.
- `getFhirOrganizations` is the older list-only form: same filters, just
  the matching Organizations.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_organization_translator
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.organization.search_params import (
    ActiveArg,
    AddressArg,
    AddressCityArg,
    AddressCountryArg,
    AddressPostalCodeArg,
    AddressStateArg,
    AddressUseArg,
    EndpointArg,
    IdentifierArg,
    IncludeArg,
    NameArg,
    PartofArg,
    PhoneticArg,
    RevincludeArg,
    TypeArg,
    fhir_filters,
)
from app.gql.organization.types.response import FhirOrganizationType
from app.gql.organization.types.search import FhirOrganizationSearchResult
from app.gql.permissions import require_gql_permission
from app.gql.search import (
    CountArg,
    IdArg,
    LastUpdatedArg,
    OffsetArg,
    ParamsArg,
    SortArg,
    TotalArg,
    bundle_links,
    run_fhir_search,
)


async def _run_search(info, **search):
    """One Organization FHIR search on the active connector — see
    app.gql.search.run_fhir_search."""
    return await run_fhir_search(
        info,
        resource="organization",
        translator=active_organization_translator(),
        **search,
    )


def _organization(resource: dict) -> FhirOrganizationType:
    """One FHIR Organization dict -> what a resolver returns for FhirOrganizationType.

    The type reads the FHIR dict directly (see app.gql.fhir_types), so the backend's JSON is
    passed through unchanged - nothing is validated on a read, so one record that lacks an
    element R4 requires (another EHR's data) cannot fail the query."""
    return resource


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
        return _organization(translator.from_wire(raw))

    @strawberry.field(
        description=(
            "FHIR R4 search over Organizations (https://www.hl7.org/fhir/R4/search.html), returning "
            "the whole result: matching Organizations, `include`/`revinclude`d resources, the total "
            "match count, paging (`nextOffset`, links) and any warnings. Every R4 Organization search "
            "parameter is a typed argument; `params` adds modifiers, chains and anything else FHIR "
            "search accepts. Requires the `organization:read` permission."
        )
    )
    @translate_errors
    async def search_fhir_organizations(
        self,
        info: strawberry.types.Info,
        id: IdArg = None,
        last_updated: LastUpdatedArg = None,
        name: NameArg = None,
        phonetic: PhoneticArg = None,
        active: ActiveArg = None,
        identifier: IdentifierArg = None,
        type: TypeArg = None,
        address: AddressArg = None,
        address_city: AddressCityArg = None,
        address_state: AddressStateArg = None,
        address_postal_code: AddressPostalCodeArg = None,
        address_country: AddressCountryArg = None,
        address_use: AddressUseArg = None,
        partof: PartofArg = None,
        endpoint: EndpointArg = None,
        params: ParamsArg = None,
        count: CountArg = 50,
        offset: OffsetArg = 0,
        sort: SortArg = None,
        total: TotalArg = None,
        include: IncludeArg = None,
        revinclude: RevincludeArg = None,
    ) -> FhirOrganizationSearchResult:
        """Mirrors GET /Organization?... and returns the whole searchset."""
        result = await _run_search(
            info,
            filters=fhir_filters(
                id=id,
                last_updated=last_updated,
                name=name,
                phonetic=phonetic,
                active=active,
                identifier=identifier,
                type=type,
                address=address,
                address_city=address_city,
                address_state=address_state,
                address_postal_code=address_postal_code,
                address_country=address_country,
                address_use=address_use,
                partof=partof,
                endpoint=endpoint,
            ),
            params=params,
            count=count,
            offset=offset,
            sort=sort,
            total=total,
            include=include,
            revinclude=revinclude,
        )
        return FhirOrganizationSearchResult(
            total=result.total,
            organizations=[_organization(r) for r in result.matches],
            # Only Organization includes can be typed; every include (any
            # resource type) is still available raw in `included`.
            included_organizations=[
                _organization(r)
                for r in result.included
                if r.get("resourceType") == "Organization"
            ],
            included=result.included,
            next_offset=result.next_offset,
            links=bundle_links(result),
            warnings=result.warnings,
        )

    @strawberry.field(
        description=(
            "Search Organizations and return just the matching page, in genuine FHIR R4 shape — the "
            "same FHIR R4 search and filters as `searchFhirOrganizations` (use that one for the "
            "total, includes, paging and warnings). Requires the `organization:read` permission."
        )
    )
    @translate_errors
    async def get_fhir_organizations(
        self,
        info: strawberry.types.Info,
        id: IdArg = None,
        last_updated: LastUpdatedArg = None,
        name: NameArg = None,
        phonetic: PhoneticArg = None,
        active: ActiveArg = None,
        identifier: IdentifierArg = None,
        type: TypeArg = None,
        address: AddressArg = None,
        address_city: AddressCityArg = None,
        address_state: AddressStateArg = None,
        address_postal_code: AddressPostalCodeArg = None,
        address_country: AddressCountryArg = None,
        address_use: AddressUseArg = None,
        partof: PartofArg = None,
        endpoint: EndpointArg = None,
        params: ParamsArg = None,
        limit: Annotated[
            int,
            strawberry.argument(
                description="Page size — sent as FHIR `_count` (default 50)."
            ),
        ] = 50,
        offset: OffsetArg = 0,
        sort: SortArg = None,
    ) -> list[FhirOrganizationType]:
        """Mirrors GET /Organization?... — the matches only. `limit` keeps
        this query's original argument name (it is FHIR's `_count`), so
        existing callers don't break."""
        result = await _run_search(
            info,
            filters=fhir_filters(
                id=id,
                last_updated=last_updated,
                name=name,
                phonetic=phonetic,
                active=active,
                identifier=identifier,
                type=type,
                address=address,
                address_city=address_city,
                address_state=address_state,
                address_postal_code=address_postal_code,
                address_country=address_country,
                address_use=address_use,
                partof=partof,
                endpoint=endpoint,
            ),
            params=params,
            count=limit,
            offset=offset,
            sort=sort,
            total=None,
            include=None,
            revinclude=None,
        )
        return [_organization(r) for r in result.matches]
