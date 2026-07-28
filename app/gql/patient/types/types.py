"""
GraphQL response (output) types for the Patient resource, derived from the
existing Pydantic schemas in app/schemas/patient/response.py via
`strawberry.experimental.pydantic`. Patient is the most complex resource in
this API (9 sub-resource types), chosen as the pilot specifically to stress
-test this pattern before it is replicated to the other 14 resources. Input
types live in app/gql/patient/types/input.py — this split mirrors the
app/schemas/patient/{response,input}.py split one layer down.

Every type below carries an explicit `description=`. Strawberry does NOT
promote a class's Python docstring into the GraphQL schema automatically —
`description=` here is what actually shows up in GraphiQL's
introspection-based "Docs" panel, the GraphQL equivalent of REST's Swagger
UI. The docstrings stay alongside as the Python-facing complement.

Naming convention: `<X>Response` (Pydantic) -> `<X>Type` (GraphQL object type).

Declaration order matters — leaf sub-resource types must be declared before
anything that nests them.
"""

import strawberry

from app.schemas.patient.response import (
    PaginatedPatientResponse,
    PatientAddressResponse,
    PatientCommunicationResponse,
    PatientContactRelationshipResponse,
    PatientContactResponse,
    PatientContactTelecomResponse,
    PatientGeneralPractitionerResponse,
    PatientIdentifierResponse,
    PatientLinkResponse,
    PatientNameResponse,
    PatientPhotoResponse,
    PatientResponse,
    PatientTelecomResponse,
)

# ── Response (output) types — leaf sub-resources first ───────────────────────


@strawberry.experimental.pydantic.type(
    model=PatientNameResponse,
    all_fields=True,
    description="A single Patient.name (HumanName) entry.",
)
class PatientNameType:
    """A single Patient.name (HumanName) entry."""


@strawberry.experimental.pydantic.type(
    model=PatientIdentifierResponse,
    all_fields=True,
    description="A single Patient.identifier entry.",
)
class PatientIdentifierType:
    """A single Patient.identifier entry."""


@strawberry.experimental.pydantic.type(
    model=PatientTelecomResponse,
    all_fields=True,
    description="A single Patient.telecom (ContactPoint) entry — phone, email, fax, etc.",
)
class PatientTelecomType:
    """A single Patient.telecom (ContactPoint) entry."""


@strawberry.experimental.pydantic.type(
    model=PatientAddressResponse,
    all_fields=True,
    description="A single Patient.address entry.",
)
class PatientAddressType:
    """A single Patient.address entry."""


@strawberry.experimental.pydantic.type(
    model=PatientPhotoResponse,
    all_fields=True,
    description="A single Patient.photo (Attachment) entry — inline base64 data or a URL reference.",
)
class PatientPhotoType:
    """A single Patient.photo (Attachment) entry."""


@strawberry.experimental.pydantic.type(
    model=PatientContactTelecomResponse,
    all_fields=True,
    description="A single telecom entry nested inside a Patient.contact person.",
)
class PatientContactTelecomType:
    """A single telecom entry nested inside a Patient.contact person."""


@strawberry.experimental.pydantic.type(
    model=PatientContactRelationshipResponse,
    all_fields=True,
    description="A single relationship CodeableConcept nested inside a Patient.contact person — describes how the contact relates to the patient (e.g. next-of-kin, guardian, emergency contact).",
)
class PatientContactRelationshipType:
    """A single relationship CodeableConcept nested inside a Patient.contact person."""


@strawberry.experimental.pydantic.type(
    model=PatientContactResponse,
    all_fields=True,
    description="A single Patient.contact person — a next-of-kin, guardian, or emergency contact, with nested relationship and telecom entries.",
)
class PatientContactType:
    """A single Patient.contact person (references PatientContactRelationshipType/PatientContactTelecomType)."""


@strawberry.experimental.pydantic.type(
    model=PatientCommunicationResponse,
    all_fields=True,
    description="A single Patient.communication language preference entry.",
)
class PatientCommunicationType:
    """A single Patient.communication language preference entry."""


@strawberry.experimental.pydantic.type(
    model=PatientGeneralPractitionerResponse,
    all_fields=True,
    description="A single Patient.generalPractitioner reference to an Organization, Practitioner, or PractitionerRole.",
)
class PatientGeneralPractitionerType:
    """A single Patient.generalPractitioner reference."""


@strawberry.experimental.pydantic.type(
    model=PatientLinkResponse,
    all_fields=True,
    description="A single Patient.link entry to another Patient or RelatedPerson record.",
)
class PatientLinkType:
    """A single Patient.link entry to another Patient or RelatedPerson."""


@strawberry.experimental.pydantic.type(
    model=PatientResponse,
    all_fields=True,
    description=(
        "A full Patient resource, including all nine nested sub-resource arrays: "
        "name, identifier, telecom, address, photo, contact, communication, "
        "generalPractitioner, and link."
    ),
)
class PatientType:
    """A full Patient resource, including all nine nested sub-resource arrays."""


@strawberry.experimental.pydantic.type(
    model=PaginatedPatientResponse,
    all_fields=True,
    description="Paginated envelope returned by the `patients` query — `data` for the current page, plus `total`/`limit`/`offset` for pagination.",
)
class PaginatedPatientType:
    """Paginated envelope returned by the `patients` list query."""


__all__ = [
    "PatientNameType",
    "PatientIdentifierType",
    "PatientTelecomType",
    "PatientAddressType",
    "PatientPhotoType",
    "PatientContactTelecomType",
    "PatientContactRelationshipType",
    "PatientContactType",
    "PatientCommunicationType",
    "PatientGeneralPractitionerType",
    "PatientLinkType",
    "PatientType",
    "PaginatedPatientType",
]
