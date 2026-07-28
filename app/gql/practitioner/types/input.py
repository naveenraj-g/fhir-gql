"""
GraphQL input types for the Practitioner resource, derived from the
existing Pydantic schemas in app/schemas/practitioner/input.py via
`strawberry.experimental.pydantic`. Output types live in
app/gql/practitioner/types/types.py.

Naming convention:
  - `<X>CreateSchema`/`<X>PatchSchema` (Pydantic) -> `<X>CreateInput`/`<X>PatchInput`
  - `QualificationIdentifierInput` (Pydantic, already ends in "Input") is
    imported under a `...Schema` alias so the plain name is free for this
    module's GraphQL wrapper class — same collision-handling pattern used
    throughout this project's other resource ports.
"""

import strawberry

# Registers ContactPointSystem/IdentifierUse/AdministrativeGender/etc. as
# GraphQL enums (side-effect import) — required before wrapping any input
# schema whose fields use them.
import app.gql.enums  # noqa: F401
from app.schemas.practitioner.input import (
    PractitionerAddressCreateSchema,
    PractitionerAddressPatchSchema,
    PractitionerCommunicationCreateSchema,
    PractitionerCommunicationPatchSchema,
    PractitionerCreateSchema,
    PractitionerFullCreateSchema,
    PractitionerFullPatchSchema,
    PractitionerIdentifierCreateSchema,
    PractitionerIdentifierPatchSchema,
    PractitionerNameCreateSchema,
    PractitionerNamePatchSchema,
    PractitionerPatchSchema,
    PractitionerPhotoCreateSchema,
    PractitionerPhotoPatchSchema,
    PractitionerQualificationCreateSchema,
    PractitionerQualificationPatchSchema,
    PractitionerTelecomCreateSchema,
    PractitionerTelecomPatchSchema,
)
from app.schemas.practitioner.input import (
    QualificationIdentifierInput as QualificationIdentifierInputSchema,
)

# ── Input types — leaf sub-resources first ───────────────────────────────────


@strawberry.experimental.pydantic.input(
    model=PractitionerNameCreateSchema, all_fields=True,
    description="Input for adding a Practitioner.name (HumanName) entry. All fields optional.",
)
class PractitionerNameCreateInput:
    """Input for adding a Practitioner.name entry."""


@strawberry.experimental.pydantic.input(
    model=PractitionerNamePatchSchema, all_fields=True,
    description="Input for patching a Practitioner.name entry — all fields optional.",
)
class PractitionerNamePatchInput:
    """Input for patching a Practitioner.name entry."""


@strawberry.experimental.pydantic.input(
    model=PractitionerIdentifierCreateSchema, all_fields=True,
    description="Input for adding a Practitioner.identifier entry. `value` is required.",
)
class PractitionerIdentifierCreateInput:
    """Input for adding a Practitioner.identifier entry."""


@strawberry.experimental.pydantic.input(
    model=PractitionerIdentifierPatchSchema, all_fields=True,
    description="Input for patching a Practitioner.identifier entry — all fields optional.",
)
class PractitionerIdentifierPatchInput:
    """Input for patching a Practitioner.identifier entry."""


@strawberry.experimental.pydantic.input(
    model=PractitionerTelecomCreateSchema, all_fields=True,
    description="Input for adding a Practitioner.telecom entry. `system` and `value` are required.",
)
class PractitionerTelecomCreateInput:
    """Input for adding a Practitioner.telecom entry."""


@strawberry.experimental.pydantic.input(
    model=PractitionerTelecomPatchSchema, all_fields=True,
    description="Input for patching a Practitioner.telecom entry — all fields optional.",
)
class PractitionerTelecomPatchInput:
    """Input for patching a Practitioner.telecom entry."""


@strawberry.experimental.pydantic.input(
    model=PractitionerAddressCreateSchema, all_fields=True,
    description="Input for adding a Practitioner.address entry. All fields optional.",
)
class PractitionerAddressCreateInput:
    """Input for adding a Practitioner.address entry."""


@strawberry.experimental.pydantic.input(
    model=PractitionerAddressPatchSchema, all_fields=True,
    description="Input for patching a Practitioner.address entry — all fields optional.",
)
class PractitionerAddressPatchInput:
    """Input for patching a Practitioner.address entry."""


@strawberry.experimental.pydantic.input(
    model=PractitionerPhotoCreateSchema, all_fields=True,
    description="Input for adding a Practitioner.photo entry. All fields optional.",
)
class PractitionerPhotoCreateInput:
    """Input for adding a Practitioner.photo entry."""


@strawberry.experimental.pydantic.input(
    model=PractitionerPhotoPatchSchema, all_fields=True,
    description="Input for patching a Practitioner.photo entry — all fields optional.",
)
class PractitionerPhotoPatchInput:
    """Input for patching a Practitioner.photo entry."""


@strawberry.experimental.pydantic.input(
    model=QualificationIdentifierInputSchema, all_fields=True,
    description="Input for one identifier attached to a Practitioner.qualification entry.",
)
class QualificationIdentifierInput:
    """Input for one identifier attached to a Practitioner.qualification entry."""


@strawberry.experimental.pydantic.input(
    model=PractitionerQualificationCreateSchema, all_fields=True,
    description=(
        "Input for adding a Practitioner.qualification entry. If `issuer` is set, it must "
        "reference an existing organization in the caller's own tenant."
    ),
)
class PractitionerQualificationCreateInput:
    """Input for adding a Practitioner.qualification entry (references QualificationIdentifierInput)."""


@strawberry.experimental.pydantic.input(
    model=PractitionerQualificationPatchSchema, all_fields=True,
    description=(
        "Input for patching a Practitioner.qualification entry — all fields optional. When "
        "`identifier` is provided it fully replaces the existing identifier array (not a merge). "
        "When `issuer` is provided it is re-validated the same way as on create."
    ),
)
class PractitionerQualificationPatchInput:
    """Input for patching a Practitioner.qualification entry."""


@strawberry.experimental.pydantic.input(
    model=PractitionerCommunicationCreateSchema, all_fields=True,
    description="Input for adding a Practitioner.communication entry. `languageCode` is required.",
)
class PractitionerCommunicationCreateInput:
    """Input for adding a Practitioner.communication entry."""


@strawberry.experimental.pydantic.input(
    model=PractitionerCommunicationPatchSchema, all_fields=True,
    description="Input for patching a Practitioner.communication entry — all fields optional.",
)
class PractitionerCommunicationPatchInput:
    """Input for patching a Practitioner.communication entry."""


@strawberry.experimental.pydantic.input(
    model=PractitionerCreateSchema, all_fields=True,
    description=(
        "Input for `createPractitioner`. `userId`/`orgId` are optional (tenant scoping). "
        "`createdBy` is stamped automatically from the caller's JWT — do not supply it."
    ),
)
class PractitionerCreateInput:
    """Input for `createPractitioner` — mirrors PractitionerCreateSchema."""


@strawberry.experimental.pydantic.input(
    model=PractitionerPatchSchema, all_fields=True,
    description=(
        "Input for `updatePractitioner` — every scalar field optional, at least one must be set. "
        "Sub-resource arrays are managed via their own dedicated mutations, not this one."
    ),
)
class PractitionerPatchInput:
    """Input for `updatePractitioner` — every field optional, at least one must be set (enforced in PractitionerService)."""


@strawberry.experimental.pydantic.input(
    model=PractitionerFullCreateSchema, all_fields=True,
    description=(
        "Input for `createPractitionerFull` — creates a Practitioner and any combination of its "
        "seven sub-resource arrays atomically in a single fhir-server transaction; if any "
        "sub-resource insert fails, nothing is persisted. All arrays are optional; omit any to "
        "skip that sub-resource. If a qualification's `issuer` is set, it must reference an "
        "existing organization in the caller's own tenant."
    ),
)
class PractitionerFullCreateInput:
    """Input for `createPractitionerFull` — creates a Practitioner and any combination of its seven sub-resource arrays atomically."""


@strawberry.experimental.pydantic.input(
    model=PractitionerFullPatchSchema, all_fields=True,
    description=(
        "Input for `updatePractitionerFull` — updates scalar fields and/or rewrites any "
        "combination of sub-resource arrays atomically. Array semantics: omit/null leaves a "
        "sub-resource untouched, `[]` deletes all records of that type, a non-empty list "
        "replaces all records (not a merge)."
    ),
)
class PractitionerFullPatchInput:
    """Input for `updatePractitionerFull` — updates scalar fields and/or rewrites any combination of sub-resource arrays atomically."""


# `ListPractitionersSchema` is a query-parameter schema, not a mutation
# payload — exposed as plain field arguments on the `practitioners` query
# instead, matching every other resource's `List*Schema` treatment.
__all__ = [
    "PractitionerNameCreateInput",
    "PractitionerNamePatchInput",
    "PractitionerIdentifierCreateInput",
    "PractitionerIdentifierPatchInput",
    "PractitionerTelecomCreateInput",
    "PractitionerTelecomPatchInput",
    "PractitionerAddressCreateInput",
    "PractitionerAddressPatchInput",
    "PractitionerPhotoCreateInput",
    "PractitionerPhotoPatchInput",
    "QualificationIdentifierInput",
    "PractitionerQualificationCreateInput",
    "PractitionerQualificationPatchInput",
    "PractitionerCommunicationCreateInput",
    "PractitionerCommunicationPatchInput",
    "PractitionerCreateInput",
    "PractitionerPatchInput",
    "PractitionerFullCreateInput",
    "PractitionerFullPatchInput",
]
