"""
GraphQL input types for the Practitioner resource.

Mirrors app.gql.organization.types.input/app.gql.location.types.input/
app.gql.healthcare_service.types.input exactly — see those modules and
app.gql.organization's package docstring for the overall idea. Declaration
order matters for strawberry.experimental.pydantic: leaf types before the
parent model that references them. `FhirIdentifierInput`,
`FhirCodeableConceptInput`, `FhirContactPointInput`, `FhirAddressInput`,
`FhirHumanNameInput`, `FhirReferenceInput` are reused from
app.gql.organization.types.input, and `FhirAttachmentInput` from
app.gql.healthcare_service.types.input, rather than redeclared —
Practitioner uses the exact same underlying Pydantic models, so a second
strawberry.experimental.pydantic.input registration for the same model
would conflict rather than add anything.
"""

import strawberry
from strawberry.scalars import JSON

from app.fhir.schemas.practitioner import FhirPractitionerQualification
from app.fhir.schemas.practitioner import (
    FhirPractitionerInput as FhirPractitionerInputSchema,
)

# Importing these ensures FhirIdentifierInput/FhirCodeableConceptInput/
# FhirContactPointInput/FhirAddressInput/FhirHumanNameInput/
# FhirReferenceInput/FhirCodingInput and FhirAttachmentInput are registered
# before FhirPractitionerInput below — see this module's docstring.
import app.gql.healthcare_service.types.input  # noqa: F401
import app.gql.organization.types.input  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.input(
    model=FhirPractitionerQualification,
    all_fields=True,
    description="Input for one Practitioner.qualification entry.",
)
class FhirPractitionerQualificationInput:
    """Input for one Practitioner.qualification entry."""


@strawberry.experimental.pydantic.input(
    model=FhirPractitionerInputSchema,
    all_fields=True,
    description=(
        "Input for createFhirPractitioner/updateFhirPractitioner — a "
        "genuine FHIR R4 Practitioner shape, translated per-connector on "
        "write. See app.connectors.base.PractitionerWireTranslator."
    ),
)
class FhirPractitionerInput:
    """Input for createFhirPractitioner/updateFhirPractitioner."""

    extension: JSON | None = None
