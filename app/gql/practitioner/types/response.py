"""
GraphQL object (output) types for the Practitioner resource.

One canonical, genuinely FHIR R4-shaped Practitioner — the same shape
regardless of which connector (internal, medplum, ...) is actually active;
mirrors app.gql.organization.types.response/app.gql.location.types.response/
app.gql.healthcare_service.types.response exactly — see those modules and
app.gql.organization's package docstring for the overall idea, and
app.connectors.base.PractitionerWireTranslator for how each connector's own
wire conventions get bridged to this one canonical shape.

Declaration order matters for strawberry.experimental.pydantic: leaf types
before the parent model that references them. `FhirCodeableConceptType`,
`FhirContactPointType`, `FhirAddressType`, `FhirHumanNameType`,
`FhirIdentifierType`, `FhirReferenceType`, `FhirMetaType`, `FhirPeriodType`
are NOT redeclared here — they're the exact same leaf types
app.gql.organization.types.response already declares from the exact same
app.fhir.schemas.datatypes models, so reusing those avoids strawberry
registering two distinct GraphQL types for what is structurally one
Pydantic model. `FhirAttachmentType` similarly reuses the one
app.gql.healthcare_service.types.response already declares from the now-
shared app.fhir.schemas.datatypes.FhirAttachment model.
"""

import strawberry
from strawberry.scalars import JSON

from app.fhir.schemas.practitioner import (
    FhirPractitionerQualification,
    FhirPractitionerResponse,
)

# Importing these ensures FhirCodeableConceptType/FhirContactPointType/
# FhirAddressType/FhirHumanNameType/FhirIdentifierType/FhirReferenceType/
# FhirMetaType/FhirPeriodType and FhirAttachmentType are registered before
# FhirPractitionerType below — see this module's docstring.
import app.gql.healthcare_service.types.response  # noqa: F401
import app.gql.organization.types.response  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.type(
    model=FhirPractitionerQualification,
    all_fields=True,
    description="One Practitioner.qualification entry.",
)
class FhirPractitionerQualificationType:
    """One Practitioner.qualification entry."""


@strawberry.experimental.pydantic.type(
    model=FhirPractitionerResponse,
    all_fields=True,
    description=(
        "A full FHIR R4 Practitioner resource — the one canonical shape "
        "returned regardless of which connector (internal, medplum, ...) is "
        "active."
    ),
)
class FhirPractitionerType:
    """A full FHIR R4 Practitioner resource."""

    extension: JSON | None
