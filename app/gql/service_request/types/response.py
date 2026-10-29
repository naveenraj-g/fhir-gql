"""
GraphQL object (output) types for the ServiceRequest resource. Mirrors
app.gql.questionnaire_response.types.response's overall pattern — see
that module and app.gql.organization's package docstring for the overall
idea.

No recursive types here (unlike Questionnaire/QuestionnaireResponse) —
every nested type is declared in strict leaf-first order, so no
`strawberry.lazy()` override is needed anywhere.

`FhirCodeableConceptType`, `FhirIdentifierType`, `FhirReferenceType`,
`FhirMetaType`, `FhirPeriodType` are NOT redeclared — reused from
app.gql.organization.types.response. `FhirQuantityType`/`FhirAnnotationType`
ARE new.

`quantityRatio` is rendered as raw `JSON` rather than a nested
`FhirRatioType` — nesting a second `@strawberry.experimental.pydantic.type`
(`FhirQuantityType`) inside another one (`FhirRatio`'s own numerator/
denominator) hits a confirmed-live strawberry bug: the auto-generated
`from_pydantic()` conversion produces a `FhirQuantityType` instance that
GraphQL's own runtime type check then rejects with "Expected value of
type 'FhirQuantityType' but got: <FhirQuantityType instance>" — same
class by name, but not `is` the registered one. `quantityQuantity` (a
*direct* field on this type, not nested inside another pydantic-wrapped
type) hits no such issue, so it keeps its real `FhirQuantityType`.
`quantityRange`/`occurrenceTiming` were already raw JSON for unrelated
reasons (no dedicated Range/Timing type at all) — `quantityRatio` simply
joins them rather than fighting the nested-type bug.
"""

from strawberry.scalars import JSON

import strawberry

from app.fhir.schemas.service_request import (
    FhirAnnotation,
    FhirQuantity,
    FhirServiceRequestResponse,
)

# Importing this ensures FhirCodeableConceptType/FhirIdentifierType/
# FhirReferenceType/FhirMetaType/FhirPeriodType are registered before
# FhirServiceRequestType below — see this module's docstring.
import app.gql.organization.types.response  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.type(
    model=FhirQuantity,
    all_fields=True,
    description="FHIR R4 Quantity.",
)
class FhirQuantityType:
    """FHIR R4 Quantity."""


@strawberry.experimental.pydantic.type(
    model=FhirAnnotation,
    all_fields=True,
    description="FHIR R4 Annotation — ServiceRequest.note entry.",
)
class FhirAnnotationType:
    """FHIR R4 Annotation."""


@strawberry.experimental.pydantic.type(
    model=FhirServiceRequestResponse,
    all_fields=True,
    description=(
        "A full FHIR R4 ServiceRequest resource — the one canonical shape "
        "returned regardless of which connector (internal, medplum, ...) is "
        "active."
    ),
)
class FhirServiceRequestType:
    """A full FHIR R4 ServiceRequest resource."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar.
    extension: JSON | None
    quantityRatio: JSON | None
    quantityRange: JSON | None
    occurrenceTiming: JSON | None
