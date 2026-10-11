"""
GraphQL input types for the Location resource, derived from the
Pydantic schemas in the app/schemas/location/input/ package via
`strawberry.experimental.pydantic`. Output types live in
app/gql/location/types/response.py.

Naming convention:
  - `<X>Schema` (Pydantic) -> `<X>Input` (GraphQL input type)
  - Pydantic input schemas that already share a name with the GraphQL
    wrapper class defined here (LocationIdentifierInput, LocationTypeInput,
    LocationAliasInput, LocationTelecomInput,
    LocationHoursOfOperationInput, LocationEndpointInput) are imported under
    a `...Schema` alias so the plain name is free for this module's GraphQL
    class.

Declaration order matters — leaf sub-resource input types are declared
first, `LocationCreateInput`/`LocationPatchInput` last.
"""

import strawberry

# Registers AddressUse/ContactPointSystem/LocationStatus/DayOfWeek/etc. as
# GraphQL enums (side-effect import) — required before wrapping any input
# schema whose fields use them.
import app.gql.enums  # noqa: F401
from app.schemas.location.input import LocationAliasInput as LocationAliasInputSchema
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
    model=LocationAliasInputSchema,
    all_fields=True,
    description="Input for one Location.alias entry.",
)
class LocationAliasInput:
    """Input for one Location.alias entry."""


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
        "Input for `createLocation`. Creates a Location and any combination of its "
        "sub-resources (identifier, type, alias, telecom, hoursOfOperation, endpoint) "
        "atomically in one request. If `managingOrganization` is provided, fhir-server "
        "validates it exists and belongs to the caller's own tenant. If `partOf` is "
        "provided, fhir-server validates it exists and belongs to the caller's own "
        "tenant. `orgId`/`createdBy` are derived from the caller's JWT — do not supply "
        "them (not declared on this input type at all)."
    ),
)
class LocationCreateInput:
    """Input for `createLocation` — mirrors LocationCreateSchema exactly."""


@strawberry.experimental.pydantic.input(
    model=LocationPatchSchema,
    all_fields=True,
    description=(
        "Input for `updateLocation`. Only supplied fields are written; every supplied "
        "sub-resource list (even `[]`) replaces the corresponding rows wholesale. "
        "`partOf` and `managingOrganization` ARE patchable — re-parenting is supported, "
        "revalidated server-side for existence/tenant match, and `partOf` changes are "
        "additionally checked to avoid creating a circular hierarchy "
        "(`extensions.code == 409`). `updatedBy` is derived from the caller's JWT — do "
        "not supply it."
    ),
)
class LocationPatchInput:
    """Input for `updateLocation` — every field optional, at least one must be set."""


# `ListLocationsSchema` is a query-parameter schema, not a mutation
# payload — GraphQL convention is to expose filters via LocationFilterInput
# (app/gql/location/types/filter.py) rather than a wrapped input type here.
# See app/gql/location/queries.py, which imports ListLocationsSchema
# directly from app.schemas.location.input.
__all__ = [
    "LocationAliasInput",
    "LocationCreateInput",
    "LocationEndpointInput",
    "LocationHoursOfOperationInput",
    "LocationIdentifierInput",
    "LocationPatchInput",
    "LocationTelecomInput",
    "LocationTypeInput",
]
