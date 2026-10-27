"""
GraphQL object (output) types for the PractitionerRole resource.

One canonical, genuinely FHIR R4-shaped PractitionerRole — the same shape
regardless of which connector (internal, medplum, ...) is actually active;
mirrors app.gql.organization.types.response/app.gql.location.types.response/
app.gql.healthcare_service.types.response/app.gql.practitioner.types.response
exactly — see those modules and app.gql.organization's package docstring for
the overall idea, and app.connectors.base.PractitionerRoleWireTranslator for
how each connector's own wire conventions get bridged to this one canonical
shape.

Declaration order matters for strawberry.experimental.pydantic: leaf types
before the parent model that references them. `FhirCodeableConceptType`,
`FhirContactPointType`, `FhirIdentifierType`, `FhirReferenceType`,
`FhirMetaType`, `FhirPeriodType` are NOT redeclared here — they're the exact
same leaf types app.gql.organization.types.response already declares from
the exact same app.fhir.schemas.datatypes models, so reusing those avoids
strawberry registering two distinct GraphQL types for what is structurally
one Pydantic model.
"""

import strawberry
from strawberry.scalars import JSON

from app.fhir.schemas.practitioner_role import (
    FhirPractitionerRoleAvailableTime,
    FhirPractitionerRoleNotAvailable,
    FhirPractitionerRoleResponse,
)

# Importing this ensures FhirCodeableConceptType/FhirContactPointType/
# FhirIdentifierType/FhirReferenceType/FhirMetaType/FhirPeriodType are
# registered before FhirPractitionerRoleType below — see this module's
# docstring.
import app.gql.organization.types.response  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.type(
    model=FhirPractitionerRoleAvailableTime,
    all_fields=True,
    description="One PractitionerRole.availableTime entry.",
)
class FhirPractitionerRoleAvailableTimeType:
    """One PractitionerRole.availableTime entry."""


@strawberry.experimental.pydantic.type(
    model=FhirPractitionerRoleNotAvailable,
    all_fields=True,
    description="One PractitionerRole.notAvailable entry.",
)
class FhirPractitionerRoleNotAvailableType:
    """One PractitionerRole.notAvailable entry."""


@strawberry.experimental.pydantic.type(
    model=FhirPractitionerRoleResponse,
    all_fields=True,
    description=(
        "A full FHIR R4 PractitionerRole resource — the one canonical shape "
        "returned regardless of which connector (internal, medplum, ...) is "
        "active."
    ),
)
class FhirPractitionerRoleType:
    """A full FHIR R4 PractitionerRole resource."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar, same as Organization's own extension/assigner fields.
    extension: JSON | None
