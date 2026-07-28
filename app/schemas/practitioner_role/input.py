"""
Input schemas for the PractitionerRole resource endpoints.

Three schemas cover the write surfaces:
  - PractitionerRoleCreateSchema  — POST /practitioner-roles body
  - PractitionerRolePatchSchema   — PATCH /practitioner-roles/{id} body
  - ListPractitionerRolesSchema   — GET /practitioner-roles query parameters

Design notes:
  - Unlike Practitioner (child arrays via sub-routes), PractitionerRole accepts
    ALL child arrays directly in the create body (identifier, code, specialty,
    location, healthcare_service, characteristic, communication, contact,
    availability, endpoint) — matching Organization/Location/HealthcareService's
    shape, not Practitioner's.
  - `practitioner` (-> Practitioner), `organization` (-> Organization), each
    `location[]` entry (-> Location), and each `healthcare_service[]` entry
    (-> HealthcareService) are validated for existence + tenant match in
    PractitionerRoleService — the fourth resource to need this, and the
    deepest cross-container fan-out yet (four sibling clients). `endpoint[]`
    (-> Endpoint) is NOT validated — this project doesn't implement Endpoint,
    same as every other resource's own unvalidated `endpoint` field.
  - user_id/org_id/practitioner/organization are all Optional (matches
    Organization/HealthcareService's convention).
  - None of the child arrays are patchable — PractitionerRolePatchSchema only
    exposes active/period_start/period_end/availability_exceptions.
  - Fixed FHIR code sets reuse the shared enums in app.schemas.enums
    (IdentifierUse, ContactPointSystem, ContactPointUse, AddressUse,
    AddressType, HumanNameUse, DayOfWeek) instead of the sibling's plain
    strings — same upgrade applied to Location's/HealthcareService's ports.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import (
    AddressType,
    AddressUse,
    ContactPointSystem,
    ContactPointUse,
    DayOfWeek,
    HumanNameUse,
    IdentifierUse,
)

# ── Sub-resource schemas ───────────────────────────────────────────────────────


class PractitionerRoleIdentifierInput(BaseModel):
    """A business identifier for the PractitionerRole."""

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


class PractitionerRoleCodeInput(BaseModel):
    """Role code for the PractitionerRole (e.g. General Physician, Nurse)."""

    model_config = ConfigDict(extra="forbid")

    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class PractitionerRoleSpecialtyInput(BaseModel):
    """Clinical specialty for the PractitionerRole (e.g. General Practice, Cardiology)."""

    model_config = ConfigDict(extra="forbid")

    coding_system: Optional[str] = Field(None, description="e.g. http://snomed.info/sct")
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class PractitionerRoleLocationInput(BaseModel):
    """A Location where this PractitionerRole provides services. Validated on create."""

    model_config = ConfigDict(extra="forbid")

    reference: str = Field(..., description="FHIR reference string e.g. 'Location/123'.")
    reference_display: Optional[str] = None


class PractitionerRoleHealthcareServiceInput(BaseModel):
    """A HealthcareService this PractitionerRole provides. Validated on create."""

    model_config = ConfigDict(extra="forbid")

    reference: str = Field(..., description="FHIR reference string e.g. 'HealthcareService/150001'.")
    reference_display: Optional[str] = None


class PractitionerRoleCharacteristicInput(BaseModel):
    """A characteristic of the PractitionerRole (e.g. accepts walk-ins)."""

    model_config = ConfigDict(extra="forbid")

    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class PractitionerRoleCommunicationInput(BaseModel):
    """A language the practitioner can communicate in for this role."""

    model_config = ConfigDict(extra="forbid")

    coding_system: Optional[str] = Field(None, description="e.g. urn:ietf:bcp:47")
    coding_code: Optional[str] = Field(None, description="BCP-47 language code (e.g. en-US).")
    coding_display: Optional[str] = None
    text: Optional[str] = None


class PractitionerRoleContactNameInput(BaseModel):
    """Name component within a PractitionerRole contact entry."""

    model_config = ConfigDict(extra="forbid")

    use: Optional[HumanNameUse] = None
    text: Optional[str] = None
    family: Optional[str] = None
    given: Optional[List[str]] = None
    prefix: Optional[List[str]] = None
    suffix: Optional[List[str]] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class PractitionerRoleContactTelecomInput(BaseModel):
    """Telecom contact point within a PractitionerRole contact entry."""

    model_config = ConfigDict(extra="forbid")

    system: Optional[ContactPointSystem] = None
    value: Optional[str] = None
    use: Optional[ContactPointUse] = None
    rank: Optional[int] = Field(None, ge=1)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class PractitionerRoleContactInput(BaseModel):
    """
    A contact for the PractitionerRole for a specific purpose (e.g. admin,
    billing) — flattens purpose CodeableConcept, address, and an
    organisation reference, with nested name/telecom child lists.
    """

    model_config = ConfigDict(extra="forbid")

    purpose_system: Optional[str] = None
    purpose_code: Optional[str] = None
    purpose_display: Optional[str] = None
    purpose_text: Optional[str] = None

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

    organization: Optional[str] = Field(None, description="FHIR reference to the contact organization, e.g. 'Organization/190001'.")
    organization_display: Optional[str] = None

    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    names: Optional[List[PractitionerRoleContactNameInput]] = None
    telecoms: Optional[List[PractitionerRoleContactTelecomInput]] = None


class PractitionerRoleAvailableTimeInput(BaseModel):
    """A time slot when the PractitionerRole is available."""

    model_config = ConfigDict(extra="forbid")

    days_of_week: Optional[List[DayOfWeek]] = None
    all_day: Optional[bool] = None
    available_start_time: Optional[str] = Field(None, description="Opening time in HH:mm:ss format.")
    available_end_time: Optional[str] = Field(None, description="Closing time in HH:mm:ss format.")


class PractitionerRoleNotAvailableTimeInput(BaseModel):
    """A period when the PractitionerRole is not available (e.g. annual leave)."""

    model_config = ConfigDict(extra="forbid")

    description: Optional[str] = None
    during_start: Optional[datetime] = None
    during_end: Optional[datetime] = None


class PractitionerRoleAvailabilityInput(BaseModel):
    """An availability group containing available and not-available time slots."""

    model_config = ConfigDict(extra="forbid")

    available_times: Optional[List[PractitionerRoleAvailableTimeInput]] = None
    not_available_times: Optional[List[PractitionerRoleNotAvailableTimeInput]] = None


class PractitionerRoleEndpointInput(BaseModel):
    """A technical endpoint reference. Not validated (no Endpoint resource in this project)."""

    model_config = ConfigDict(extra="forbid")

    reference: str = Field(..., description="FHIR reference string e.g. 'Endpoint/123'.")
    reference_display: Optional[str] = None


# ── Top-level schemas ──────────────────────────────────────────────────────────


class PractitionerRoleCreateSchema(BaseModel):
    """Schema for creating a PractitionerRole. All child arrays accepted directly in the create body."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "user_id": "user-123",
                "org_id": "org-456",
                "practitioner": "Practitioner/30001",
                "practitioner_display": "Dr. Jane Smith",
                "organization": "Organization/190001",
                "organization_display": "General Hospital",
                "active": True,
                "period_start": "2024-01-01T00:00:00Z",
                "code": [{"coding_system": "http://snomed.info/sct", "coding_code": "59058001", "coding_display": "General physician"}],
                "specialty": [{"coding_system": "http://snomed.info/sct", "coding_code": "394814009", "coding_display": "General practice"}],
                "location": [{"reference": "Location/1", "reference_display": "Main Clinic"}],
                "availability": [
                    {
                        "available_times": [
                            {"days_of_week": ["mon", "tue", "wed", "thu", "fri"], "available_start_time": "09:00:00", "available_end_time": "17:00:00"}
                        ]
                    }
                ],
            }
        },
    )

    user_id: Optional[str] = Field(None, description="User identifier for tenant scoping.")
    org_id: Optional[str] = Field(None, description="Organization identifier for tenant scoping.")

    practitioner: Optional[str] = Field(
        None,
        description=(
            "Reference to the Practitioner this role applies to, e.g. 'Practitioner/30001'. "
            "Validated — must reference an existing practitioner in the caller's own tenant."
        ),
    )
    practitioner_display: Optional[str] = None

    organization: Optional[str] = Field(
        None,
        description=(
            "Reference to the Organization, e.g. 'Organization/190001'. Validated — must "
            "reference an existing organization in the caller's own tenant."
        ),
    )
    organization_display: Optional[str] = None

    active: Optional[bool] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    availability_exceptions: Optional[str] = None

    identifier: Optional[List[PractitionerRoleIdentifierInput]] = None
    code: Optional[List[PractitionerRoleCodeInput]] = None
    specialty: Optional[List[PractitionerRoleSpecialtyInput]] = None
    location: Optional[List[PractitionerRoleLocationInput]] = Field(
        None, description="Location(s) where the practitioner provides this role. Each entry validated on create."
    )
    healthcare_service: Optional[List[PractitionerRoleHealthcareServiceInput]] = Field(
        None, description="HealthcareService(s) the practitioner provides in this role. Each entry validated on create."
    )
    characteristic: Optional[List[PractitionerRoleCharacteristicInput]] = None
    communication: Optional[List[PractitionerRoleCommunicationInput]] = None
    contact: Optional[List[PractitionerRoleContactInput]] = None
    availability: Optional[List[PractitionerRoleAvailabilityInput]] = None
    endpoint: Optional[List[PractitionerRoleEndpointInput]] = None


class PractitionerRolePatchSchema(BaseModel):
    """Schema for patching a PractitionerRole. Only these 4 scalar fields are patchable."""

    model_config = ConfigDict(extra="forbid")

    active: Optional[bool] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    availability_exceptions: Optional[str] = None


class ListPractitionerRolesSchema(BaseModel):
    """Query parameters for listing practitioner roles."""

    active: Optional[bool] = None
    practitioner_id: Optional[int] = Field(None, description="Filter to roles for a specific Practitioner.")
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    limit: int = Field(20, ge=1, le=200)
    offset: int = Field(0, ge=0)
