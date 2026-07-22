"""
GraphQL types for the Patient resource, derived from the existing Pydantic
schemas in app/schemas/patient/{response,input}.py via
`strawberry.experimental.pydantic`. Patient is the most complex resource in
this API (9 sub-resource types), chosen as the pilot specifically to stress
-test this pattern before it is replicated to the other 14 resources.

Every type below carries an explicit `description=`. Strawberry does NOT
promote a class's Python docstring into the GraphQL schema automatically —
`description=` here is what actually shows up in GraphiQL's
introspection-based "Docs" panel, the GraphQL equivalent of REST's Swagger
UI. The docstrings stay alongside as the Python-facing complement.

Naming convention (see app/gql/types/organization.py for the same rule):
  - `<X>Response` (Pydantic) -> `<X>Type` (GraphQL object type)
  - `<X>CreateSchema` / `<X>PatchSchema` (Pydantic) -> `<X>CreateInput` / `<X>PatchInput`
  - Pydantic classes that already end in "Input" (ContactRelationshipInput,
    ContactTelecomInput) are imported under a `...Schema` alias so the plain
    name is free for this module's GraphQL wrapper class.

Declaration order matters — see the module docstring in
app/gql/types/organization.py for why leaf sub-resource types must be
declared before anything that nests them.
"""

import strawberry

# Registers AdministrativeGender/HumanNameUse/etc. as GraphQL enums
# (side-effect import) — required before wrapping any input schema whose
# fields use these enums.
import app.gql.enums  # noqa: F401
from app.schemas.patient.input import (
    AddressCreateSchema,
    AddressPatchSchema,
    CommunicationCreateSchema,
    CommunicationPatchSchema,
    ContactCreateSchema,
    ContactPatchSchema,
    GeneralPractitionerCreateSchema,
    GeneralPractitionerPatchSchema,
    IdentifierCreateSchema,
    IdentifierPatchSchema,
    LinkCreateSchema,
    LinkPatchSchema,
    NameCreateSchema,
    NamePatchSchema,
    PatientCreateSchema,
    PatientFullCreateSchema,
    PatientFullPatchSchema,
    PatientPatchSchema,
    PhotoCreateSchema,
    PhotoPatchSchema,
    TelecomCreateSchema,
    TelecomPatchSchema,
)
from app.schemas.patient.input import (
    ContactRelationshipInput as ContactRelationshipInputSchema,
)
from app.schemas.patient.input import (
    ContactTelecomInput as ContactTelecomInputSchema,
)
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


# ── Input types — leaf sub-resources first ───────────────────────────────────


@strawberry.experimental.pydantic.input(
    model=NameCreateSchema,
    all_fields=True,
    description="Input for adding a Patient.name (HumanName) entry. All fields optional — a name with only family or only text is valid FHIR.",
)
class NameCreateInput:
    """Input for adding a Patient.name (HumanName) entry."""


@strawberry.experimental.pydantic.input(
    model=NamePatchSchema,
    all_fields=True,
    description="Input for patching a Patient.name entry — all fields optional, at least one must be set.",
)
class NamePatchInput:
    """Input for patching a Patient.name entry — all fields optional."""


@strawberry.experimental.pydantic.input(
    model=IdentifierCreateSchema,
    all_fields=True,
    description="Input for adding a Patient.identifier entry. `value` is the only required field.",
)
class IdentifierCreateInput:
    """Input for adding a Patient.identifier entry."""


@strawberry.experimental.pydantic.input(
    model=IdentifierPatchSchema,
    all_fields=True,
    description="Input for patching a Patient.identifier entry — all fields optional.",
)
class IdentifierPatchInput:
    """Input for patching a Patient.identifier entry — all fields optional."""


@strawberry.experimental.pydantic.input(
    model=TelecomCreateSchema,
    all_fields=True,
    description="Input for adding a Patient.telecom entry. `system` and `value` are required.",
)
class TelecomCreateInput:
    """Input for adding a Patient.telecom (ContactPoint) entry."""


@strawberry.experimental.pydantic.input(
    model=TelecomPatchSchema,
    all_fields=True,
    description="Input for patching a Patient.telecom entry — all fields optional.",
)
class TelecomPatchInput:
    """Input for patching a Patient.telecom entry — all fields optional."""


@strawberry.experimental.pydantic.input(
    model=AddressCreateSchema,
    all_fields=True,
    description="Input for adding a Patient.address entry. All fields optional — an address may be as minimal as just a city.",
)
class AddressCreateInput:
    """Input for adding a Patient.address entry."""


@strawberry.experimental.pydantic.input(
    model=AddressPatchSchema,
    all_fields=True,
    description="Input for patching a Patient.address entry — all fields optional.",
)
class AddressPatchInput:
    """Input for patching a Patient.address entry — all fields optional."""


@strawberry.experimental.pydantic.input(
    model=PhotoCreateSchema,
    all_fields=True,
    description="Input for adding a Patient.photo entry — inline base64 `data` or a `url` reference.",
)
class PhotoCreateInput:
    """Input for adding a Patient.photo (Attachment) entry."""


@strawberry.experimental.pydantic.input(
    model=PhotoPatchSchema,
    all_fields=True,
    description="Input for patching a Patient.photo entry — all fields optional.",
)
class PhotoPatchInput:
    """Input for patching a Patient.photo entry — all fields optional."""


@strawberry.experimental.pydantic.input(
    model=ContactRelationshipInputSchema,
    all_fields=True,
    description="Input for one relationship CodeableConcept nested inside a Patient.contact person.",
)
class ContactRelationshipInput:
    """Input for one relationship CodeableConcept nested inside a Patient.contact person."""


@strawberry.experimental.pydantic.input(
    model=ContactTelecomInputSchema,
    all_fields=True,
    description="Input for one telecom entry nested inside a Patient.contact person.",
)
class ContactTelecomInput:
    """Input for one telecom entry nested inside a Patient.contact person."""


@strawberry.experimental.pydantic.input(
    model=ContactCreateSchema,
    all_fields=True,
    description="Input for adding a Patient.contact person (next-of-kin/guardian/emergency), with nested relationship and telecom arrays.",
)
class ContactCreateInput:
    """Input for adding a Patient.contact person (references ContactRelationshipInput/ContactTelecomInput)."""


@strawberry.experimental.pydantic.input(
    model=ContactPatchSchema,
    all_fields=True,
    description="Input for patching a Patient.contact person — all fields optional; `relationship`/`telecom` fully replace the existing array when provided, they do not merge.",
)
class ContactPatchInput:
    """Input for patching a Patient.contact person — all fields optional; relationship/telecom fully replace when provided."""


@strawberry.experimental.pydantic.input(
    model=CommunicationCreateSchema,
    all_fields=True,
    description="Input for adding a Patient.communication language preference. `languageCode` (ISO 639-1, e.g. en, fr, de) is required.",
)
class CommunicationCreateInput:
    """Input for adding a Patient.communication language preference entry."""


@strawberry.experimental.pydantic.input(
    model=CommunicationPatchSchema,
    all_fields=True,
    description="Input for patching a Patient.communication entry — all fields optional.",
)
class CommunicationPatchInput:
    """Input for patching a Patient.communication entry — all fields optional."""


@strawberry.experimental.pydantic.input(
    model=GeneralPractitionerCreateSchema,
    all_fields=True,
    description="Input for adding a Patient.generalPractitioner reference. `referenceType` must be Organization, Practitioner, or PractitionerRole.",
)
class GeneralPractitionerCreateInput:
    """Input for adding a Patient.generalPractitioner reference."""


@strawberry.experimental.pydantic.input(
    model=GeneralPractitionerPatchSchema,
    all_fields=True,
    description="Input for patching a Patient.generalPractitioner reference — all fields optional.",
)
class GeneralPractitionerPatchInput:
    """Input for patching a Patient.generalPractitioner reference — all fields optional."""


@strawberry.experimental.pydantic.input(
    model=LinkCreateSchema,
    all_fields=True,
    description="Input for adding a Patient.link entry. `otherType`, `otherId`, and `type` (replaced-by | replaces | refer | seealso) are all required.",
)
class LinkCreateInput:
    """Input for adding a Patient.link entry to another Patient or RelatedPerson."""


@strawberry.experimental.pydantic.input(
    model=LinkPatchSchema,
    all_fields=True,
    description="Input for patching a Patient.link entry — all fields optional.",
)
class LinkPatchInput:
    """Input for patching a Patient.link entry — all fields optional."""


@strawberry.experimental.pydantic.input(
    model=PatientCreateSchema,
    all_fields=True,
    description=(
        "Input for `createPatient`. `userId` and `orgId` are required for tenant scoping; "
        "`createdBy` is stamped automatically from the caller's JWT — do not supply it."
    ),
)
class PatientCreateInput:
    """Input for `createPatient` — mirrors PatientCreateSchema, including its `user_id`/`org_id` requirement."""


@strawberry.experimental.pydantic.input(
    model=PatientPatchSchema,
    all_fields=True,
    description=(
        "Input for `updatePatient` — every scalar field optional, at least one must be set. "
        "Sub-resource arrays (name, identifier, telecom, etc.) are managed via their own "
        "dedicated mutations, not this one."
    ),
)
class PatientPatchInput:
    """Input for `updatePatient` — every scalar field optional, at least one must be set (enforced in PatientService)."""


@strawberry.experimental.pydantic.input(
    model=PatientFullCreateSchema,
    all_fields=True,
    description=(
        "Input for `createPatientFull` — creates a Patient and any combination of its nine "
        "sub-resource arrays atomically in a single fhir-server transaction; if any "
        "sub-resource insert fails, nothing is persisted. All arrays are optional; omit any "
        "to skip that sub-resource."
    ),
)
class PatientFullCreateInput:
    """
    Input for `createPatientFull` — creates a Patient and any combination of
    its nine sub-resource arrays atomically in one call. Reuses the same
    *CreateInput wrappers declared above for each nested array.
    """


@strawberry.experimental.pydantic.input(
    model=PatientFullPatchSchema,
    all_fields=True,
    description=(
        "Input for `updatePatientFull` — updates scalar fields and/or rewrites any "
        "combination of sub-resource arrays atomically. Array semantics: omit/null leaves a "
        "sub-resource untouched, `[]` deletes all records of that type, a non-empty list "
        "replaces all records (not a merge)."
    ),
)
class PatientFullPatchInput:
    """
    Input for `updatePatientFull` — updates scalar fields and/or rewrites any
    combination of sub-resource arrays atomically. Array semantics match the
    REST endpoint: omit/null leaves a sub-resource untouched, `[]` deletes
    all records of that type, a non-empty list replaces all records.
    """


# `ListPatientsSchema` is a query-parameter schema, not a mutation payload —
# GraphQL convention is to expose filters as plain field arguments rather
# than a wrapped input type. See app/gql/resolvers/patient.py, which builds
# this Pydantic object directly from the `patients` query field's scalar
# arguments.
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
    "NameCreateInput",
    "NamePatchInput",
    "IdentifierCreateInput",
    "IdentifierPatchInput",
    "TelecomCreateInput",
    "TelecomPatchInput",
    "AddressCreateInput",
    "AddressPatchInput",
    "PhotoCreateInput",
    "PhotoPatchInput",
    "ContactRelationshipInput",
    "ContactTelecomInput",
    "ContactCreateInput",
    "ContactPatchInput",
    "CommunicationCreateInput",
    "CommunicationPatchInput",
    "GeneralPractitionerCreateInput",
    "GeneralPractitionerPatchInput",
    "LinkCreateInput",
    "LinkPatchInput",
    "PatientCreateInput",
    "PatientPatchInput",
    "PatientFullCreateInput",
    "PatientFullPatchInput",
]
