"""
GraphQL object (output) types for the Observation resource. Mirrors
app.gql.medication_request.types.response's overall pattern — see that
module and app.gql.organization's package docstring for the overall
idea.

No recursive types here — every nested type is declared in strict
leaf-first order, so no `strawberry.lazy()` override is needed anywhere.

`FhirCodeableConceptType`, `FhirIdentifierType`, `FhirReferenceType`,
`FhirMetaType`, `FhirPeriodType` are NOT redeclared — reused from
app.gql.organization.types.response. `FhirAnnotationType` IS new
(local, duplicate definition — same situation as
app.gql.medication_request's own copy).

Every Quantity/Range/Ratio/SampledData-shaped field — on the root
resource, on `referenceRange` (root AND component), and on
`component`'s own `value[x]` — is rendered as raw `JSON` rather than a
nested strawberry type. See app.fhir.schemas.observation's module
docstring for the confirmed strawberry nested-pydantic-type bug this
sidesteps. There is therefore no local `FhirQuantityType`/
`FhirRangeType`/`FhirRatioType`/`FhirSampledDataType` anywhere in this
resource's GraphQL layer at all — same conclusion as
app.gql.medication_request.types.response.
"""

from strawberry.scalars import JSON

import strawberry

from app.fhir.schemas.observation import (
    FhirAnnotation,
    FhirObservationComponent,
    FhirObservationReferenceRange,
    FhirObservationResponse,
)

# Importing this ensures FhirCodeableConceptType/FhirIdentifierType/
# FhirReferenceType/FhirMetaType/FhirPeriodType are registered before
# FhirObservationType below — see this module's docstring.
import app.gql.organization.types.response  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.type(
    model=FhirAnnotation,
    all_fields=True,
    description="FHIR R4 Annotation — Observation.note entry.",
)
class FhirAnnotationType:
    """FHIR R4 Annotation."""


@strawberry.experimental.pydantic.type(
    model=FhirObservationReferenceRange,
    all_fields=True,
    description="Observation.referenceRange entry — reused identically for Observation.component.referenceRange.",
)
class FhirObservationReferenceRangeType:
    """Observation.referenceRange entry."""

    low: JSON | None
    high: JSON | None
    age: JSON | None


@strawberry.experimental.pydantic.type(
    model=FhirObservationComponent,
    all_fields=True,
    description="Observation.component entry.",
)
class FhirObservationComponentType:
    """Observation.component entry."""

    valueQuantity: JSON | None
    valueRange: JSON | None
    valueRatio: JSON | None
    valueSampledData: JSON | None


@strawberry.experimental.pydantic.type(
    model=FhirObservationResponse,
    all_fields=True,
    description=(
        "A full FHIR R4 Observation resource — the one canonical shape "
        "returned regardless of which connector (internal, medplum, ...) is "
        "active."
    ),
)
class FhirObservationType:
    """A full FHIR R4 Observation resource."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar.
    extension: JSON | None
    effectiveTiming: JSON | None
    valueQuantity: JSON | None
    valueRange: JSON | None
    valueRatio: JSON | None
    valueSampledData: JSON | None
