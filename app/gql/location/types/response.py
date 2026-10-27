"""
GraphQL object (output) types for the Location resource.

One canonical, genuinely FHIR R4-shaped Location — the same shape
regardless of which connector (internal, medplum, ...) is actually active;
mirrors app.gql.organization.types.response exactly — see that module and
app.gql.organization's package docstring for the overall idea, and
app.connectors.base.LocationWireTranslator for how each connector's own
wire conventions get bridged to this one canonical shape.

Declaration order matters for strawberry.experimental.pydantic: leaf types
before the parent model that references them. `FhirCodingType`,
`FhirCodeableConceptType`, `FhirMetaType`, `FhirContactPointType`,
`FhirAddressType`, `FhirIdentifierType`, `FhirReferenceType` are NOT
redeclared here — they're the exact same leaf types app.gql.organization.types.response
already declares from the exact same app.fhir.schemas.datatypes models, so
reusing those avoids strawberry registering two distinct GraphQL types for
what is structurally one Pydantic model.
"""

import strawberry
from strawberry.scalars import JSON

# Importing app.gql.organization.types.response (even without using its
# names directly) ensures FhirCodingType/FhirCodeableConceptType/
# FhirContactPointType/FhirAddressType/FhirIdentifierType/FhirReferenceType/
# FhirMetaType are registered against their underlying app.fhir.schemas.datatypes
# Pydantic models *before* FhirLocationType below is declared — Location
# reuses those exact same Pydantic classes, so strawberry.experimental.pydantic
# auto-resolves every nested field (identifier, type, telecom, address,
# physicalType, managingOrganization, partOf, endpoint, meta) to the
# already-registered type without any explicit override needed here, the
# same way FhirOrganizationType's own nested fields need none.
import app.gql.organization.types.response  # noqa: F401
from app.fhir.schemas.location import (
    FhirLocationHoursOfOperation,
    FhirLocationPosition,
    FhirLocationResponse,
)

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.type(
    model=FhirLocationPosition,
    all_fields=True,
    description="The absolute geographic location of the Location (WGS84 datum).",
)
class FhirLocationPositionType:
    """Location.position."""


@strawberry.experimental.pydantic.type(
    model=FhirLocationHoursOfOperation,
    all_fields=True,
    description="What days/times during a week a Location is usually open.",
)
class FhirLocationHoursOfOperationType:
    """Location.hoursOfOperation."""


@strawberry.experimental.pydantic.type(
    model=FhirLocationResponse,
    all_fields=True,
    description=(
        "A full FHIR R4 Location resource — the one canonical shape "
        "returned regardless of which connector (internal, medplum, ...) is "
        "active."
    ),
)
class FhirLocationType:
    """A full FHIR R4 Location resource."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar, same as Organization's own extension/assigner fields.
    extension: JSON | None
