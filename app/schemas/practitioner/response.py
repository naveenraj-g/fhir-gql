"""
Plain JSON response schemas for the Practitioner resource.

Sub-resource response models are renamed here to this project's
`Practitioner<Sub>Response` convention (the sibling project used its own
`Plain*` naming) — matches Patient's/Organization's/Location's/
HealthcareService's naming. `extra="allow"` on every model lets new
fhir-server fields pass through without requiring a schema bump here.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

# ── Sub-resource response schemas ──────────────────────────────────────────────


class PractitionerNameResponse(BaseModel):
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


class PractitionerIdentifierResponse(BaseModel):
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


class PractitionerTelecomResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    system: Optional[str] = None
    value: Optional[str] = None
    use: Optional[str] = None
    rank: Optional[int] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None


class PractitionerAddressResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    use: Optional[str] = None
    type: Optional[str] = None
    text: Optional[str] = None
    line: Optional[List[str]] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None


class PractitionerPhotoResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    content_type: Optional[str] = None
    language: Optional[str] = None
    data: Optional[str] = None
    url: Optional[str] = None
    size: Optional[int] = None
    hash: Optional[str] = None
    title: Optional[str] = None
    creation: Optional[str] = None


class QualificationIdentifierResponse(BaseModel):
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


class PractitionerQualificationResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    identifier: Optional[List[QualificationIdentifierResponse]] = None
    code_system: Optional[str] = None
    code_code: Optional[str] = None
    code_display: Optional[str] = None
    code_text: Optional[str] = None
    status_system: Optional[str] = None
    status_code: Optional[str] = None
    status_display: Optional[str] = None
    status_text: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    issuer_type: Optional[str] = None
    issuer_id: Optional[int] = None
    issuer_display: Optional[str] = None


class PractitionerCommunicationResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    language_system: Optional[str] = None
    language_code: Optional[str] = None
    language_display: Optional[str] = None
    language_text: Optional[str] = None
    preferred: Optional[bool] = None


# ── Top-level response ─────────────────────────────────────────────────────────


class PractitionerResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    active: Optional[bool] = None
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    deceased_boolean: Optional[bool] = None
    deceased_datetime: Optional[str] = None

    name: Optional[List[PractitionerNameResponse]] = None
    identifier: Optional[List[PractitionerIdentifierResponse]] = None
    telecom: Optional[List[PractitionerTelecomResponse]] = None
    address: Optional[List[PractitionerAddressResponse]] = None
    photo: Optional[List[PractitionerPhotoResponse]] = None
    qualification: Optional[List[PractitionerQualificationResponse]] = None
    communication: Optional[List[PractitionerCommunicationResponse]] = None

    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class PaginatedPractitionerResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: List[PractitionerResponse]


# ── Sub-resource list response wrappers ({data, total} — no limit/offset) ─────


class PractitionerNameListResponse(BaseModel):
    data: List[PractitionerNameResponse]
    total: int


class PractitionerIdentifierListResponse(BaseModel):
    data: List[PractitionerIdentifierResponse]
    total: int


class PractitionerTelecomListResponse(BaseModel):
    data: List[PractitionerTelecomResponse]
    total: int


class PractitionerAddressListResponse(BaseModel):
    data: List[PractitionerAddressResponse]
    total: int


class PractitionerPhotoListResponse(BaseModel):
    data: List[PractitionerPhotoResponse]
    total: int


class PractitionerQualificationListResponse(BaseModel):
    data: List[PractitionerQualificationResponse]
    total: int


class PractitionerCommunicationListResponse(BaseModel):
    data: List[PractitionerCommunicationResponse]
    total: int
