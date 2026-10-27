"""
GraphQL input types for the Location resource.

Mirrors app.gql.organization.types.input exactly — see that module and
app.gql.organization's package docstring for the overall idea. Declaration
order matters for strawberry.experimental.pydantic: leaf types before the
parent model that references them. `FhirIdentifierInput`,
`FhirCodeableConceptInput`, `FhirContactPointInput`, `FhirAddressInput`,
`FhirReferenceInput` are reused from app.gql.organization.types.input
rather than redeclared — Location uses the exact same
app.fhir.schemas.datatypes Pydantic models, so a second
strawberry.experimental.pydantic.input registration for the same model
would conflict rather than add anything.
"""

import strawberry
from strawberry.scalars import JSON

# Importing app.gql.organization.types.input ensures FhirIdentifierInput/
# FhirCodeableConceptInput/FhirContactPointInput/FhirAddressInput/
# FhirReferenceInput/FhirCodingInput are registered before FhirLocationInput
# below — see this module's docstring.
import app.gql.organization.types.input  # noqa: F401
from app.fhir.schemas.location import (
    FhirLocationHoursOfOperation,
    FhirLocationPosition,
)
from app.fhir.schemas.location import (
    FhirLocationInput as FhirLocationInputSchema,
)

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.input(
    model=FhirLocationPosition,
    all_fields=True,
    description="Input for Location.position — the absolute geographic location.",
)
class FhirLocationPositionInput:
    """Input for Location.position."""


@strawberry.experimental.pydantic.input(
    model=FhirLocationHoursOfOperation,
    all_fields=True,
    description="Input for one Location.hoursOfOperation entry.",
)
class FhirLocationHoursOfOperationInput:
    """Input for one Location.hoursOfOperation entry."""


@strawberry.experimental.pydantic.input(
    model=FhirLocationInputSchema,
    all_fields=True,
    description=(
        "Input for createFhirLocation/updateFhirLocation — a genuine FHIR "
        "R4 Location shape, translated per-connector on write. See "
        "app.connectors.base.LocationWireTranslator."
    ),
)
class FhirLocationInput:
    """Input for createFhirLocation/updateFhirLocation."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar, same as Organization's own extension/assigner fields.
    extension: JSON | None = None
