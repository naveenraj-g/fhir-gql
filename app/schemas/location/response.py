"""
Pydantic response models for FHIR Location resources.

These models describe the shape of data returned by the fhir-server and
re-serialised by this middleware layer to API consumers. Sub-resource arrays
use typed models (LocationIdentifierResponse, etc.) rather than
List[Dict[str, Any]] — untyped dicts would force a raw JSON scalar into the
generated GraphQL schema instead of a proper nested object type, defeating
much of the point of exposing this over GraphQL. `extra="allow"` on every
model still gives the same forward-compatibility guarantee for new
fhir-server fields as an untyped dict would.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

# ── Sub-resource response schemas (mirror fhir-server plain responses) ────────


class LocationIdentifierResponse(BaseModel):
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


class LocationTypeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class LocationTelecomResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    system: Optional[str] = None
    value: Optional[str] = None
    use: Optional[str] = None
    rank: Optional[int] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None


class LocationHoursOfOperationResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    days_of_week: Optional[List[str]] = None
    all_day: Optional[bool] = None
    opening_time: Optional[str] = None
    closing_time: Optional[str] = None


class LocationEndpointResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    reference_display: Optional[str] = None


# ── Top-level response ─────────────────────────────────────────────────────────


class LocationResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    status: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    mode: Optional[str] = None

    operational_status_system: Optional[str] = None
    operational_status_code: Optional[str] = None
    operational_status_display: Optional[str] = None

    address_use: Optional[str] = None
    address_type: Optional[str] = None
    address_text: Optional[str] = None
    address_city: Optional[str] = None
    address_district: Optional[str] = None
    address_state: Optional[str] = None
    address_postal_code: Optional[str] = None
    address_country: Optional[str] = None
    address_period_start: Optional[str] = None
    address_period_end: Optional[str] = None

    physical_type_system: Optional[str] = None
    physical_type_code: Optional[str] = None
    physical_type_display: Optional[str] = None
    physical_type_text: Optional[str] = None

    managing_organization_type: Optional[str] = None
    managing_organization_id: Optional[str] = None
    managing_organization_display: Optional[str] = None
    part_of_type: Optional[str] = None
    part_of_id: Optional[str] = None
    part_of_display: Optional[str] = None

    availability_exceptions: Optional[str] = None

    position_longitude: Optional[float] = None
    position_latitude: Optional[float] = None
    position_altitude: Optional[float] = None

    identifier: Optional[List[LocationIdentifierResponse]] = None
    alias: Optional[List[str]] = None
    type: Optional[List[LocationTypeResponse]] = None
    telecom: Optional[List[LocationTelecomResponse]] = None
    hours_of_operation: Optional[List[LocationHoursOfOperationResponse]] = None
    endpoint: Optional[List[LocationEndpointResponse]] = None

    user_id: Optional[str] = None
    org_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class PaginatedLocationResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: List[LocationResponse]
