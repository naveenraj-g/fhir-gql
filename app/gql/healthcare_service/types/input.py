"""
GraphQL input types for the HealthcareService resource.

Mirrors app.gql.organization.types.input/app.gql.location.types.input
exactly — see those modules and app.gql.organization's package docstring
for the overall idea. Declaration order matters for
strawberry.experimental.pydantic: leaf types before the parent model that
references them. `FhirCodeableConceptInput`, `FhirContactPointInput`,
`FhirIdentifierInput`, `FhirReferenceInput`, `FhirPeriodInput` are reused
from app.gql.organization.types.input rather than redeclared —
HealthcareService uses the exact same app.fhir.schemas.datatypes Pydantic
models, so a second strawberry.experimental.pydantic.input registration
for the same model would conflict rather than add anything.
"""

import strawberry
from strawberry.scalars import JSON

from app.fhir.schemas.healthcare_service import (
    FhirAttachment,
    FhirHealthcareServiceAvailableTime,
    FhirHealthcareServiceEligibility,
    FhirHealthcareServiceInput as FhirHealthcareServiceInputSchema,
    FhirHealthcareServiceNotAvailable,
)

# Importing app.gql.organization.types.input ensures FhirCodeableConceptInput/
# FhirContactPointInput/FhirIdentifierInput/FhirReferenceInput/FhirPeriodInput
# are registered before FhirHealthcareServiceInput below — see this
# module's docstring.
import app.gql.organization.types.input  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.input(
    model=FhirAttachment,
    all_fields=True,
    description="Input for HealthcareService.photo.",
)
class FhirAttachmentInput:
    """Input for HealthcareService.photo."""


@strawberry.experimental.pydantic.input(
    model=FhirHealthcareServiceEligibility,
    all_fields=True,
    description="Input for one HealthcareService.eligibility entry.",
)
class FhirHealthcareServiceEligibilityInput:
    """Input for one HealthcareService.eligibility entry."""


@strawberry.experimental.pydantic.input(
    model=FhirHealthcareServiceAvailableTime,
    all_fields=True,
    description="Input for one HealthcareService.availableTime entry.",
)
class FhirHealthcareServiceAvailableTimeInput:
    """Input for one HealthcareService.availableTime entry."""


@strawberry.experimental.pydantic.input(
    model=FhirHealthcareServiceNotAvailable,
    all_fields=True,
    description="Input for one HealthcareService.notAvailable entry.",
)
class FhirHealthcareServiceNotAvailableInput:
    """Input for one HealthcareService.notAvailable entry."""


@strawberry.experimental.pydantic.input(
    model=FhirHealthcareServiceInputSchema,
    all_fields=True,
    description=(
        "Input for createFhirHealthcareService/updateFhirHealthcareService "
        "— a genuine FHIR R4 HealthcareService shape, translated "
        "per-connector on write. See "
        "app.connectors.base.HealthcareServiceWireTranslator."
    ),
)
class FhirHealthcareServiceInput:
    """Input for createFhirHealthcareService/updateFhirHealthcareService."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar, same as Organization's own extension/assigner fields.
    extension: JSON | None = None
