"""
GraphQL input types for the PractitionerRole resource.

Mirrors app.gql.organization.types.input/app.gql.location.types.input/
app.gql.healthcare_service.types.input/app.gql.practitioner.types.input
exactly — see those modules and app.gql.organization's package docstring
for the overall idea. Declaration order matters for
strawberry.experimental.pydantic: leaf types before the parent model that
references them. `FhirCodeableConceptInput`, `FhirContactPointInput`,
`FhirIdentifierInput`, `FhirReferenceInput`, `FhirPeriodInput` are reused
from app.gql.organization.types.input rather than redeclared —
PractitionerRole uses the exact same underlying Pydantic models, so a
second strawberry.experimental.pydantic.input registration for the same
model would conflict rather than add anything.
"""

import strawberry
from strawberry.scalars import JSON

from app.fhir.schemas.practitioner_role import (
    FhirPractitionerRoleAvailableTime,
    FhirPractitionerRoleInput as FhirPractitionerRoleInputSchema,
    FhirPractitionerRoleNotAvailable,
)

# Importing this ensures FhirCodeableConceptInput/FhirContactPointInput/
# FhirIdentifierInput/FhirReferenceInput/FhirPeriodInput are registered
# before FhirPractitionerRoleInput below — see this module's docstring.
import app.gql.organization.types.input  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.input(
    model=FhirPractitionerRoleAvailableTime,
    all_fields=True,
    description="Input for one PractitionerRole.availableTime entry.",
)
class FhirPractitionerRoleAvailableTimeInput:
    """Input for one PractitionerRole.availableTime entry."""


@strawberry.experimental.pydantic.input(
    model=FhirPractitionerRoleNotAvailable,
    all_fields=True,
    description="Input for one PractitionerRole.notAvailable entry.",
)
class FhirPractitionerRoleNotAvailableInput:
    """Input for one PractitionerRole.notAvailable entry."""


@strawberry.experimental.pydantic.input(
    model=FhirPractitionerRoleInputSchema,
    all_fields=True,
    description=(
        "Input for createFhirPractitionerRole/updateFhirPractitionerRole — "
        "a genuine FHIR R4 PractitionerRole shape, translated per-connector "
        "on write. See app.connectors.base.PractitionerRoleWireTranslator."
    ),
)
class FhirPractitionerRoleInput:
    """Input for createFhirPractitionerRole/updateFhirPractitionerRole."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar, same as Organization's own extension/assigner fields.
    extension: JSON | None = None
