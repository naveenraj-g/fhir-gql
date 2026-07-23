"""
GraphQL input types for the Location resource, derived from the existing
Pydantic schemas in app/schemas/location/input.py via
`strawberry.experimental.pydantic`. Output types live in
app/gql/location/types/types.py.

Naming convention:
  - `<X>Schema` (Pydantic) -> `<X>Input` (GraphQL input type)
  - Pydantic input schemas that already share a name with the GraphQL
    wrapper class defined here (LocationIdentifierInput, LocationTypeInput,
    LocationTelecomInput, LocationHoursOfOperationInput,
    LocationEndpointInput) are imported under a `...Schema` alias so the
    plain name is free for this module's GraphQL class.

Declaration order matters — leaf sub-resource input types are declared
first, `LocationCreateInput`/`LocationPatchInput` last.
"""

import strawberry

# Registers AddressUse/ContactPointSystem/LocationStatus/etc. as GraphQL
# enums (side-effect import) — required before wrapping any input schema
# whose fields use them.
import app.gql.enums  # noqa: F401
from app.schemas.location.input import LocationCreateSchema, LocationPatchSchema
from app.schemas.location.input import (
    LocationEndpointInput as LocationEndpointInputSchema,
)
from app.schemas.location.input import (
    LocationHoursOfOperationInput as LocationHoursOfOperationInputSchema,
)
from app.schemas.location.input import (
    LocationIdentifierInput as LocationIdentifierInputSchema,
)
from app.schemas.location.input import (
    LocationTelecomInput as LocationTelecomInputSchema,
)
from app.schemas.location.input import LocationTypeInput as LocationTypeInputSchema

# ── Input types — leaf sub-resources first ───────────────────────────────────


@strawberry.experimental.pydantic.input(
    model=LocationIdentifierInputSchema,
    all_fields=True,
    description="Input for one Location.identifier entry.",
)
class LocationIdentifierInput:
    """Input for one Location.identifier entry."""


@strawberry.experimental.pydantic.input(
    model=LocationTypeInputSchema,
    all_fields=True,
    description="Input for one Location.type CodeableConcept entry (e.g. ward, building, room).",
)
class LocationTypeInput:
    """Input for one Location.type CodeableConcept entry."""


@strawberry.experimental.pydantic.input(
    model=LocationTelecomInputSchema,
    all_fields=True,
    description="Input for one Location.telecom entry. `system` and `value` are required.",
)
class LocationTelecomInput:
    """Input for one Location.telecom entry."""


@strawberry.experimental.pydantic.input(
    model=LocationHoursOfOperationInputSchema,
    all_fields=True,
    description="Input for one Location.hoursOfOperation entry.",
)
class LocationHoursOfOperationInput:
    """Input for one Location.hoursOfOperation entry."""


@strawberry.experimental.pydantic.input(
    model=LocationEndpointInputSchema,
    all_fields=True,
    description="Input for one Location.endpoint reference.",
)
class LocationEndpointInput:
    """Input for one Location.endpoint reference."""


@strawberry.experimental.pydantic.input(
    model=LocationCreateSchema,
    all_fields=True,
    description=(
        "Input for `createLocation`. `userId` and `orgId` are required for tenant scoping. "
        "If `managingOrganization` is provided, it must reference an existing organization in "
        "the caller's own tenant. If `partOf` is provided, it must reference an existing "
        "Location in the caller's own tenant. `createdBy` is stamped automatically from the "
        "caller's JWT — do not supply it."
    ),
)
class LocationCreateInput:
    """Input for `createLocation` — mirrors LocationCreateSchema, including its `userId`/`orgId` requirement."""


@strawberry.experimental.pydantic.input(
    model=LocationPatchSchema,
    all_fields=True,
    description=(
        "Input for `updateLocation` — every field optional, at least one must be set. Unlike "
        "Organization's immutable `partof`, `partOf` and `managingOrganization` ARE patchable "
        "here — re-parenting is supported, revalidated for existence/tenant match, and `partOf` "
        "changes are additionally checked to avoid creating a circular hierarchy. Array "
        "sub-resources (identifiers, types, telecoms, hoursOfOperation, endpoints) are managed "
        "via delete-and-recreate, not this mutation."
    ),
)
class LocationPatchInput:
    """Input for `updateLocation` — every field optional, at least one must be set (enforced in LocationService)."""


# `ListLocationsSchema` is a query-parameter schema, not a mutation payload —
# GraphQL convention is to expose filters as plain field arguments rather
# than a wrapped input type. See app/gql/location/queries.py, which imports
# it directly from app.schemas.location.input.
__all__ = [
    "LocationIdentifierInput",
    "LocationTypeInput",
    "LocationTelecomInput",
    "LocationHoursOfOperationInput",
    "LocationEndpointInput",
    "LocationCreateInput",
    "LocationPatchInput",
]
