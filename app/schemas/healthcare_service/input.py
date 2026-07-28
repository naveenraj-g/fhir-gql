"""
Input schemas for FHIR HealthcareService resource endpoints.

Three schemas cover the full API surface:
  - HealthcareServiceCreateSchema: validated body for POST /healthcare-services
  - HealthcareServicePatchSchema:  validated body for PATCH /healthcare-services/{id}
  - ListHealthcareServicesSchema:  validated query parameters for GET /healthcare-services

Design decisions:
  - user_id/org_id are Optional (matches app/schemas/organization/input.py,
    unlike Location's/Patient's required tenant fields — ported faithfully
    from the sibling project rather than forced to match Location).
  - `provided_by` (-> Organization, scalar), `location[]` (-> Location, list),
    and `coverage_area[]` (-> Location, list) are validated for existence and
    tenant match on create (see app/services/healthcare_service_service.py) —
    but, unlike Location's `part_of`/`managing_organization`, none of them
    are patchable: HealthcareServicePatchSchema only exposes scalar and
    photo_* fields, matching the sibling project exactly. No cycle-detection
    concern applies since these are all create-only.
  - Fixed, FHIR-defined small code sets use the shared enums in
    app.schemas.enums (IdentifierUse, ContactPointSystem, ContactPointUse,
    DayOfWeek) rather than plain strings, matching the Organization/Location
    convention. Open/extensible code sets (category/type/specialty/
    service_provision_code/eligibility/program/characteristic/communication/
    referral_method coding) stay as plain strings, same reasoning as
    OrgTypeInput.coding_code.
  - `endpoint[]` references an Endpoint resource, which this project doesn't
    implement — left as an opaque reference string, same as Organization's
    and Location's own `endpoint` fields (unvalidated).
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import (
    ContactPointSystem,
    ContactPointUse,
    DayOfWeek,
    IdentifierUse,
)

# ── Array sub-schemas ──────────────────────────────────────────────────────────


class HealthcareServiceIdentifierInput(BaseModel):
    """A business identifier for a HealthcareService (e.g. a facility service code)."""

    model_config = ConfigDict(extra="forbid")

    use: Optional[IdentifierUse] = Field(
        None, description="usual|official|temp|secondary|old"
    )
    type_system: Optional[str] = None
    type_code: Optional[str] = None
    type_display: Optional[str] = None
    type_text: Optional[str] = None
    system: Optional[str] = Field(None, description="URI of the identifier namespace.")
    value: str = Field(..., description="Identifier value.")
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    assigner: Optional[str] = Field(
        None, description="Display name of the assigning organization."
    )


class HealthcareServiceCategoryInput(BaseModel):
    """A broad category grouping the HealthcareService (e.g. 'General Practice', 'Dental')."""

    model_config = ConfigDict(extra="forbid")

    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class HealthcareServiceTypeInput(BaseModel):
    """A specific type of service being delivered within the broad category."""

    model_config = ConfigDict(extra="forbid")

    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class HealthcareServiceSpecialtyInput(BaseModel):
    """A clinical specialty associated with this HealthcareService (e.g. 'Cardiology')."""

    model_config = ConfigDict(extra="forbid")

    coding_system: Optional[str] = Field(
        None, description="e.g. http://snomed.info/sct"
    )
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class HealthcareServiceLocationInput(BaseModel):
    """A Location where this HealthcareService is provided. Validated on create."""

    model_config = ConfigDict(extra="forbid")

    reference: str = Field(..., description="FHIR reference string e.g. 'Location/1'.")
    reference_display: Optional[str] = None


class HealthcareServiceTelecomInput(BaseModel):
    """A contact point for this HealthcareService (phone, email, fax, etc.)."""

    model_config = ConfigDict(extra="forbid")

    system: ContactPointSystem = Field(
        ..., description="phone|fax|email|pager|url|sms|other"
    )
    value: str = Field(..., description="Contact value.")
    use: Optional[ContactPointUse] = Field(
        None, description="home|work|temp|old|mobile"
    )
    rank: Optional[int] = Field(None, ge=1)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class HealthcareServiceCoverageAreaInput(BaseModel):
    """A Location defining the coverage area for this HealthcareService. Validated on create."""

    model_config = ConfigDict(extra="forbid")

    reference: str = Field(..., description="FHIR reference string e.g. 'Location/1'.")
    reference_display: Optional[str] = None


class HealthcareServiceProvisionCodeInput(BaseModel):
    """Conditions under which the service is available (e.g. free, discounted, private-pay)."""

    model_config = ConfigDict(extra="forbid")

    coding_system: Optional[str] = None
    coding_code: Optional[str] = Field(None, description="e.g. 'free', 'disc', 'cost'.")
    coding_display: Optional[str] = None
    text: Optional[str] = None


class HealthcareServiceEligibilityInput(BaseModel):
    """Eligibility criteria required to receive this HealthcareService."""

    model_config = ConfigDict(extra="forbid")

    code_system: Optional[str] = None
    code_code: Optional[str] = None
    code_display: Optional[str] = None
    code_text: Optional[str] = None
    comment: Optional[str] = Field(
        None, description="Additional eligibility details or requirements."
    )


class HealthcareServiceProgramInput(BaseModel):
    """A health program this service is part of (e.g. 'HACC', 'DVA')."""

    model_config = ConfigDict(extra="forbid")

    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class HealthcareServiceCharacteristicInput(BaseModel):
    """A characteristic of this HealthcareService (e.g. wheelchair accessible)."""

    model_config = ConfigDict(extra="forbid")

    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class HealthcareServiceCommunicationInput(BaseModel):
    """A language in which this HealthcareService can communicate with patients."""

    model_config = ConfigDict(extra="forbid")

    coding_system: Optional[str] = Field(None, description="e.g. urn:ietf:bcp:47")
    coding_code: Optional[str] = Field(
        None, description="BCP-47 language code (e.g. 'en', 'fr', 'ar')."
    )
    coding_display: Optional[str] = None
    text: Optional[str] = None


class HealthcareServiceReferralMethodInput(BaseModel):
    """Ways that the service accepts referrals (e.g. phone, fax, letter, email)."""

    model_config = ConfigDict(extra="forbid")

    coding_system: Optional[str] = None
    coding_code: Optional[str] = Field(None, description="e.g. 'phone', 'fax', 'elec'.")
    coding_display: Optional[str] = None
    text: Optional[str] = None


class HealthcareServiceAvailableTimeInput(BaseModel):
    """A time slot during which this HealthcareService is available."""

    model_config = ConfigDict(extra="forbid")

    days_of_week: Optional[List[DayOfWeek]] = None
    all_day: Optional[bool] = Field(
        None, description="True if available all day on the listed days."
    )
    available_start_time: Optional[str] = Field(
        None, description="Opening time in HH:mm:ss format."
    )
    available_end_time: Optional[str] = Field(
        None, description="Closing time in HH:mm:ss format."
    )


class HealthcareServiceNotAvailableInput(BaseModel):
    """A period during which this HealthcareService is not available."""

    model_config = ConfigDict(extra="forbid")

    description: str = Field(
        ..., description="Reason for unavailability e.g. 'Public holiday'."
    )
    during_start: Optional[datetime] = None
    during_end: Optional[datetime] = None


class HealthcareServiceEndpointInput(BaseModel):
    """A technical endpoint providing access to this HealthcareService. Not validated (no Endpoint resource in this project)."""

    model_config = ConfigDict(extra="forbid")

    reference: str = Field(..., description="FHIR reference string e.g. 'Endpoint/1'.")
    reference_display: Optional[str] = None


# ── Top-level schemas ──────────────────────────────────────────────────────────


class HealthcareServiceCreateSchema(BaseModel):
    """
    Schema for creating a HealthcareService.

    user_id/org_id are Optional (matches RegisterOrgSchema's convention, not
    LocationCreateSchema's required fields).
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "user_id": "user-123",
                "org_id": "org-456",
                "provided_by": "Organization/190001",
                "provided_by_display": "General Hospital",
                "active": True,
                "name": "General Practice Consultation",
                "comment": "Walk-in and appointment-based GP service",
                "appointment_required": False,
                "category": [
                    {
                        "coding_system": "http://example.org/service-category",
                        "coding_code": "17",
                        "coding_display": "General Practice",
                    }
                ],
                "available_time": [
                    {
                        "days_of_week": ["mon", "tue", "wed", "thu", "fri"],
                        "available_start_time": "09:00:00",
                        "available_end_time": "17:00:00",
                    }
                ],
            }
        },
    )

    # ── Tenant scoping ─────────────────────────────────────────────────────────
    user_id: Optional[str] = Field(
        None, description="User identifier for tenant scoping."
    )
    org_id: Optional[str] = Field(
        None, description="Organization identifier for tenant scoping."
    )

    # ── Providing organization ─────────────────────────────────────────────────
    provided_by: Optional[str] = Field(
        None,
        description=(
            "Reference to the Organization providing this service e.g. 'Organization/190001'. "
            "Validated on create — must reference an existing organization in the caller's tenant."
        ),
    )
    provided_by_display: Optional[str] = None

    # ── Core fields ────────────────────────────────────────────────────────────
    active: Optional[bool] = None
    name: Optional[str] = Field(None, description="Human-readable name of the service.")
    comment: Optional[str] = None
    extra_details: Optional[str] = None
    appointment_required: Optional[bool] = None
    availability_exceptions: Optional[str] = None

    # ── Photo (FHIR Attachment, stored flat) ──────────────────────────────────
    photo_content_type: Optional[str] = None
    photo_language: Optional[str] = None
    photo_data: Optional[str] = None
    photo_url: Optional[str] = None
    photo_size: Optional[int] = None
    photo_hash: Optional[str] = None
    photo_title: Optional[str] = None
    photo_creation: Optional[datetime] = None

    # ── Array sub-resources ────────────────────────────────────────────────────
    identifier: Optional[List[HealthcareServiceIdentifierInput]] = None
    category: Optional[List[HealthcareServiceCategoryInput]] = None
    type: Optional[List[HealthcareServiceTypeInput]] = None
    specialty: Optional[List[HealthcareServiceSpecialtyInput]] = None
    location: Optional[List[HealthcareServiceLocationInput]] = Field(
        None,
        description="Location(s) where the service is provided. Each entry validated on create.",
    )
    telecom: Optional[List[HealthcareServiceTelecomInput]] = None
    coverage_area: Optional[List[HealthcareServiceCoverageAreaInput]] = Field(
        None,
        description="Location(s) defining the coverage area. Each entry validated on create.",
    )
    service_provision_code: Optional[List[HealthcareServiceProvisionCodeInput]] = None
    eligibility: Optional[List[HealthcareServiceEligibilityInput]] = None
    program: Optional[List[HealthcareServiceProgramInput]] = None
    characteristic: Optional[List[HealthcareServiceCharacteristicInput]] = None
    communication: Optional[List[HealthcareServiceCommunicationInput]] = None
    referral_method: Optional[List[HealthcareServiceReferralMethodInput]] = None
    available_time: Optional[List[HealthcareServiceAvailableTimeInput]] = None
    not_available: Optional[List[HealthcareServiceNotAvailableInput]] = None
    endpoint: Optional[List[HealthcareServiceEndpointInput]] = None


class HealthcareServicePatchSchema(BaseModel):
    """
    Schema for patching a HealthcareService. Only scalar and photo_* fields
    are patchable — `provided_by`, `location`, `coverage_area`, and every
    array sub-resource are create-only; delete and re-create to correct
    those (matches the sibling project exactly).
    """

    model_config = ConfigDict(extra="forbid")

    active: Optional[bool] = None
    name: Optional[str] = None
    comment: Optional[str] = None
    extra_details: Optional[str] = None
    appointment_required: Optional[bool] = None
    availability_exceptions: Optional[str] = None

    photo_content_type: Optional[str] = None
    photo_language: Optional[str] = None
    photo_data: Optional[str] = None
    photo_url: Optional[str] = None
    photo_size: Optional[int] = None
    photo_hash: Optional[str] = None
    photo_title: Optional[str] = None
    photo_creation: Optional[datetime] = None


class ListHealthcareServicesSchema(BaseModel):
    """Query parameters for listing healthcare services."""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(
        None, description="Case-insensitive substring match on name."
    )
    active: Optional[bool] = Field(None, description="Filter by active status.")
    limit: int = Field(20, ge=1, le=200, description="Max results to return.")
    offset: int = Field(0, ge=0, description="Number of results to skip.")
