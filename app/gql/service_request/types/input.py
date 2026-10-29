"""
GraphQL input types for the ServiceRequest resource. Mirrors
app.gql.service_request.types.response's overall pattern.
"""

from strawberry.scalars import JSON

import strawberry

from app.fhir.schemas.service_request import (
    FhirAnnotation,
    FhirQuantity,
    FhirServiceRequestInput as FhirServiceRequestInputSchema,
)

# Importing this ensures FhirCodeableConceptInput/FhirIdentifierInput/
# FhirReferenceInput/FhirPeriodInput are registered before
# FhirServiceRequestInput below.
import app.gql.organization.types.input  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.input(
    model=FhirQuantity,
    all_fields=True,
    description="Input for a FHIR R4 Quantity.",
)
class FhirQuantityInput:
    """Input for a FHIR R4 Quantity."""


@strawberry.experimental.pydantic.input(
    model=FhirAnnotation,
    all_fields=True,
    description="Input for one FHIR R4 Annotation — ServiceRequest.note entry.",
)
class FhirAnnotationInput:
    """Input for one FHIR R4 Annotation."""


@strawberry.experimental.pydantic.input(
    model=FhirServiceRequestInputSchema,
    all_fields=True,
    description=(
        "Input for createFhirServiceRequest/updateFhirServiceRequest — a "
        "genuine FHIR R4 ServiceRequest shape, translated per-connector on "
        "write."
    ),
)
class FhirServiceRequestInput:
    """Input for createFhirServiceRequest/updateFhirServiceRequest."""

    extension: JSON | None = None
    quantityRatio: JSON | None = None
    quantityRange: JSON | None = None
    occurrenceTiming: JSON | None = None
