"""
Input validation schemas for the Patient resource and all its sub-resources.

All schemas use extra="forbid" to reject unknown fields at the API boundary,
preventing accidental pass-through of fields the fhir-server does not accept.

Shared FHIR code-set enums (address use/type, contact point, name use,
identifier use) are imported from app.schemas.enums.
Patient-specific enums (GP reference type, link type) are imported from
app.schemas.patient.enums.

Reference: https://hl7.org/fhir/R4/patient.html
"""

from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.enums import (
    AddressType,
    AddressUse,
    AdministrativeGender,
    ContactPointSystem,
    ContactPointUse,
    HumanNameUse,
    IdentifierUse,
)
from app.schemas.patient.enums import (
    GeneralPractitionerReferenceType,
    PatientLinkOtherType,
    PatientLinkType,
)


# ── Top-level Patient schemas ─────────────────────────────────────────────────


class PatientCreateSchema(BaseModel):
    """
    Input schema for creating a Patient resource.

    user_id is required — the fhir-server uses it to link the patient to the
    owning portal user. org_id is NOT included here: unlike every other
    resource, fhir-server derives Patient's org_id from the verified JWT's
    `activeOrganizationId` claim itself (see fhir-server's Multi-Tenancy &
    Ownership rollout status) — a client-supplied org_id would now be
    rejected outright (extra="forbid", no such field declared). created_by
    is likewise NOT included here; fhir-server stamps it from the verified
    JWT's `sub` claim, not from FhirClient's usual actor.sub injection.

    All FHIR scalar fields (gender, birth_date, deceased_*, marital_status_*,
    multiple_birth_*, managing_organization) are optional — the fhir-server
    allows creating a minimal patient with only user_id.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "user_id": "u-abc123",
                "active": True,
                "gender": "female",
                "birth_date": "1990-06-15",
            }
        },
    )

    # Owning-user scoping — required so the fhir-server can link this Patient
    # to a portal user. org_id is deliberately absent: fhir-server derives it
    # from the caller's verified JWT instead (Patient-only exception).
    user_id: str = Field(description="JWT subject of the owning user.")

    # FHIR Patient scalar fields — all optional per the R4 spec.
    active: Optional[bool] = Field(True, description="Whether this patient record is active.")
    gender: Optional[AdministrativeGender] = Field(None, description="Administrative gender: male | female | other | unknown.")
    birth_date: Optional[date] = Field(None, description="Date of birth (YYYY-MM-DD).")

    # deceased[x] — only one of these should be set at a time.
    deceased_boolean: Optional[bool] = Field(None, description="True if the patient is deceased (no date known).")
    deceased_datetime: Optional[datetime] = Field(None, description="Date/time of death (if known).")

    # maritalStatus — flattened CodeableConcept.
    marital_status_system: Optional[str] = Field(None, description="Coding system URI for marital status.")
    marital_status_version: Optional[str] = Field(None, description="Version of the marital-status coding system.")
    marital_status_code: Optional[str] = Field(None, description="Marital status code (e.g. M, S, D, W).")
    marital_status_display: Optional[str] = Field(None, description="Human-readable marital status label.")
    marital_status_text: Optional[str] = Field(None, description="Plain-text marital status description.")
    marital_status_user_selected: Optional[bool] = Field(None, description="Whether this marital-status coding was chosen directly by the user.")

    # multipleBirth[x] — only one of these should be set at a time.
    multiple_birth_boolean: Optional[bool] = Field(None, description="True if the patient is part of a multiple birth.")
    multiple_birth_integer: Optional[int] = Field(None, description="Birth order in a multiple birth.")

    # managingOrganization — flattened Reference(Organization).
    managing_organization: Optional[str] = Field(None, description="FHIR reference to managing org e.g. 'Organization/190001'.")
    managing_organization_display: Optional[str] = Field(None, description="Display name of the managing organisation.")

    # managingOrganization.identifier — logical-reference fallback for when the
    # managing organisation isn't a resource in this system at all (matches
    # FHIR's Reference.identifier).
    managing_organization_identifier_use: Optional[IdentifierUse] = Field(None, description="Fallback identifier use: usual | official | temp | secondary | old.")
    managing_organization_identifier_type_system: Optional[str] = Field(None, description="Fallback identifier — coding system for its type.")
    managing_organization_identifier_type_version: Optional[str] = Field(None, description="Fallback identifier — version of the type coding system.")
    managing_organization_identifier_type_code: Optional[str] = Field(None, description="Fallback identifier — code for its type (e.g. MR, SS).")
    managing_organization_identifier_type_display: Optional[str] = Field(None, description="Fallback identifier — display for its type.")
    managing_organization_identifier_type_text: Optional[str] = Field(None, description="Fallback identifier — plain-text rendering of its type.")
    managing_organization_identifier_type_user_selected: Optional[bool] = Field(None, description="Fallback identifier — whether its type coding was user-selected.")
    managing_organization_identifier_system: Optional[str] = Field(None, description="Fallback identifier — URI namespace.")
    managing_organization_identifier_value: Optional[str] = Field(None, description="Fallback identifier — value within the given system.")
    managing_organization_identifier_period_start: Optional[datetime] = Field(None, description="Fallback identifier — when it became valid.")
    managing_organization_identifier_period_end: Optional[datetime] = Field(None, description="Fallback identifier — when it stopped being valid.")


class PatientPatchSchema(BaseModel):
    """
    Patchable fields for a Patient resource.

    All fields are optional — at least one must be provided (enforced in the
    service layer). user_id is not patchable (fixed at creation time); org_id
    and updated_by are never client-suppliable at all — fhir-server derives
    both from the verified JWT.
    """

    model_config = ConfigDict(extra="forbid")

    active: Optional[bool] = None
    gender: Optional[AdministrativeGender] = None
    birth_date: Optional[date] = None
    deceased_boolean: Optional[bool] = None
    deceased_datetime: Optional[datetime] = None
    marital_status_system: Optional[str] = None
    marital_status_version: Optional[str] = None
    marital_status_code: Optional[str] = None
    marital_status_display: Optional[str] = None
    marital_status_text: Optional[str] = None
    marital_status_user_selected: Optional[bool] = None
    multiple_birth_boolean: Optional[bool] = None
    multiple_birth_integer: Optional[int] = None
    managing_organization: Optional[str] = None
    managing_organization_display: Optional[str] = None
    managing_organization_identifier_use: Optional[IdentifierUse] = None
    managing_organization_identifier_type_system: Optional[str] = None
    managing_organization_identifier_type_version: Optional[str] = None
    managing_organization_identifier_type_code: Optional[str] = None
    managing_organization_identifier_type_display: Optional[str] = None
    managing_organization_identifier_type_text: Optional[str] = None
    managing_organization_identifier_type_user_selected: Optional[bool] = None
    managing_organization_identifier_system: Optional[str] = None
    managing_organization_identifier_value: Optional[str] = None
    managing_organization_identifier_period_start: Optional[datetime] = None
    managing_organization_identifier_period_end: Optional[datetime] = None


class ListPatientsSchema(BaseModel):
    """
    Query parameters for the GET /patients list endpoint.

    All filters are optional and combinable. Mirrors fhir-server's current
    `list_patients` filter set exactly (app/routers/patient.py there) — see
    dev-docs/12-search-and-filter-standards.md for the design rationale.
    This schema declares the contract; PatientService.list() translates each
    field into the exact (possibly hyphenated) query-string key fhir-server
    expects, and PatientClient.list() forwards them untouched.

    org_id is deliberately NOT a filter here (removed — previously existed):
    fhir-server always scopes Patient reads to the caller's own org via the
    verified JWT's activeOrganizationId claim; a client can never widen or
    redirect that scope. user_id remains — it can only narrow the results to
    a single user within the caller's own org, never escape it.

    populate_by_name=True lets callers construct this model with either the
    Python attribute name (e.g. GraphQL's queries.py) or the FHIR-style alias
    (e.g. FastAPI parsing `?address-city=...` from the REST querystring).
    """

    model_config = ConfigDict(populate_by_name=True)

    family: Optional[str] = Field(None, description="Filter by family (last) name — partial match.")
    given: Optional[str] = Field(None, description="Filter by given name — partial match.")
    name: Optional[str] = Field(
        None,
        description="Partial match against any HumanName sub-field (family, given, prefix, suffix, text).",
    )
    gender: Optional[AdministrativeGender] = Field(None, description="male|female|other|unknown")
    active: Optional[bool] = Field(None, description="Filter by active status.")
    user_id: Optional[str] = Field(None, description="Filter by owning user (JWT subject).")
    identifier: Optional[str] = Field(None, description="Exact match on a business identifier value (MRN, SSN, etc.).")

    birthdate: Optional[List[str]] = Field(
        None,
        description=(
            "FHIR comparator-prefixed date (eq/ne/gt/lt/ge/le), e.g. `ge2020-01-01`. "
            "Repeat the param for a range, e.g. birthdate=ge2020-01-01&birthdate=le2020-12-31."
        ),
    )
    death_date: Optional[List[str]] = Field(
        None,
        alias="death-date",
        description="Same comparator-prefixed format as birthdate, filtering on the deceased dateTime.",
    )
    deceased: Optional[bool] = Field(
        None, description="true = deceased[x] is populated at all (boolean true or a death date present)."
    )

    address: Optional[str] = Field(
        None,
        description="Partial match against any Address sub-field (line, city, district, state, country, postalCode, text).",
    )
    address_city: Optional[str] = Field(None, alias="address-city", description="Filter by address city — partial match.")
    address_state: Optional[str] = Field(None, alias="address-state", description="Filter by address state — partial match.")
    address_postal_code: Optional[str] = Field(
        None, alias="address-postalcode", description="Filter by address postal code — exact match."
    )
    address_country: Optional[str] = Field(None, alias="address-country", description="Filter by address country — partial match.")
    address_use: Optional[AddressUse] = Field(None, alias="address-use", description="home|work|temp|old|billing.")

    telecom: Optional[str] = Field(None, description="Filter by any telecom value, regardless of system — partial match.")
    email: Optional[str] = Field(None, description="Filter by telecom email — partial match, system=email only.")
    phone: Optional[str] = Field(None, description="Filter by telecom phone — partial match, system=phone only.")
    language: Optional[str] = Field(None, description="Exact match on Patient.communication.language code (e.g. en, fr).")

    general_practitioner: Optional[str] = Field(
        None,
        alias="general-practitioner",
        description="generalPractitioner as a FHIR reference string, e.g. `Practitioner/30001`.",
    )
    organization: Optional[str] = Field(
        None, description="managingOrganization as a FHIR reference string, e.g. `Organization/190001`."
    )
    link: Optional[str] = Field(None, description="FHIR reference string, e.g. `Patient/10002` or `RelatedPerson/300001`.")

    sort: Optional[str] = Field(None, description="Field to sort by; prefix with '-' for descending (e.g. '-birthdate').")
    total_mode: Literal["accurate", "none"] = Field(
        "accurate",
        description="'none' skips the total-count query — use on large result sets when only the page is needed.",
    )

    limit: int = Field(50, ge=1, le=200, description="Max results to return.")
    offset: int = Field(0, ge=0, description="Number of results to skip.")


# ── Sub-resource: Names ───────────────────────────────────────────────────────


class NameCreateSchema(BaseModel):
    """
    Input for adding a HumanName to a Patient.

    All fields are optional — a name with only family or only text is valid FHIR.
    given, prefix, and suffix are lists because a person may have multiple
    given names or multiple prefixes/suffixes.
    """

    model_config = ConfigDict(extra="forbid")

    use: Optional[HumanNameUse] = Field(None, description="usual | official | temp | nickname | anonymous | old | maiden")
    text: Optional[str] = Field(None, description="Full name as a single string.")
    family: Optional[str] = Field(None, description="Family (last) name.")
    given: Optional[List[str]] = Field(None, description="Given (first/middle) names.")
    prefix: Optional[List[str]] = Field(None, description="Name prefixes (e.g. Dr., Mr.).")
    suffix: Optional[List[str]] = Field(None, description="Name suffixes (e.g. Jr., PhD).")
    period_start: Optional[datetime] = Field(None, description="Start of the period this name was in use.")
    period_end: Optional[datetime] = Field(None, description="End of the period this name was in use.")


class NamePatchSchema(BaseModel):
    """Patchable fields for a Patient HumanName. All fields optional."""

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


class IdentifierCreateSchema(BaseModel):
    """
    Input for adding an Identifier to a Patient.

    `value` is the only required field — every identifier must have a value.
    All other fields describe the type and context of the identifier.
    """

    model_config = ConfigDict(extra="forbid")

    use: Optional[IdentifierUse] = Field(None, description="usual | official | temp | secondary | old")
    type_system: Optional[str] = Field(None, description="Coding system URI for the identifier type.")
    type_version: Optional[str] = Field(None, description="Version of the identifier-type coding system.")
    type_code: Optional[str] = Field(None, description="Type code (e.g. MR for medical record number).")
    type_display: Optional[str] = Field(None, description="Human-readable label for the type code.")
    type_text: Optional[str] = Field(None, description="Plain-text description of the identifier type.")
    type_user_selected: Optional[bool] = Field(None, description="Whether this identifier-type coding was chosen directly by the user.")
    system: Optional[str] = Field(None, description="URI of the identifier namespace.")
    value: str = Field(..., description="The identifier value within the namespace.")
    period_start: Optional[datetime] = Field(None, description="Start of the period this identifier is valid.")
    period_end: Optional[datetime] = Field(None, description="End of the period this identifier is valid.")

    # assigner — Reference(Organization) that issued the identifier. `assigner`
    # is now a FHIR reference string (e.g. 'Organization/190001'), not a
    # display name — use assigner_display for the human-readable label.
    assigner: Optional[str] = Field(None, description="FHIR reference to the assigning organisation e.g. 'Organization/190001'.")
    assigner_display: Optional[str] = Field(None, description="Display name of the assigning organisation.")

    # assigner.identifier — logical-reference fallback for when the assigning
    # organisation isn't a resource in this system at all.
    assigner_identifier_use: Optional[IdentifierUse] = Field(None, description="Fallback identifier use: usual | official | temp | secondary | old.")
    assigner_identifier_type_system: Optional[str] = Field(None, description="Fallback identifier — coding system for its type.")
    assigner_identifier_type_version: Optional[str] = Field(None, description="Fallback identifier — version of the type coding system.")
    assigner_identifier_type_code: Optional[str] = Field(None, description="Fallback identifier — code for its type (e.g. MR, SS).")
    assigner_identifier_type_display: Optional[str] = Field(None, description="Fallback identifier — display for its type.")
    assigner_identifier_type_text: Optional[str] = Field(None, description="Fallback identifier — plain-text rendering of its type.")
    assigner_identifier_type_user_selected: Optional[bool] = Field(None, description="Fallback identifier — whether its type coding was user-selected.")
    assigner_identifier_system: Optional[str] = Field(None, description="Fallback identifier — URI namespace.")
    assigner_identifier_value: Optional[str] = Field(None, description="Fallback identifier — value within the given system.")
    assigner_identifier_period_start: Optional[datetime] = Field(None, description="Fallback identifier — when it became valid.")
    assigner_identifier_period_end: Optional[datetime] = Field(None, description="Fallback identifier — when it stopped being valid.")


class IdentifierPatchSchema(BaseModel):
    """Patchable fields for a Patient Identifier. All fields optional."""

    model_config = ConfigDict(extra="forbid")

    use: Optional[IdentifierUse] = None
    type_system: Optional[str] = None
    type_version: Optional[str] = None
    type_code: Optional[str] = None
    type_display: Optional[str] = None
    type_text: Optional[str] = None
    type_user_selected: Optional[bool] = None
    system: Optional[str] = None
    value: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    assigner: Optional[str] = None
    assigner_display: Optional[str] = None
    assigner_identifier_use: Optional[IdentifierUse] = None
    assigner_identifier_type_system: Optional[str] = None
    assigner_identifier_type_version: Optional[str] = None
    assigner_identifier_type_code: Optional[str] = None
    assigner_identifier_type_display: Optional[str] = None
    assigner_identifier_type_text: Optional[str] = None
    assigner_identifier_type_user_selected: Optional[bool] = None
    assigner_identifier_system: Optional[str] = None
    assigner_identifier_value: Optional[str] = None
    assigner_identifier_period_start: Optional[datetime] = None
    assigner_identifier_period_end: Optional[datetime] = None


# ── Sub-resource: Telecom ─────────────────────────────────────────────────────


class TelecomCreateSchema(BaseModel):
    """
    Input for adding a ContactPoint (telecom) to a Patient.

    `system` and `value` are required — every contact point must specify
    the technology and the actual contact value.
    """

    model_config = ConfigDict(extra="forbid")

    system: ContactPointSystem = Field(..., description="phone | fax | email | pager | url | sms | other")
    value: str = Field(..., description="The actual contact value (phone number, email address, etc.).")
    use: Optional[ContactPointUse] = Field(None, description="home | work | temp | old | mobile")
    rank: Optional[int] = Field(None, ge=1, description="Preferred order of contact (1 = most preferred).")
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class TelecomPatchSchema(BaseModel):
    """Patchable fields for a Patient ContactPoint. All fields optional."""

    model_config = ConfigDict(extra="forbid")

    system: Optional[ContactPointSystem] = None
    value: Optional[str] = None
    use: Optional[ContactPointUse] = None
    rank: Optional[int] = Field(None, ge=1)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


# ── Sub-resource: Addresses ───────────────────────────────────────────────────


class AddressCreateSchema(BaseModel):
    """
    Input for adding an Address to a Patient.

    All fields are optional — an address may be as minimal as just a city,
    or as complete as a full structured address with period.
    `line` is a list because an address may span multiple lines.
    """

    model_config = ConfigDict(extra="forbid")

    use: Optional[AddressUse] = Field(None, description="home | work | temp | old | billing")
    type: Optional[AddressType] = Field(None, description="postal | physical | both")
    text: Optional[str] = Field(None, description="Full address as a single plain-text string.")
    line: Optional[List[str]] = Field(None, description="Street address lines (e.g. ['123 Main St', 'Apt 4']).")
    city: Optional[str] = None
    district: Optional[str] = Field(None, description="County or district.")
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class AddressPatchSchema(BaseModel):
    """Patchable fields for a Patient Address. All fields optional."""

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


class PhotoCreateSchema(BaseModel):
    """
    Input for adding an Attachment (photo) to a Patient.

    All fields are optional — a photo may be a URL reference or inline base64 data.
    `data` should be base64-encoded binary. `hash` should be a base64-encoded SHA-1.
    """

    model_config = ConfigDict(extra="forbid")

    content_type: Optional[str] = Field(None, description="MIME type of the photo (e.g. image/jpeg).")
    language: Optional[str] = Field(None, description="BCP-47 language code for the photo's language (if applicable).")
    data: Optional[str] = Field(None, description="Base64-encoded photo data.")
    url: Optional[str] = Field(None, description="URL pointing to the photo (alternative to inline data).")
    size: Optional[int] = Field(None, description="Size of the photo in bytes.")
    hash: Optional[str] = Field(None, description="Base64-encoded SHA-1 hash of the data.")
    title: Optional[str] = Field(None, description="Human-readable label for the photo.")
    creation: Optional[datetime] = Field(None, description="Date/time the photo was taken or created.")


class PhotoPatchSchema(BaseModel):
    """Patchable fields for a Patient photo Attachment. All fields optional."""

    model_config = ConfigDict(extra="forbid")

    content_type: Optional[str] = None
    language: Optional[str] = None
    data: Optional[str] = None
    url: Optional[str] = None
    size: Optional[int] = None
    hash: Optional[str] = None
    title: Optional[str] = None
    creation: Optional[datetime] = None


# ── Sub-resource: Contacts ────────────────────────────────────────────────────


class ContactRelationshipInput(BaseModel):
    """
    A single relationship CodeableConcept within a Patient contact.

    Describes the relationship of the contact person to the patient
    (e.g. Emergency contact, Next-of-kin, Guardian).
    """

    model_config = ConfigDict(extra="forbid")

    coding_system: Optional[str] = Field(None, description="Coding system URI (e.g. http://terminology.hl7.org/CodeSystem/v2-0131).")
    coding_version: Optional[str] = Field(None, description="Version of the relationship coding system.")
    coding_code: Optional[str] = Field(None, description="Relationship code (e.g. C for emergency contact, N for next-of-kin).")
    coding_display: Optional[str] = Field(None, description="Human-readable label for the relationship code.")
    text: Optional[str] = Field(None, description="Plain-text description of the relationship.")
    coding_user_selected: Optional[bool] = Field(None, description="Whether this coding was chosen directly by the user.")


class ContactTelecomInput(BaseModel):
    """A single ContactPoint within a Patient contact's telecom list."""

    model_config = ConfigDict(extra="forbid")

    system: ContactPointSystem = Field(..., description="phone | fax | email | pager | url | sms | other")
    value: str = Field(..., description="The actual contact value.")
    use: Optional[ContactPointUse] = Field(None, description="home | work | temp | old | mobile")
    rank: Optional[int] = Field(None, ge=1)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class ContactCreateSchema(BaseModel):
    """
    Input for adding a contact (next-of-kin/guardian/emergency contact) to a Patient.

    The contact's name and address are flattened into scalar fields (name_family,
    address_city, etc.) to match the fhir-server's storage model.
    relationship and telecom are nested arrays because a contact may have
    multiple relationships and multiple contact points.
    """

    model_config = ConfigDict(extra="forbid")

    # relationship (0..*) — CodeableConcept array describing how the contact relates to the patient.
    relationship: Optional[List[ContactRelationshipInput]] = None

    # HumanName — flattened (0..1).
    name_use: Optional[HumanNameUse] = None
    name_text: Optional[str] = None
    name_family: Optional[str] = None
    name_given: Optional[List[str]] = None
    name_prefix: Optional[List[str]] = None
    name_suffix: Optional[List[str]] = None
    name_period_start: Optional[datetime] = Field(None, description="When the contact person's name became valid.")
    name_period_end: Optional[datetime] = Field(None, description="When the contact person's name stopped being valid.")

    # ContactPoint array (0..*).
    telecom: Optional[List[ContactTelecomInput]] = None

    # Address — flattened (0..1).
    address_use: Optional[AddressUse] = None
    address_type: Optional[AddressType] = None
    address_text: Optional[str] = None
    address_line: Optional[List[str]] = None
    address_city: Optional[str] = None
    address_district: Optional[str] = None
    address_state: Optional[str] = None
    address_postal_code: Optional[str] = None
    address_country: Optional[str] = None
    address_period_start: Optional[datetime] = None
    address_period_end: Optional[datetime] = None

    gender: Optional[AdministrativeGender] = Field(None, description="Administrative gender of the contact person.")
    organization: Optional[str] = Field(None, description="FHIR reference to the contact's organisation e.g. 'Organization/190001'.")
    organization_display: Optional[str] = None

    # organization.identifier — logical-reference fallback for when the
    # contact's organisation isn't a resource in this system at all.
    organization_identifier_use: Optional[IdentifierUse] = Field(None, description="Fallback identifier use: usual | official | temp | secondary | old.")
    organization_identifier_type_system: Optional[str] = Field(None, description="Fallback identifier — coding system for its type.")
    organization_identifier_type_version: Optional[str] = Field(None, description="Fallback identifier — version of the type coding system.")
    organization_identifier_type_code: Optional[str] = Field(None, description="Fallback identifier — code for its type (e.g. MR, SS).")
    organization_identifier_type_display: Optional[str] = Field(None, description="Fallback identifier — display for its type.")
    organization_identifier_type_text: Optional[str] = Field(None, description="Fallback identifier — plain-text rendering of its type.")
    organization_identifier_type_user_selected: Optional[bool] = Field(None, description="Fallback identifier — whether its type coding was user-selected.")
    organization_identifier_system: Optional[str] = Field(None, description="Fallback identifier — URI namespace.")
    organization_identifier_value: Optional[str] = Field(None, description="Fallback identifier — value within the given system.")
    organization_identifier_period_start: Optional[datetime] = Field(None, description="Fallback identifier — when it became valid.")
    organization_identifier_period_end: Optional[datetime] = Field(None, description="Fallback identifier — when it stopped being valid.")

    period_start: Optional[datetime] = Field(None, description="Start of the period this contact is/was applicable.")
    period_end: Optional[datetime] = None


class ContactPatchSchema(BaseModel):
    """
    Patchable fields for a Patient contact. All fields optional.

    When relationship or telecom arrays are provided, they replace the
    existing array entirely on the fhir-server (full replacement, not merge).
    """

    model_config = ConfigDict(extra="forbid")

    relationship: Optional[List[ContactRelationshipInput]] = None
    name_use: Optional[HumanNameUse] = None
    name_text: Optional[str] = None
    name_family: Optional[str] = None
    name_given: Optional[List[str]] = None
    name_prefix: Optional[List[str]] = None
    name_suffix: Optional[List[str]] = None
    name_period_start: Optional[datetime] = None
    name_period_end: Optional[datetime] = None
    telecom: Optional[List[ContactTelecomInput]] = None
    address_use: Optional[AddressUse] = None
    address_type: Optional[AddressType] = None
    address_text: Optional[str] = None
    address_line: Optional[List[str]] = None
    address_city: Optional[str] = None
    address_district: Optional[str] = None
    address_state: Optional[str] = None
    address_postal_code: Optional[str] = None
    address_country: Optional[str] = None
    address_period_start: Optional[datetime] = None
    address_period_end: Optional[datetime] = None
    gender: Optional[AdministrativeGender] = None
    organization: Optional[str] = None
    organization_display: Optional[str] = None
    organization_identifier_use: Optional[IdentifierUse] = None
    organization_identifier_type_system: Optional[str] = None
    organization_identifier_type_version: Optional[str] = None
    organization_identifier_type_code: Optional[str] = None
    organization_identifier_type_display: Optional[str] = None
    organization_identifier_type_text: Optional[str] = None
    organization_identifier_type_user_selected: Optional[bool] = None
    organization_identifier_system: Optional[str] = None
    organization_identifier_value: Optional[str] = None
    organization_identifier_period_start: Optional[datetime] = None
    organization_identifier_period_end: Optional[datetime] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


# ── Sub-resource: Communications ──────────────────────────────────────────────


class CommunicationCreateSchema(BaseModel):
    """
    Input for adding a communication language preference to a Patient.

    `language_code` is required — it must be a valid ISO 639-1 code (e.g. en, fr, de).
    `preferred` flags whether this is the patient's preferred communication language.
    """

    model_config = ConfigDict(extra="forbid")

    language_system: Optional[str] = Field(None, description="Coding system URI for the language (e.g. urn:ietf:bcp:47).")
    language_version: Optional[str] = Field(None, description="Version of the language coding system.")
    language_code: str = Field(..., description="ISO 639-1 language code (e.g. en, fr, de).")
    language_display: Optional[str] = Field(None, description="Human-readable language name.")
    language_text: Optional[str] = Field(None, description="Plain-text description of the language preference.")
    language_user_selected: Optional[bool] = Field(None, description="Whether this coding was chosen directly by the user.")
    preferred: Optional[bool] = Field(None, description="True if this is the patient's preferred language.")


class CommunicationPatchSchema(BaseModel):
    """Patchable fields for a Patient communication entry. All fields optional."""

    model_config = ConfigDict(extra="forbid")

    language_system: Optional[str] = None
    language_version: Optional[str] = None
    language_code: Optional[str] = None
    language_display: Optional[str] = None
    language_text: Optional[str] = None
    language_user_selected: Optional[bool] = None
    preferred: Optional[bool] = None


# ── Sub-resource: General Practitioners ──────────────────────────────────────


class GeneralPractitionerCreateSchema(BaseModel):
    """
    Input for adding a generalPractitioner reference to a Patient.

    `reference_type`/`reference_id` are now optional — the fhir-server also
    accepts a logical-reference fallback (`reference_identifier_system` +
    `reference_identifier_value`) for a GP who isn't a resource in this
    system at all (e.g. an external provider known only by NPI). At least
    one of the two forms must be supplied (enforced below).
    """

    model_config = ConfigDict(extra="forbid")

    reference_type: Optional[GeneralPractitionerReferenceType] = Field(None, description="Organization | Practitioner | PractitionerRole. Required together with reference_id unless the identifier fallback is used instead.")
    reference_id: Optional[int] = Field(None, description="Integer ID of the referenced resource on the fhir-server.")
    reference_display: Optional[str] = Field(None, description="Human-readable display name for the reference.")

    # Logical-reference fallback — used when the GP isn't a resource in this system.
    reference_identifier_use: Optional[IdentifierUse] = Field(None, description="Fallback identifier use: usual | official | temp | secondary | old.")
    reference_identifier_type_system: Optional[str] = Field(None, description="Fallback identifier — coding system for its type.")
    reference_identifier_type_version: Optional[str] = Field(None, description="Fallback identifier — version of the type coding system.")
    reference_identifier_type_code: Optional[str] = Field(None, description="Fallback identifier — code for its type (e.g. MR, SS).")
    reference_identifier_type_display: Optional[str] = Field(None, description="Fallback identifier — display for its type.")
    reference_identifier_type_text: Optional[str] = Field(None, description="Fallback identifier — plain-text rendering of its type.")
    reference_identifier_type_user_selected: Optional[bool] = Field(None, description="Fallback identifier — whether its type coding was user-selected.")
    reference_identifier_system: Optional[str] = Field(None, description="Fallback identifier — URI namespace.")
    reference_identifier_value: Optional[str] = Field(None, description="Fallback identifier — value within the given system.")
    reference_identifier_period_start: Optional[datetime] = Field(None, description="Fallback identifier — when it became valid.")
    reference_identifier_period_end: Optional[datetime] = Field(None, description="Fallback identifier — when it stopped being valid.")

    @model_validator(mode="after")
    def _require_reference_or_identifier(self):
        has_reference = self.reference_type is not None and self.reference_id is not None
        has_identifier = self.reference_identifier_system is not None and self.reference_identifier_value is not None
        if not has_reference and not has_identifier:
            raise ValueError(
                "Provide either reference_type+reference_id or "
                "reference_identifier_system+reference_identifier_value."
            )
        return self


class GeneralPractitionerPatchSchema(BaseModel):
    """Patchable fields for a Patient generalPractitioner reference. All fields optional."""

    model_config = ConfigDict(extra="forbid")

    reference_type: Optional[GeneralPractitionerReferenceType] = None
    reference_id: Optional[int] = None
    reference_display: Optional[str] = None
    reference_identifier_use: Optional[IdentifierUse] = None
    reference_identifier_type_system: Optional[str] = None
    reference_identifier_type_version: Optional[str] = None
    reference_identifier_type_code: Optional[str] = None
    reference_identifier_type_display: Optional[str] = None
    reference_identifier_type_text: Optional[str] = None
    reference_identifier_type_user_selected: Optional[bool] = None
    reference_identifier_system: Optional[str] = None
    reference_identifier_value: Optional[str] = None
    reference_identifier_period_start: Optional[datetime] = None
    reference_identifier_period_end: Optional[datetime] = None


# ── Sub-resource: Links ───────────────────────────────────────────────────────


class LinkCreateSchema(BaseModel):
    """
    Input for adding a link between this Patient and another Patient or RelatedPerson.

    `other_type`/`other_id` are now optional — the fhir-server also accepts a
    logical-reference fallback (`other_identifier_system` + `other_identifier_value`)
    for linking to a record that isn't a resource in this system at all (e.g.
    a duplicate record in an external EMR). At least one of the two forms
    must be supplied (enforced below). `type` is still always required.
    """

    model_config = ConfigDict(extra="forbid")

    other_type: Optional[PatientLinkOtherType] = Field(None, description="Patient | RelatedPerson. Required together with other_id unless the identifier fallback is used instead.")
    other_id: Optional[int] = Field(None, description="Integer ID of the linked Patient or RelatedPerson.")
    other_display: Optional[str] = Field(None, description="Display name for the linked resource.")

    # Logical-reference fallback — used when the linked record isn't a resource in this system.
    other_identifier_use: Optional[IdentifierUse] = Field(None, description="Fallback identifier use: usual | official | temp | secondary | old.")
    other_identifier_type_system: Optional[str] = Field(None, description="Fallback identifier — coding system for its type.")
    other_identifier_type_version: Optional[str] = Field(None, description="Fallback identifier — version of the type coding system.")
    other_identifier_type_code: Optional[str] = Field(None, description="Fallback identifier — code for its type (e.g. MR, SS).")
    other_identifier_type_display: Optional[str] = Field(None, description="Fallback identifier — display for its type.")
    other_identifier_type_text: Optional[str] = Field(None, description="Fallback identifier — plain-text rendering of its type.")
    other_identifier_type_user_selected: Optional[bool] = Field(None, description="Fallback identifier — whether its type coding was user-selected.")
    other_identifier_system: Optional[str] = Field(None, description="Fallback identifier — URI namespace.")
    other_identifier_value: Optional[str] = Field(None, description="Fallback identifier — value within the given system.")
    other_identifier_period_start: Optional[datetime] = Field(None, description="Fallback identifier — when it became valid.")
    other_identifier_period_end: Optional[datetime] = Field(None, description="Fallback identifier — when it stopped being valid.")

    type: PatientLinkType = Field(..., description="replaced-by | replaces | refer | seealso")

    @model_validator(mode="after")
    def _require_reference_or_identifier(self):
        has_reference = self.other_type is not None and self.other_id is not None
        has_identifier = self.other_identifier_system is not None and self.other_identifier_value is not None
        if not has_reference and not has_identifier:
            raise ValueError(
                "Provide either other_type+other_id or "
                "other_identifier_system+other_identifier_value."
            )
        return self


class LinkPatchSchema(BaseModel):
    """Patchable fields for a Patient link. All fields optional."""

    model_config = ConfigDict(extra="forbid")

    other_type: Optional[PatientLinkOtherType] = None
    other_id: Optional[int] = None
    other_display: Optional[str] = None
    other_identifier_use: Optional[IdentifierUse] = None
    other_identifier_type_system: Optional[str] = None
    other_identifier_type_version: Optional[str] = None
    other_identifier_type_code: Optional[str] = None
    other_identifier_type_display: Optional[str] = None
    other_identifier_type_text: Optional[str] = None
    other_identifier_type_user_selected: Optional[bool] = None
    other_identifier_system: Optional[str] = None
    other_identifier_value: Optional[str] = None
    other_identifier_period_start: Optional[datetime] = None
    other_identifier_period_end: Optional[datetime] = None
    type: Optional[PatientLinkType] = None


# ── Full atomic patch ─────────────────────────────────────────────────────────


class PatientFullPatchSchema(PatientPatchSchema):
    """
    Input schema for PATCH /patients/{id}/full.

    Extends PatientPatchSchema with all nine sub-resource arrays.
    The semantics differ from the regular sub-resource routes:

      - null / omitted → leave that sub-resource completely untouched.
      - []             → delete ALL records of that sub-resource type.
      - [{...}, ...]   → replace ALL records with the provided items
                         (full replacement, not a merge).

    This allows a single call to update scalar fields AND/OR rewrite any
    combination of sub-resources atomically on the fhir-server.

    At least one field or array must be provided (enforced in the service layer).
    updated_by is NOT included — FhirClient injects it from actor.sub automatically.
    """

    model_config = ConfigDict(extra="forbid")

    # Sub-resource arrays — None means "leave alone"; [] means "delete all".
    names: Optional[List[NameCreateSchema]] = None
    identifiers: Optional[List[IdentifierCreateSchema]] = None
    telecom: Optional[List[TelecomCreateSchema]] = None
    addresses: Optional[List[AddressCreateSchema]] = None
    photos: Optional[List[PhotoCreateSchema]] = None
    contacts: Optional[List[ContactCreateSchema]] = None
    communications: Optional[List[CommunicationCreateSchema]] = None
    general_practitioners: Optional[List[GeneralPractitionerCreateSchema]] = None
    links: Optional[List[LinkCreateSchema]] = None


# ── Full atomic create ────────────────────────────────────────────────────────


class PatientFullCreateSchema(PatientCreateSchema):
    """
    Input schema for creating a Patient and any combination of sub-resources
    atomically in a single request.

    Extends PatientCreateSchema with 9 optional sub-resource arrays. Each array
    is forwarded to the fhir-server's POST /patients/full endpoint, which wraps
    all inserts in one DB transaction — if any sub-resource insert fails, the
    entire request rolls back and no records are created.

    All arrays are optional; omit any to skip those sub-resources.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "user_id": "u-abc123",
                "active": True,
                "gender": "female",
                "birth_date": "1990-06-15",
                "names": [{"use": "official", "family": "Doe", "given": ["Jane"]}],
                "identifiers": [{"value": "MRN-98765", "system": "http://hospital.com/mrn"}],
                "telecom": [{"system": "email", "value": "jane@example.com", "use": "home"}],
                "addresses": [{"use": "home", "city": "Boston", "state": "MA", "country": "USA"}],
                "communications": [{"language_code": "en", "preferred": True}],
            }
        },
    )

    # Sub-resource arrays — all optional; any combination may be provided.
    names: Optional[List[NameCreateSchema]] = None
    identifiers: Optional[List[IdentifierCreateSchema]] = None
    telecom: Optional[List[TelecomCreateSchema]] = None
    addresses: Optional[List[AddressCreateSchema]] = None
    photos: Optional[List[PhotoCreateSchema]] = None
    contacts: Optional[List[ContactCreateSchema]] = None
    communications: Optional[List[CommunicationCreateSchema]] = None
    general_practitioners: Optional[List[GeneralPractitionerCreateSchema]] = None
    links: Optional[List[LinkCreateSchema]] = None
