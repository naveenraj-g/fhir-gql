"""
Pydantic response models for FHIR Organization resources.

These models describe the shape of data returned by the fhir-server and
re-serialised by this middleware layer to API consumers. They mirror the
flat, relational structure the fhir-server uses internally rather than the
deeply-nested FHIR JSON wire format.

`extra="allow"` is set on all models so new fields added to the fhir-server
response are passed through transparently without requiring a schema update
here first — same convention as app/schemas/patient/response.py.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

# ── Sub-resource response schemas (mirror fhir-server plain responses) ────────


class OrgIdentifierResponse(BaseModel):
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


class OrgTypeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class OrgAliasResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    value: Optional[str] = None


class OrgTelecomResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    system: Optional[str] = None
    value: Optional[str] = None
    use: Optional[str] = None
    rank: Optional[int] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None


class OrgAddressResponse(BaseModel):
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


class OrgContactTelecomResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    system: Optional[str] = None
    value: Optional[str] = None
    use: Optional[str] = None
    rank: Optional[int] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None


class OrgContactResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    purpose_system: Optional[str] = None
    purpose_code: Optional[str] = None
    purpose_display: Optional[str] = None
    purpose_text: Optional[str] = None
    name_use: Optional[str] = None
    name_text: Optional[str] = None
    name_family: Optional[str] = None
    name_given: Optional[List[str]] = None
    name_prefix: Optional[List[str]] = None
    name_suffix: Optional[List[str]] = None
    name_period_start: Optional[str] = None
    name_period_end: Optional[str] = None
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
    telecoms: Optional[List[OrgContactTelecomResponse]] = None


class OrgEndpointResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    reference_display: Optional[str] = None


# ── Top-level response ─────────────────────────────────────────────────────────


class OrgResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    active: Optional[bool] = None
    name: Optional[str] = None
    partof_type: Optional[str] = None
    partof_id: Optional[int] = None
    partof_display: Optional[str] = None
    identifier: Optional[List[OrgIdentifierResponse]] = None
    type: Optional[List[OrgTypeResponse]] = None
    alias: Optional[List[OrgAliasResponse]] = None
    telecom: Optional[List[OrgTelecomResponse]] = None
    address: Optional[List[OrgAddressResponse]] = None
    contact: Optional[List[OrgContactResponse]] = None
    endpoint: Optional[List[OrgEndpointResponse]] = None
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class PaginatedOrgResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: List[OrgResponse]
