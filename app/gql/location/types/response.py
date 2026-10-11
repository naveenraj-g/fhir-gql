"""
GraphQL response (output) types for the Location resource, derived from
the Pydantic schemas in the app/schemas/location/response/ package via
`strawberry.experimental.pydantic`. Input types live in
app/gql/location/types/input.py — this split mirrors the
app/schemas/location/{response,input}/ package split one layer down.

Naming convention: `<X>Response` (Pydantic) -> `<X>Type` (GraphQL object type).

Declaration order matters: `strawberry.experimental.pydantic` resolves a
wrapped model's nested-model fields by looking up the nested Pydantic class
in its own registry, which only has entries for classes wrapped *before*
the parent is declared. Leaf sub-resource types are therefore declared
first, the top-level `LocationType` / `PaginatedLocationType` last.
"""

import strawberry

from app.schemas.location.response import (
    LocationAliasResponse,
    LocationEndpointResponse,
    LocationHoursOfOperationResponse,
    LocationIdentifierResponse,
    LocationResponse,
    LocationTelecomResponse,
    LocationTypeResponse,
    PaginatedLocationResponse,
)

# ── Response (output) types — leaf sub-resources first ───────────────────────


@strawberry.experimental.pydantic.type(
    model=LocationIdentifierResponse,
    all_fields=True,
    description="A single Location.identifier entry.",
)
class LocationIdentifierType:
    """A single Location.identifier entry."""


@strawberry.experimental.pydantic.type(
    model=LocationTypeResponse,
    all_fields=True,
    description="A single Location.type CodeableConcept entry categorising the location (e.g. ward, building, room).",
)
class LocationTypeType:
    """A single Location.type CodeableConcept entry."""


@strawberry.experimental.pydantic.type(
    model=LocationAliasResponse,
    all_fields=True,
    description="A single Location.alias entry — an alternative name the location is or was known by.",
)
class LocationAliasType:
    """A single Location.alias entry."""


@strawberry.experimental.pydantic.type(
    model=LocationTelecomResponse,
    all_fields=True,
    description="A single Location.telecom (ContactPoint) entry — phone, email, fax, etc.",
)
class LocationTelecomType:
    """A single Location.telecom (ContactPoint) entry."""


@strawberry.experimental.pydantic.type(
    model=LocationHoursOfOperationResponse,
    all_fields=True,
    description="A single Location.hoursOfOperation entry — the days/times this location is usually open.",
)
class LocationHoursOfOperationType:
    """A single Location.hoursOfOperation entry."""


@strawberry.experimental.pydantic.type(
    model=LocationEndpointResponse,
    all_fields=True,
    description="A single Location.endpoint reference to a technical endpoint associated with the location.",
)
class LocationEndpointType:
    """A single Location.endpoint reference."""


@strawberry.experimental.pydantic.type(
    model=LocationResponse,
    all_fields=True,
    description="A full Location resource, including all nested sub-resource arrays (identifiers, types, aliases, telecoms, hours of operation, endpoints).",
)
class LocationType:
    """A full Location resource, including all nested sub-resource arrays."""


@strawberry.experimental.pydantic.type(
    model=PaginatedLocationResponse,
    all_fields=True,
    description="Paginated envelope returned by the `locations` query — `data` for the current page, plus `total`/`limit`/`offset` for pagination.",
)
class PaginatedLocationType:
    """Paginated envelope returned by the `locations` list query."""


__all__ = [
    "LocationAliasType",
    "LocationEndpointType",
    "LocationHoursOfOperationType",
    "LocationIdentifierType",
    "LocationTelecomType",
    "LocationType",
    "LocationTypeType",
    "PaginatedLocationType",
]
