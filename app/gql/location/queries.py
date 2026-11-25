"""
Query fields for the Location resource — one canonical, genuinely FHIR
R4-shaped Location regardless of which connector (internal, medplum, ...)
is actually active. Mirrors app.gql.organization.queries — see that module
for the overall shape:

- Every FHIR R4 Location search parameter
  (https://www.hl7.org/fhir/R4/location.html#search) is a typed argument
  (FHIR GraphQL convention, camelCased: `address-city` -> `addressCity`,
  `operational-status` -> `operationalStatus`), plus `_id` (`id`) and
  `_lastUpdated` (`lastUpdated`). Values use FHIR value syntax unchanged.
- `params` reaches everything else — modifiers, chains
  (`organization.name`, `partof.name`), `_summary`, `_elements`, ...
- `searchFhirLocations` returns the whole searchset (total, includes,
  `near` distances, paging, warnings); `getFhirLocations` is the older
  list-only form with the same filters.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_location_translator
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.location.search_params import (
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
    NearArg,
    OperationalStatusArg,
    OrganizationArg,
    PartofArg,
    RevincludeArg,
    StatusArg,
    TypeArg,
    fhir_filters,
)
from app.gql.location.types.response import FhirLocationType
from app.gql.location.types.search import (
    FhirLocationDistanceType,
    FhirLocationSearchResult,
)
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

# The FHIR extension a `near` match carries its distance in.
_DISTANCE_URL = "http://hl7.org/fhir/StructureDefinition/location-distance"


async def _run_search(info, **search):
    """One Location FHIR search on the active connector — see
    app.gql.search.run_fhir_search."""
    return await run_fhir_search(
        info, resource="location", translator=active_location_translator(), **search
    )


def _location(resource: dict) -> FhirLocationType:
    """One FHIR Location dict -> its GraphQL type (validated through the
    canonical Pydantic model first)."""
    return resource


def _distances(result) -> list[FhirLocationDistanceType]:
    """Each match's location-distance extension (present on `near` searches)."""
    out = []
    for resource, extensions in zip(result.matches, result.match_extensions):
        for ext in extensions:
            if ext.get("url") == _DISTANCE_URL and ext.get("valueDistance"):
                d = ext["valueDistance"]
                out.append(
                    FhirLocationDistanceType(
                        location_id=resource["id"],
                        value=d["value"],
                        unit=d.get("unit", ""),
                    )
                )
    return out


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
        return _location(translator.from_wire(raw))

    @strawberry.field(
        description=(
            "FHIR R4 search over Locations (https://www.hl7.org/fhir/R4/search.html), returning the whole "
            "result: matching Locations, `include`/`revinclude`d resources, `near` distances, the total "
            "match count, paging (`nextOffset`, links) and any warnings. Every R4 Location search "
            "parameter is a typed argument; `params` adds modifiers, chains and anything else FHIR search "
            "accepts. Requires the `location:read` permission."
        )
    )
    @translate_errors
    async def search_fhir_locations(
        self,
        info: strawberry.types.Info,
        id: IdArg = None,
        last_updated: LastUpdatedArg = None,
        name: NameArg = None,
        identifier: IdentifierArg = None,
        status: StatusArg = None,
        operational_status: OperationalStatusArg = None,
        type: TypeArg = None,
        address: AddressArg = None,
        address_city: AddressCityArg = None,
        address_state: AddressStateArg = None,
        address_postal_code: AddressPostalCodeArg = None,
        address_country: AddressCountryArg = None,
        address_use: AddressUseArg = None,
        organization: OrganizationArg = None,
        partof: PartofArg = None,
        endpoint: EndpointArg = None,
        near: NearArg = None,
        params: ParamsArg = None,
        count: CountArg = 50,
        offset: OffsetArg = 0,
        sort: SortArg = None,
        total: TotalArg = None,
        include: IncludeArg = None,
        revinclude: RevincludeArg = None,
    ) -> FhirLocationSearchResult:
        """Mirrors GET /Location?... and returns the whole searchset."""
        result = await _run_search(
            info,
            filters=fhir_filters(
                id=id,
                last_updated=last_updated,
                name=name,
                identifier=identifier,
                status=status,
                operational_status=operational_status,
                type=type,
                address=address,
                address_city=address_city,
                address_state=address_state,
                address_postal_code=address_postal_code,
                address_country=address_country,
                address_use=address_use,
                organization=organization,
                partof=partof,
                endpoint=endpoint,
                near=near,
            ),
            params=params,
            count=count,
            offset=offset,
            sort=sort,
            total=total,
            include=include,
            revinclude=revinclude,
        )
        return FhirLocationSearchResult(
            total=result.total,
            locations=[_location(r) for r in result.matches],
            included_locations=[
                _location(r)
                for r in result.included
                if r.get("resourceType") == "Location"
            ],
            included_organizations=[
                r for r in result.included if r.get("resourceType") == "Organization"
            ],
            included=result.included,
            distances=_distances(result),
            next_offset=result.next_offset,
            links=bundle_links(result),
            warnings=result.warnings,
        )

    @strawberry.field(
        description=(
            "Search Locations and return just the matching page, in genuine FHIR R4 shape — the same FHIR "
            "R4 search and filters as `searchFhirLocations` (use that one for the total, includes, `near` "
            "distances, paging and warnings). Requires the `location:read` permission."
        )
    )
    @translate_errors
    async def get_fhir_locations(
        self,
        info: strawberry.types.Info,
        id: IdArg = None,
        last_updated: LastUpdatedArg = None,
        name: NameArg = None,
        identifier: IdentifierArg = None,
        status: StatusArg = None,
        operational_status: OperationalStatusArg = None,
        type: TypeArg = None,
        address: AddressArg = None,
        address_city: AddressCityArg = None,
        address_state: AddressStateArg = None,
        address_postal_code: AddressPostalCodeArg = None,
        address_country: AddressCountryArg = None,
        address_use: AddressUseArg = None,
        organization: OrganizationArg = None,
        partof: PartofArg = None,
        endpoint: EndpointArg = None,
        near: NearArg = None,
        params: ParamsArg = None,
        limit: Annotated[
            int,
            strawberry.argument(
                description="Page size — sent as FHIR `_count` (default 50)."
            ),
        ] = 50,
        offset: OffsetArg = 0,
        sort: SortArg = None,
    ) -> list[FhirLocationType]:
        """Mirrors GET /Location?... — the matches only. `limit` keeps this
        query's original argument name (it is FHIR's `_count`)."""
        result = await _run_search(
            info,
            filters=fhir_filters(
                id=id,
                last_updated=last_updated,
                name=name,
                identifier=identifier,
                status=status,
                operational_status=operational_status,
                type=type,
                address=address,
                address_city=address_city,
                address_state=address_state,
                address_postal_code=address_postal_code,
                address_country=address_country,
                address_use=address_use,
                organization=organization,
                partof=partof,
                endpoint=endpoint,
                near=near,
            ),
            params=params,
            count=limit,
            offset=offset,
            sort=sort,
        )
        return [_location(r) for r in result.matches]
