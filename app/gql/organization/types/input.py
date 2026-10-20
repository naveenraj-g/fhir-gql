"""
GraphQL input types for the Organization resource.

Object (output) types and input types are declared from the same
underlying Pydantic models (app.connectors.internal.schemas.organization.
fhir_schemas) but are two distinct sets of strawberry classes — GraphQL
itself requires separate Input types, they can't be reused as plain object
types or vice versa. Declaration order matters for
strawberry.experimental.pydantic: leaf types before the parent model that
references them.
"""

import strawberry
from strawberry.scalars import JSON

from app.connectors.internal.schemas.organization.fhir_schemas import (
    FhirAddress,
    FhirCodeableConcept,
    FhirCoding,
    FhirContactPoint,
    FhirHumanName,
    FhirIdentifier,
    FhirOrganizationInput as FhirOrganizationInputSchema,
    FhirOrgContact,
    FhirPeriod,
    FhirReference,
)

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.input(
    model=FhirCoding, all_fields=True, description="Input for a single Coding entry."
)
class FhirCodingInput:
    """Input for a single Coding entry (system/code/display)."""


@strawberry.experimental.pydantic.input(
    model=FhirCodeableConcept,
    all_fields=True,
    description="Input for a single CodeableConcept — coding(s) plus free text.",
)
class FhirCodeableConceptInput:
    """Input for a single CodeableConcept."""


@strawberry.experimental.pydantic.input(
    model=FhirPeriod,
    all_fields=True,
    description="Input for a single Period — start/end of a validity window.",
)
class FhirPeriodInput:
    """Input for a single Period."""


@strawberry.experimental.pydantic.input(
    model=FhirIdentifier,
    all_fields=True,
    description="Input for a single Organization.identifier entry.",
)
class FhirIdentifierInput:
    """Input for a single Organization.identifier entry."""

    assigner: JSON | None = None


@strawberry.experimental.pydantic.input(
    model=FhirContactPoint,
    all_fields=True,
    description="Input for a single ContactPoint entry (telecom).",
)
class FhirContactPointInput:
    """Input for a single ContactPoint entry."""


@strawberry.experimental.pydantic.input(
    model=FhirAddress,
    all_fields=True,
    description="Input for a single Address entry.",
)
class FhirAddressInput:
    """Input for a single Address entry."""


@strawberry.experimental.pydantic.input(
    model=FhirHumanName,
    all_fields=True,
    description="Input for a single HumanName entry.",
)
class FhirHumanNameInput:
    """Input for a single HumanName entry."""


@strawberry.experimental.pydantic.input(
    model=FhirOrgContact,
    all_fields=True,
    description="Input for a single Organization.contact entry.",
)
class FhirOrgContactInput:
    """Input for a single Organization.contact entry."""


@strawberry.experimental.pydantic.input(
    model=FhirReference,
    all_fields=True,
    description="Input for a single Reference entry (partOf, endpoint).",
)
class FhirReferenceInput:
    """Input for a single Reference entry."""


@strawberry.experimental.pydantic.input(
    model=FhirOrganizationInputSchema,
    all_fields=True,
    description=(
        "Input for createFhirOrganization/updateFhirOrganization — a "
        "genuine FHIR R4 Organization shape, translated per-connector on "
        "write. See app.connectors.base.OrganizationWireTranslator."
    ),
)
class FhirOrganizationInput:
    """Input for createFhirOrganization/updateFhirOrganization."""

    extension: JSON | None = None
