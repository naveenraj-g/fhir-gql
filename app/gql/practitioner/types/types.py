"""
GraphQL response (output) types for the Practitioner resource, derived from
the existing Pydantic schemas in app/schemas/practitioner/response.py via
`strawberry.experimental.pydantic`. Input types live in
app/gql/practitioner/types/input.py — this split mirrors the
app/schemas/practitioner/{response,input}.py split one layer down.

No lazy-loading layer here (unlike app/gql/patient/types/operations/) —
Practitioner's REST only has one fetch, GET /practitioners/{id}, which
already returns all 7 arrays every time (no separate cheap "core" endpoint
to lazy-load against). `PractitionerType` is a single eager type wrapping
the full response, same shape as Organization/Location/HealthcareService.

Naming convention: `<X>Response` (Pydantic) -> `<X>Type` (GraphQL object type).
"""

import strawberry

from app.schemas.practitioner.response import (
    PaginatedPractitionerResponse,
    PractitionerAddressResponse,
    PractitionerCommunicationResponse,
    PractitionerIdentifierResponse,
    PractitionerNameResponse,
    PractitionerPhotoResponse,
    PractitionerQualificationResponse,
    PractitionerResponse,
    PractitionerTelecomResponse,
    QualificationIdentifierResponse,
)

# ── Response (output) types — leaf sub-resources first ───────────────────────


@strawberry.experimental.pydantic.type(
    model=PractitionerNameResponse, all_fields=True,
    description="A single Practitioner.name (HumanName) entry.",
)
class PractitionerNameType:
    """A single Practitioner.name (HumanName) entry."""


@strawberry.experimental.pydantic.type(
    model=PractitionerIdentifierResponse, all_fields=True,
    description="A single Practitioner.identifier entry.",
)
class PractitionerIdentifierType:
    """A single Practitioner.identifier entry."""


@strawberry.experimental.pydantic.type(
    model=PractitionerTelecomResponse, all_fields=True,
    description="A single Practitioner.telecom (ContactPoint) entry.",
)
class PractitionerTelecomType:
    """A single Practitioner.telecom entry."""


@strawberry.experimental.pydantic.type(
    model=PractitionerAddressResponse, all_fields=True,
    description="A single Practitioner.address entry.",
)
class PractitionerAddressType:
    """A single Practitioner.address entry."""


@strawberry.experimental.pydantic.type(
    model=PractitionerPhotoResponse, all_fields=True,
    description="A single Practitioner.photo (Attachment) entry.",
)
class PractitionerPhotoType:
    """A single Practitioner.photo entry."""


@strawberry.experimental.pydantic.type(
    model=QualificationIdentifierResponse, all_fields=True,
    description="A single identifier attached to a Practitioner.qualification entry (e.g. a license number).",
)
class QualificationIdentifierType:
    """A single identifier attached to a Practitioner.qualification entry."""


@strawberry.experimental.pydantic.type(
    model=PractitionerQualificationResponse, all_fields=True,
    description="A single Practitioner.qualification entry — a certification, license, or training record.",
)
class PractitionerQualificationType:
    """A single Practitioner.qualification entry (references QualificationIdentifierType)."""


@strawberry.experimental.pydantic.type(
    model=PractitionerCommunicationResponse, all_fields=True,
    description="A single Practitioner.communication language preference entry.",
)
class PractitionerCommunicationType:
    """A single Practitioner.communication entry."""


@strawberry.experimental.pydantic.type(
    model=PractitionerResponse, all_fields=True,
    description=(
        "A full Practitioner resource, including all seven nested sub-resource arrays: "
        "name, identifier, telecom, address, photo, qualification, and communication."
    ),
)
class PractitionerType:
    """A full Practitioner resource, including all seven nested sub-resource arrays."""


@strawberry.experimental.pydantic.type(
    model=PaginatedPractitionerResponse, all_fields=True,
    description="Paginated envelope returned by the `practitioners` query.",
)
class PaginatedPractitionerType:
    """Paginated envelope returned by the `practitioners` list query."""


__all__ = [
    "PractitionerNameType",
    "PractitionerIdentifierType",
    "PractitionerTelecomType",
    "PractitionerAddressType",
    "PractitionerPhotoType",
    "QualificationIdentifierType",
    "PractitionerQualificationType",
    "PractitionerCommunicationType",
    "PractitionerType",
    "PaginatedPractitionerType",
]
