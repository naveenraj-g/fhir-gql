"""
Input schemas for the Practitioner resource endpoints.

Three top-level schemas cover the write surfaces:
  - PractitionerCreateSchema  — POST /practitioners body
  - PractitionerPatchSchema   — PATCH /practitioners/{id} body
  - ListPractitionersSchema   — GET /practitioners query parameters

Plus PractitionerFullCreateSchema/PractitionerFullPatchSchema (POST/PATCH .../full)
which extend the base schemas with all 7 sub-resource arrays, mirroring
app/schemas/patient/input.py's PatientFullCreateSchema/PatientFullPatchSchema
exactly (same array semantics: omit/null = untouched, [] = delete all,
[{...}] = full replace on PATCH).

Design notes:
  - user_id/org_id are Optional (matches Organization/HealthcareService,
    unlike Location's/Patient's required fields) — ported faithfully from
    the sibling project.
  - created_by/updated_by are NOT exposed — FhirClient injects them from
    actor.sub automatically.
  - `qualification.issuer` is a FHIR reference to the issuing Organization —
    validated for existence + tenant match in PractitionerService (the only
    cross-resource reference anywhere on Practitioner; FHIR itself has no
    Organization/Location reference on Practitioner directly — that's
    PractitionerRole's job).
  - Fixed FHIR code sets reuse the shared enums in app.schemas.enums
    (IdentifierUse, ContactPointSystem, ContactPointUse, AddressUse,
    AddressType, HumanNameUse, AdministrativeGender).
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import (
    AddressType,
    AddressUse,
    AdministrativeGender,
    ContactPointSystem,
    ContactPointUse,
    HumanNameUse,
    IdentifierUse,
)


class PractitionerCreateSchema(BaseModel):
    """
    Schema for creating a Practitioner. All fields optional — a bare
    Practitioner record can be created and sub-resources added afterward via
    their own sub-routes.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "user_id": "user-uuid-123",
                "org_id": "org-uuid-456",
                "active": True,
                "gender": "female",
                "birth_date": "1978-03-15",
            }
        },
    )

    user_id: Optional[str] = Field(None, description="User identifier for tenant scoping.")
    org_id: Optional[str] = Field(None, description="Organization identifier for tenant scoping.")

    active: Optional[bool] = Field(True, description="Whether this practitioner record is active.")
    gender: Optional[AdministrativeGender] = Field(None, description="male|female|other|unknown")
    birth_date: Optional[date] = None
    deceased_boolean: Optional[bool] = None
    deceased_datetime: Optional[datetime] = None


class PractitionerPatchSchema(BaseModel):
    """
    Schema for patching a Practitioner. All fields optional — at least one
    must be provided (enforced in PractitionerService). Sub-resource arrays
    are managed via their own dedicated sub-routes, not this one.
    """

    model_config = ConfigDict(extra="forbid")

    active: Optional[bool] = None
    gender: Optional[AdministrativeGender] = None
    birth_date: Optional[date] = None
    deceased_boolean: Optional[bool] = None
    deceased_datetime: Optional[datetime] = None


class ListPractitionersSchema(BaseModel):
    """Query parameters for listing practitioners."""

    family_name: Optional[str] = Field(None, description="Partial, case-insensitive match on family name.")
    given_name: Optional[str] = Field(None, description="Partial, case-insensitive match on given name.")
    active: Optional[bool] = None
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    limit: int = Field(20, ge=1, le=200)
    offset: int = Field(0, ge=0)


# ── Sub-resource: Names ───────────────────────────────────────────────────────


class PractitionerNameCreateSchema(BaseModel):
    """Input for adding a HumanName to a Practitioner. All fields optional."""

    model_config = ConfigDict(extra="forbid")

    use: Optional[HumanNameUse] = None
    text: Optional[str] = None
    family: Optional[str] = None
    given: Optional[List[str]] = None
    prefix: Optional[List[str]] = None
    suffix: Optional[List[str]] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class PractitionerNamePatchSchema(BaseModel):
    """Patchable fields for a Practitioner HumanName. All fields optional."""

    model_config = ConfigDict(extra="forbid")

    use: Optional[HumanNameUse] = None
    text: Optional[str] = None
    family: Optional[str] = None
    given: Optional[List[str]] = None
    prefix: Optional[List[str]] = None
    suffix: Optional[List[str]] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


# ── Sub-resource: Identifiers ─────────────────────────────────────────────────


class PractitionerIdentifierCreateSchema(BaseModel):
    """Input for adding an Identifier to a Practitioner. `value` is required."""

    model_config = ConfigDict(extra="forbid")

    use: Optional[IdentifierUse] = None
    type_system: Optional[str] = None
    type_code: Optional[str] = None
    type_display: Optional[str] = None
    type_text: Optional[str] = None
    system: Optional[str] = None
    value: str = Field(..., description="The identifier value within the namespace.")
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    assigner: Optional[str] = None


class PractitionerIdentifierPatchSchema(BaseModel):
    """Patchable fields for a Practitioner Identifier. All fields optional."""

    model_config = ConfigDict(extra="forbid")

    use: Optional[IdentifierUse] = None
    type_system: Optional[str] = None
    type_code: Optional[str] = None
    type_display: Optional[str] = None
    type_text: Optional[str] = None
    system: Optional[str] = None
    value: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    assigner: Optional[str] = None


# ── Sub-resource: Telecom ─────────────────────────────────────────────────────


class PractitionerTelecomCreateSchema(BaseModel):
    """Input for adding a ContactPoint to a Practitioner. `system` and `value` required."""

    model_config = ConfigDict(extra="forbid")

    system: ContactPointSystem = Field(..., description="phone|fax|email|pager|url|sms|other")
    value: str = Field(..., description="Contact value.")
    use: Optional[ContactPointUse] = None
    rank: Optional[int] = Field(None, ge=1)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class PractitionerTelecomPatchSchema(BaseModel):
    """Patchable fields for a Practitioner ContactPoint. All fields optional."""

    model_config = ConfigDict(extra="forbid")

    system: Optional[ContactPointSystem] = None
    value: Optional[str] = None
    use: Optional[ContactPointUse] = None
    rank: Optional[int] = Field(None, ge=1)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


# ── Sub-resource: Addresses ───────────────────────────────────────────────────


class PractitionerAddressCreateSchema(BaseModel):
    """Input for adding an Address to a Practitioner. All fields optional."""

    model_config = ConfigDict(extra="forbid")

    use: Optional[AddressUse] = None
    type: Optional[AddressType] = None
    text: Optional[str] = None
    line: Optional[List[str]] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class PractitionerAddressPatchSchema(BaseModel):
    """Patchable fields for a Practitioner Address. All fields optional."""

    model_config = ConfigDict(extra="forbid")

    use: Optional[AddressUse] = None
    type: Optional[AddressType] = None
    text: Optional[str] = None
    line: Optional[List[str]] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


# ── Sub-resource: Photos ──────────────────────────────────────────────────────


class PractitionerPhotoCreateSchema(BaseModel):
    """Input for adding an Attachment (photo) to a Practitioner. All fields optional."""

    model_config = ConfigDict(extra="forbid")

    content_type: Optional[str] = None
    language: Optional[str] = None
    data: Optional[str] = None
    url: Optional[str] = None
    size: Optional[int] = None
    hash: Optional[str] = None
    title: Optional[str] = None
    creation: Optional[datetime] = None


class PractitionerPhotoPatchSchema(BaseModel):
    """Patchable fields for a Practitioner photo Attachment. All fields optional."""

    model_config = ConfigDict(extra="forbid")

    content_type: Optional[str] = None
    language: Optional[str] = None
    data: Optional[str] = None
    url: Optional[str] = None
    size: Optional[int] = None
    hash: Optional[str] = None
    title: Optional[str] = None
    creation: Optional[datetime] = None


# ── Sub-resource: Qualifications ──────────────────────────────────────────────


class QualificationIdentifierInput(BaseModel):
    """An identifier attached to a qualification record (e.g. a license number)."""

    model_config = ConfigDict(extra="forbid")

    use: Optional[IdentifierUse] = None
    type_system: Optional[str] = None
    type_code: Optional[str] = None
    type_display: Optional[str] = None
    type_text: Optional[str] = None
    system: Optional[str] = None
    value: str = Field(..., description="The identifier value.")
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    assigner: Optional[str] = None


class PractitionerQualificationCreateSchema(BaseModel):
    """
    Input for adding a qualification (certification, license, training) to a
    Practitioner. `issuer` is a FHIR reference string e.g.
    'Organization/190001' — validated for existence + tenant match in
    PractitionerService.
    """

    model_config = ConfigDict(extra="forbid")

    identifier: Optional[List[QualificationIdentifierInput]] = None
    code_system: Optional[str] = None
    code_code: Optional[str] = None
    code_display: Optional[str] = None
    code_text: Optional[str] = None
    status_system: Optional[str] = None
    status_code: Optional[str] = None
    status_display: Optional[str] = None
    status_text: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    issuer: Optional[str] = Field(
        None,
        description=(
            "FHIR reference to the issuing organization e.g. 'Organization/190001'. "
            "Validated — must reference an existing organization in the caller's own tenant."
        ),
    )
    issuer_display: Optional[str] = None


class PractitionerQualificationPatchSchema(BaseModel):
    """
    Patchable fields for a Practitioner qualification. All fields optional.
    When `identifier` is provided it replaces all existing qualification
    identifiers entirely — not a merge. When `issuer` is provided it is
    re-validated the same way as on create.
    """

    model_config = ConfigDict(extra="forbid")

    identifier: Optional[List[QualificationIdentifierInput]] = None
    code_system: Optional[str] = None
    code_code: Optional[str] = None
    code_display: Optional[str] = None
    code_text: Optional[str] = None
    status_system: Optional[str] = None
    status_code: Optional[str] = None
    status_display: Optional[str] = None
    status_text: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    issuer: Optional[str] = None
    issuer_display: Optional[str] = None


# ── Sub-resource: Communications ──────────────────────────────────────────────


class PractitionerCommunicationCreateSchema(BaseModel):
    """Input for adding a language/communication preference. `language_code` required."""

    model_config = ConfigDict(extra="forbid")

    language_system: Optional[str] = None
    language_code: str = Field(..., description="ISO 639-1 language code (e.g. en, fr, de).")
    language_display: Optional[str] = None
    language_text: Optional[str] = None
    preferred: Optional[bool] = None


class PractitionerCommunicationPatchSchema(BaseModel):
    """Patchable fields for a Practitioner communication entry. All fields optional."""

    model_config = ConfigDict(extra="forbid")

    language_system: Optional[str] = None
    language_code: Optional[str] = None
    language_display: Optional[str] = None
    language_text: Optional[str] = None
    preferred: Optional[bool] = None


# ── Full atomic create/patch ──────────────────────────────────────────────────


class PractitionerFullCreateSchema(PractitionerCreateSchema):
    """
    Input for creating a Practitioner and any combination of its 7
    sub-resource arrays atomically in a single fhir-server transaction —
    mirrors PatientFullCreateSchema exactly. All arrays optional; omit any
    to skip that sub-resource.
    """

    model_config = ConfigDict(extra="forbid")

    names: Optional[List[PractitionerNameCreateSchema]] = None
    identifiers: Optional[List[PractitionerIdentifierCreateSchema]] = None
    telecom: Optional[List[PractitionerTelecomCreateSchema]] = None
    addresses: Optional[List[PractitionerAddressCreateSchema]] = None
    photos: Optional[List[PractitionerPhotoCreateSchema]] = None
    qualifications: Optional[List[PractitionerQualificationCreateSchema]] = None
    communications: Optional[List[PractitionerCommunicationCreateSchema]] = None


class PractitionerFullPatchSchema(PractitionerPatchSchema):
    """
    Input for updating scalar fields and/or rewriting any combination of a
    Practitioner's sub-resource arrays atomically — mirrors
    PatientFullPatchSchema's array semantics exactly: omit/null leaves a
    sub-resource untouched, `[]` deletes all records of that type, a
    non-empty list replaces all records (not a merge).
    """

    model_config = ConfigDict(extra="forbid")

    names: Optional[List[PractitionerNameCreateSchema]] = None
    identifiers: Optional[List[PractitionerIdentifierCreateSchema]] = None
    telecom: Optional[List[PractitionerTelecomCreateSchema]] = None
    addresses: Optional[List[PractitionerAddressCreateSchema]] = None
    photos: Optional[List[PractitionerPhotoCreateSchema]] = None
    qualifications: Optional[List[PractitionerQualificationCreateSchema]] = None
    communications: Optional[List[PractitionerCommunicationCreateSchema]] = None
