"""
Pydantic response models for FHIR HealthcareService resources.

Sub-resource arrays use typed models (renamed here to this project's
`HealthcareService<Sub>Response` convention, matching `Org*Response`/
`Location*Response` — the sibling project used its own `PlainHS*` naming)
rather than untyped dicts, giving both cleaner OpenAPI docs and proper
nested GraphQL object types. `extra="allow"` on every model still gives the
same forward-compatibility guarantee for new fhir-server fields.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

# ── Sub-resource response schemas (mirror fhir-server plain responses) ────────


class HealthcareServiceIdentifierResponse(BaseModel):
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


class HealthcareServiceCategoryResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class HealthcareServiceTypeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class HealthcareServiceSpecialtyResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class HealthcareServiceLocationResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    reference_display: Optional[str] = None


class HealthcareServiceTelecomResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    system: Optional[str] = None
    value: Optional[str] = None
    use: Optional[str] = None
    rank: Optional[int] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None


class HealthcareServiceCoverageAreaResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    reference_display: Optional[str] = None


class HealthcareServiceProvisionCodeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class HealthcareServiceEligibilityResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    code_system: Optional[str] = None
    code_code: Optional[str] = None
    code_display: Optional[str] = None
    code_text: Optional[str] = None
    comment: Optional[str] = None


class HealthcareServiceProgramResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class HealthcareServiceCharacteristicResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class HealthcareServiceCommunicationResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class HealthcareServiceReferralMethodResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class HealthcareServiceAvailableTimeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    days_of_week: Optional[List[str]] = None
    all_day: Optional[bool] = None
    available_start_time: Optional[str] = None
    available_end_time: Optional[str] = None


class HealthcareServiceNotAvailableResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    description: Optional[str] = None
    during_start: Optional[str] = None
    during_end: Optional[str] = None


class HealthcareServiceEndpointResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    reference_display: Optional[str] = None


# ── Top-level response ─────────────────────────────────────────────────────────


class HealthcareServiceResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    active: Optional[bool] = None
    name: Optional[str] = None
    comment: Optional[str] = None
    extra_details: Optional[str] = None
    appointment_required: Optional[bool] = None
    availability_exceptions: Optional[str] = None

    provided_by_type: Optional[str] = None
    provided_by_id: Optional[int] = None
    provided_by_display: Optional[str] = None

    photo_content_type: Optional[str] = None
    photo_language: Optional[str] = None
    photo_data: Optional[str] = None
    photo_url: Optional[str] = None
    photo_size: Optional[int] = None
    photo_hash: Optional[str] = None
    photo_title: Optional[str] = None
    photo_creation: Optional[str] = None

    identifier: Optional[List[HealthcareServiceIdentifierResponse]] = None
    category: Optional[List[HealthcareServiceCategoryResponse]] = None
    type: Optional[List[HealthcareServiceTypeResponse]] = None
    specialty: Optional[List[HealthcareServiceSpecialtyResponse]] = None
    location: Optional[List[HealthcareServiceLocationResponse]] = None
    telecom: Optional[List[HealthcareServiceTelecomResponse]] = None
    coverage_area: Optional[List[HealthcareServiceCoverageAreaResponse]] = None
    service_provision_code: Optional[List[HealthcareServiceProvisionCodeResponse]] = (
        None
    )
    eligibility: Optional[List[HealthcareServiceEligibilityResponse]] = None
    program: Optional[List[HealthcareServiceProgramResponse]] = None
    characteristic: Optional[List[HealthcareServiceCharacteristicResponse]] = None
    communication: Optional[List[HealthcareServiceCommunicationResponse]] = None
    referral_method: Optional[List[HealthcareServiceReferralMethodResponse]] = None
    available_time: Optional[List[HealthcareServiceAvailableTimeResponse]] = None
    not_available: Optional[List[HealthcareServiceNotAvailableResponse]] = None
    endpoint: Optional[List[HealthcareServiceEndpointResponse]] = None

    user_id: Optional[str] = None
    org_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class PaginatedHealthcareServiceResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: List[HealthcareServiceResponse]
