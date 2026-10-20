"""
GraphQL object + input types for the universal-FHIR-GraphQL experiment's
Organization resource. See app.connectors.universal's package docstring for
the overall idea, and app.connectors.universal.translators for how each
connector's own wire conventions get bridged to this one canonical shape.

Declaration order matters for strawberry.experimental.pydantic, same reason
as app.connectors.internal.gql.organization.types.response: leaf types
before the parent model that references them. Object (output) types and
input types are declared from the same underlying Pydantic models
(app.connectors.universal.schemas) but are two distinct sets of strawberry
classes — GraphQL itself requires separate Input types, they can't be
reused as plain object types or vice versa.
"""

import strawberry
from strawberry.scalars import JSON

from app.connectors.universal.schemas import (
    FhirAddress,
    FhirCodeableConcept,
    FhirCoding,
    FhirContactPoint,
    FhirHumanName,
    FhirIdentifier,
    FhirOrgContact,
    FhirOrgResponse,
    FhirPeriod,
    FhirReference,
)
from app.connectors.universal.schemas import (
    FhirOrganizationInput as FhirOrganizationInputSchema,
)

# ── Object (output) types — leaf sub-resources first ────────────────────────


@strawberry.experimental.pydantic.type(
    model=FhirCoding, all_fields=True, description="A single Coding entry."
)
class FhirCodingType:
    """A single Coding entry (system/code/display)."""


@strawberry.experimental.pydantic.type(
    model=FhirCodeableConcept,
    all_fields=True,
    description="A single CodeableConcept — coding(s) plus free text.",
)
class FhirCodeableConceptType:
    """A single CodeableConcept."""


@strawberry.experimental.pydantic.type(
    model=FhirPeriod,
    all_fields=True,
    description="A single Period — start/end of a validity window.",
)
class FhirPeriodType:
    """A single Period."""


@strawberry.experimental.pydantic.type(
    model=FhirIdentifier,
    all_fields=True,
    description="A single Organization.identifier entry.",
)
class FhirIdentifierType:
    """A single Organization.identifier entry."""

    # Pydantic types this as a bare dict — same JSON-scalar override used by
    # app.connectors.internal.gql.organization.types.response.OrganizationType.extension.
    assigner: JSON | None


@strawberry.experimental.pydantic.type(
    model=FhirContactPoint,
    all_fields=True,
    description="A single ContactPoint entry (telecom).",
)
class FhirContactPointType:
    """A single ContactPoint entry."""


@strawberry.experimental.pydantic.type(
    model=FhirAddress, all_fields=True, description="A single Address entry."
)
class FhirAddressType:
    """A single Address entry."""


@strawberry.experimental.pydantic.type(
    model=FhirHumanName, all_fields=True, description="A single HumanName entry."
)
class FhirHumanNameType:
    """A single HumanName entry."""


@strawberry.experimental.pydantic.type(
    model=FhirOrgContact,
    all_fields=True,
    description="A single Organization.contact entry.",
)
class FhirOrgContactType:
    """A single Organization.contact entry."""


@strawberry.experimental.pydantic.type(
    model=FhirReference,
    all_fields=True,
    description="A single Reference entry (partOf, endpoint).",
)
class FhirReferenceType:
    """A single Reference entry."""


@strawberry.experimental.pydantic.type(
    model=FhirOrgResponse,
    all_fields=True,
    description=(
        "A full FHIR R4 Organization resource — the one canonical shape "
        "returned regardless of which connector (internal, medplum, ...) is "
        "active. See app.connectors.universal's package docstring."
    ),
)
class FhirOrganizationType:
    """A full FHIR R4 Organization resource."""

    extension: JSON | None


# ── Input types — leaf sub-resources first ──────────────────────────────────


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
        "write. See app.connectors.universal.translators."
    ),
)
class FhirOrganizationInput:
    """Input for createFhirOrganization/updateFhirOrganization."""

    extension: JSON | None = None
