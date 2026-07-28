"""
Plain JSON response schemas for the PractitionerRole resource.

Sub-resource response models are renamed here to this project's
`PractitionerRole<Sub>Response` convention (the sibling project used its own
`PlainPR*`/`PlainPractitioner*`/`PlainBooking*` naming) — matches every
other resource port in this project. `extra="allow"` on every model lets
new fhir-server fields pass through without requiring a schema bump here.

Booking-specific schemas mirror the fhir-server's enriched response for
GET /practitioner-roles/booking — each item includes the linked
Practitioner's name, gender, photo, and qualifications alongside the role
data, plus enriched Location/HealthcareService data.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

# ── Sub-resource response schemas ──────────────────────────────────────────────


class PractitionerRoleIdentifierResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    use: Optional[str] = None
    type_system: Optional[str] = None
    type_code: Optional[str] = None
    type_display: Optional[str] = None
    type_text: Optional[str] = None
    system: Optional[str] = None
    value: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    assigner: Optional[str] = None


class PractitionerRoleCodeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class PractitionerRoleSpecialtyResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class PractitionerRoleLocationResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    reference_display: Optional[str] = None


class PractitionerRoleHealthcareServiceResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    reference_display: Optional[str] = None


class PractitionerRoleCharacteristicResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class PractitionerRoleCommunicationResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class PractitionerRoleContactNameResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    use: Optional[str] = None
    text: Optional[str] = None
    family: Optional[str] = None
    given: Optional[List[str]] = None
    prefix: Optional[List[str]] = None
    suffix: Optional[List[str]] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None


class PractitionerRoleContactTelecomResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    system: Optional[str] = None
    value: Optional[str] = None
    use: Optional[str] = None
    rank: Optional[int] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None


class PractitionerRoleContactResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    purpose_system: Optional[str] = None
    purpose_code: Optional[str] = None
    purpose_display: Optional[str] = None
    purpose_text: Optional[str] = None
    address_use: Optional[str] = None
    address_type: Optional[str] = None
    address_text: Optional[str] = None
    address_line: Optional[List[str]] = None
    address_city: Optional[str] = None
    address_district: Optional[str] = None
    address_state: Optional[str] = None
    address_postal_code: Optional[str] = None
    address_country: Optional[str] = None
    address_period_start: Optional[str] = None
    address_period_end: Optional[str] = None
    organization_type: Optional[str] = None
    organization_id: Optional[int] = None
    organization_display: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    names: Optional[List[PractitionerRoleContactNameResponse]] = None
    telecoms: Optional[List[PractitionerRoleContactTelecomResponse]] = None


class PractitionerRoleAvailableTimeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    days_of_week: Optional[List[str]] = None
    all_day: Optional[bool] = None
    available_start_time: Optional[str] = None
    available_end_time: Optional[str] = None


class PractitionerRoleNotAvailableTimeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    description: Optional[str] = None
    during_start: Optional[str] = None
    during_end: Optional[str] = None


class PractitionerRoleAvailabilityResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    available_times: Optional[List[PractitionerRoleAvailableTimeResponse]] = None
    not_available_times: Optional[List[PractitionerRoleNotAvailableTimeResponse]] = None


class PractitionerRoleEndpointResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    reference_display: Optional[str] = None


# ── Top-level response ─────────────────────────────────────────────────────────


class PractitionerRoleResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    active: Optional[bool] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None

    practitioner_ref_id: Optional[int] = None
    practitioner_display: Optional[str] = None

    organization_type: Optional[str] = None
    organization_id: Optional[int] = None
    organization_display: Optional[str] = None

    availability_exceptions: Optional[str] = None

    identifier: Optional[List[PractitionerRoleIdentifierResponse]] = None
    code: Optional[List[PractitionerRoleCodeResponse]] = None
    specialty: Optional[List[PractitionerRoleSpecialtyResponse]] = None
    location: Optional[List[PractitionerRoleLocationResponse]] = None
    healthcare_service: Optional[List[PractitionerRoleHealthcareServiceResponse]] = None
    characteristic: Optional[List[PractitionerRoleCharacteristicResponse]] = None
    communication: Optional[List[PractitionerRoleCommunicationResponse]] = None
    contact: Optional[List[PractitionerRoleContactResponse]] = None
    availability: Optional[List[PractitionerRoleAvailabilityResponse]] = None
    endpoint: Optional[List[PractitionerRoleEndpointResponse]] = None

    user_id: Optional[str] = None
    org_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class PaginatedPractitionerRoleResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: List[PractitionerRoleResponse]


# ── Booking-enriched response schemas ─────────────────────────────────────────


class PractitionerRoleQualificationResponse(BaseModel):
    """A single qualification entry for a Practitioner in the booking response."""

    model_config = ConfigDict(extra="allow")

    code: Optional[str] = None
    display: Optional[str] = None
    text: Optional[str] = None


class PractitionerRoleNameResponse(BaseModel):
    """Structured name for a Practitioner in the booking response."""

    model_config = ConfigDict(extra="allow")

    text: Optional[str] = None
    family: Optional[str] = None
    given: Optional[List[str]] = None
    prefix: Optional[List[str]] = None
    suffix: Optional[List[str]] = None


class PractitionerRoleDetailTelecomResponse(BaseModel):
    """A single telecom entry within the booking response's practitioner_detail block."""

    model_config = ConfigDict(extra="allow")

    system: Optional[str] = None
    value: Optional[str] = None
    use: Optional[str] = None
    rank: Optional[int] = None


class PractitionerRoleDetailLanguageResponse(BaseModel):
    """A single language entry within the booking response's practitioner_detail block."""

    model_config = ConfigDict(extra="allow")

    code: Optional[str] = None
    display: Optional[str] = None
    preferred: Optional[bool] = None


class PractitionerDetailResponse(BaseModel):
    """
    Enriched Practitioner data embedded in each booking response item — the
    fhir-server joins the linked Practitioner record onto the
    PractitionerRole so booking UIs don't need a second request.

    `telecom`/`languages` are typed (rather than left as raw dicts, as the
    sibling project's PlainPractitionerDetail does) so they translate into
    proper nested GraphQL object types instead of an opaque JSON scalar —
    same reasoning applied to every other resource's sub-arrays in this project.
    """

    model_config = ConfigDict(extra="allow")

    id: Optional[int] = None
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    name: Optional[PractitionerRoleNameResponse] = None
    telecom: Optional[List[PractitionerRoleDetailTelecomResponse]] = None
    languages: Optional[List[PractitionerRoleDetailLanguageResponse]] = None
    qualifications: Optional[List[PractitionerRoleQualificationResponse]] = None
    photo_url: Optional[str] = None


class PractitionerRoleBookingLocationResponse(PractitionerRoleLocationResponse):
    """Location reference enriched with Location model data for booking UIs."""

    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    address_text: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_postal_code: Optional[str] = None
    address_country: Optional[str] = None
    phone: Optional[str] = None


class PractitionerRoleBookingHealthcareServiceResponse(PractitionerRoleHealthcareServiceResponse):
    """HealthcareService reference enriched with HealthcareService model data for booking UIs."""

    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    comment: Optional[str] = None
    appointment_required: Optional[bool] = None
    category: Optional[str] = None
    availability_exceptions: Optional[str] = None


class PractitionerRoleBookingResponse(PractitionerRoleResponse):
    """
    PractitionerRole enriched with the linked Practitioner's details and
    resolved Location/HealthcareService data — used by GET
    /practitioner-roles/booking.
    """

    practitioner_detail: Optional[PractitionerDetailResponse] = None
    location: Optional[List[PractitionerRoleBookingLocationResponse]] = None
    healthcare_service: Optional[List[PractitionerRoleBookingHealthcareServiceResponse]] = None


class PaginatedPractitionerRoleBookingResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: List[PractitionerRoleBookingResponse]
