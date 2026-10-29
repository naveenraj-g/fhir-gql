"""
GraphQL input types for the Observation resource. Mirrors
app.gql.observation.types.response's overall pattern — including
exposing every Quantity/Range/Ratio/SampledData-shaped sub-field as
raw JSON (see that module's docstring for the confirmed strawberry
nested-pydantic-type bug this sidesteps). No local `FhirQuantityInput`/
`FhirRangeInput`/`FhirRatioInput`/`FhirSampledDataInput` exists for the
same reason there's no corresponding `*Type`.
"""

from strawberry.scalars import JSON

import strawberry

from app.fhir.schemas.observation import (
    FhirAnnotation,
    FhirObservationComponent,
    FhirObservationInput as FhirObservationInputSchema,
    FhirObservationReferenceRange,
)

# Importing this ensures FhirCodeableConceptInput/FhirIdentifierInput/
# FhirReferenceInput/FhirPeriodInput are registered before
# FhirObservationInput below.
import app.gql.organization.types.input  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.input(
    model=FhirAnnotation,
    all_fields=True,
    description="Input for one FHIR R4 Annotation — Observation.note entry.",
)
class FhirAnnotationInput:
    """Input for one FHIR R4 Annotation."""


@strawberry.experimental.pydantic.input(
    model=FhirObservationReferenceRange,
    all_fields=True,
    description="Input for one Observation.referenceRange entry — reused identically for Observation.component.referenceRange.",
)
class FhirObservationReferenceRangeInput:
    """Input for one Observation.referenceRange entry."""

    low: JSON | None = None
    high: JSON | None = None
    age: JSON | None = None


@strawberry.experimental.pydantic.input(
    model=FhirObservationComponent,
    all_fields=True,
    description="Input for one Observation.component entry.",
)
class FhirObservationComponentInput:
    """Input for one Observation.component entry."""

    valueQuantity: JSON | None = None
    valueRange: JSON | None = None
    valueRatio: JSON | None = None
    valueSampledData: JSON | None = None


@strawberry.experimental.pydantic.input(
    model=FhirObservationInputSchema,
    all_fields=True,
    description=(
        "Input for createFhirObservation/updateFhirObservation — a genuine "
        "FHIR R4 Observation shape, translated per-connector on write."
    ),
)
class FhirObservationInput:
    """Input for createFhirObservation/updateFhirObservation."""

    extension: JSON | None = None
    effectiveTiming: JSON | None = None
    valueQuantity: JSON | None = None
    valueRange: JSON | None = None
    valueRatio: JSON | None = None
    valueSampledData: JSON | None = None
