"""
GraphQL object (output) types for the HealthcareService resource.

One canonical, genuinely FHIR R4-shaped HealthcareService — the same shape
regardless of which connector (internal, medplum, ...) is actually active;
mirrors app.gql.organization.types.response/app.gql.location.types.response
exactly — see those modules and app.gql.organization's package docstring
for the overall idea, and app.connectors.base.HealthcareServiceWireTranslator
for how each connector's own wire conventions get bridged to this one
canonical shape.

Declaration order matters for strawberry.experimental.pydantic: leaf types
before the parent model that references them. `FhirCodeableConceptType`,
`FhirContactPointType`, `FhirIdentifierType`, `FhirReferenceType`,
`FhirMetaType`, `FhirPeriodType` are NOT redeclared here — they're the
exact same leaf types app.gql.organization.types.response already declares
from the exact same app.fhir.schemas.datatypes models, so reusing those
avoids strawberry registering two distinct GraphQL types for what is
structurally one Pydantic model.
"""

import strawberry
from strawberry.scalars import JSON

from app.fhir.schemas.healthcare_service import (
    FhirAttachment,
    FhirHealthcareServiceAvailableTime,
    FhirHealthcareServiceEligibility,
    FhirHealthcareServiceNotAvailable,
    FhirHealthcareServiceResponse,
)

# Importing app.gql.organization.types.response ensures FhirCodeableConceptType/
# FhirContactPointType/FhirIdentifierType/FhirReferenceType/FhirMetaType/
# FhirPeriodType are registered before FhirHealthcareServiceType below —
# see this module's docstring.
import app.gql.organization.types.response  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.type(
    model=FhirAttachment,
    all_fields=True,
    description="HealthcareService.photo — facilitates quick identification of the service.",
)
class FhirAttachmentType:
    """HealthcareService.photo."""


@strawberry.experimental.pydantic.type(
    model=FhirHealthcareServiceEligibility,
    all_fields=True,
    description="One HealthcareService.eligibility entry.",
)
class FhirHealthcareServiceEligibilityType:
    """One HealthcareService.eligibility entry."""


@strawberry.experimental.pydantic.type(
    model=FhirHealthcareServiceAvailableTime,
    all_fields=True,
    description="One HealthcareService.availableTime entry.",
)
class FhirHealthcareServiceAvailableTimeType:
    """One HealthcareService.availableTime entry."""


@strawberry.experimental.pydantic.type(
    model=FhirHealthcareServiceNotAvailable,
    all_fields=True,
    description="One HealthcareService.notAvailable entry.",
)
class FhirHealthcareServiceNotAvailableType:
    """One HealthcareService.notAvailable entry."""


@strawberry.experimental.pydantic.type(
    model=FhirHealthcareServiceResponse,
    all_fields=True,
    description=(
        "A full FHIR R4 HealthcareService resource — the one canonical "
        "shape returned regardless of which connector (internal, medplum, "
        "...) is active."
    ),
)
class FhirHealthcareServiceType:
    """A full FHIR R4 HealthcareService resource."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar, same as Organization's own extension/assigner fields.
    extension: JSON | None
