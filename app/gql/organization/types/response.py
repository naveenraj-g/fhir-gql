"""
GraphQL object (output) types for the Organization resource.

One canonical, genuinely FHIR R4-shaped Organization — the same shape
regardless of which connector (internal, medplum, ...) is actually active;
see app.gql.organization's package docstring for the overall idea and
app.connectors.base.OrganizationWireTranslator for how each connector's own
wire conventions get bridged to this one canonical shape.

Declaration order matters for strawberry.experimental.pydantic: leaf types
before the parent model that references them.
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
    FhirOrgContact,
    FhirOrgResponse,
    FhirPeriod,
    FhirReference,
)

# ── Leaf sub-resources first ─────────────────────────────────────────────────


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

    # Pydantic types this as a bare dict — strawberry.experimental.pydantic
    # can't infer a GraphQL type for a bare `dict`/`list[dict]` field, so it
    # must be overridden explicitly as the JSON scalar.
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
        "active."
    ),
)
class FhirOrganizationType:
    """A full FHIR R4 Organization resource."""

    extension: JSON | None
