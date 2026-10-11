"""
GraphQL filter input for the `locations` list query.

Bundles every Location search parameter (matching fhir-server's
Medplum-mirrored Location search parameter set — see
app/routers/location/core.py's list_locations()) into a single input
object, GraphQL's idiomatic convention for list-query filters — same
pattern as app/gql/organization/types/filter.py's OrganizationFilterInput.

Hand-written as a plain `@strawberry.input` (not derived from
ListLocationsSchema via `strawberry.experimental.pydantic.input`) because
ListLocationsSchema also carries `sort`/`total_mode`/`limit`/`offset` —
pagination/ordering concerns, not filters — which stay as separate
top-level arguments on the `locations` query in queries.py (using the
shared app.gql.common.pagination aliases) rather than living inside this
input.

Every field carries its own `description=` — same documentation bar as
fhir-server's per-parameter `Query()` descriptions.
"""

import strawberry

# Registers AddressUse/LocationStatus/etc. as GraphQL enums (side-effect
# import) — required before referencing them below.
import app.gql.enums  # noqa: F401
from app.gql.enums import AddressUseEnum, LocationStatusEnum


@strawberry.input(description="Filter arguments for the `locations` query.")
class LocationFilterInput:
    name: str | None = strawberry.field(
        default=None,
        description="Partial match against the location name or any alias.",
    )
    identifier: str | None = strawberry.field(
        default=None, description="Exact match on a business identifier value."
    )
    location_status: LocationStatusEnum | None = strawberry.field(
        default=None, description="active|suspended|inactive."
    )
    operational_status: str | None = strawberry.field(
        default=None,
        description="Exact match on the operational status code (e.g. 'U' for Unoccupied).",
    )
    location_type: str | None = strawberry.field(
        default=None,
        description="Exact match on a coded function performed at the location (e.g. 'HOSP').",
    )
    physical_type: str | None = strawberry.field(
        default=None,
        description="Exact match on the physical form code (e.g. 'wi' for Wing, 'ro' for Room).",
    )
    address: str | None = strawberry.field(
        default=None,
        description="Partial match against any Address sub-field (line, city, district, state, country, postalCode, text).",
    )
    address_city: str | None = strawberry.field(
        default=None, description="Filter by address city — partial match."
    )
    address_state: str | None = strawberry.field(
        default=None, description="Filter by address state — partial match."
    )
    address_postal_code: str | None = strawberry.field(
        default=None, description="Filter by address postal code — exact match."
    )
    address_country: str | None = strawberry.field(
        default=None, description="Filter by address country — partial match."
    )
    address_use: AddressUseEnum | None = strawberry.field(
        default=None, description="home|work|temp|old|billing."
    )
    organization: str | None = strawberry.field(
        default=None,
        description="Managing organization, as a FHIR reference string, e.g. 'Organization/190001'.",
    )
    partof: str | None = strawberry.field(
        default=None,
        description="Containing location, as a FHIR reference string, e.g. 'Location/230001'.",
    )
    endpoint: str | None = strawberry.field(
        default=None, description="FHIR reference string, e.g. 'Endpoint/1'."
    )
    near: str | None = strawberry.field(
        default=None,
        description=(
            "Radius search against Location.position, as "
            "'[latitude]|[longitude]|[distance]|[units]' — e.g. "
            "'42.25475478|-83.6945691|11.20|km'. Units default to km; km, m and mi are "
            "accepted. Locations with no recorded position never match."
        ),
    )


__all__ = ["LocationFilterInput"]
