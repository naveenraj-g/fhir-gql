"""
Plain JSON response schemas for the Schedule resource.

`service_category`/`service_type`/`specialty` remain here as read-only
output arrays — they're still returned from the fhir-server (populated by
ScheduleService's derivation logic at create time), just no longer
client-writable input fields. Sub-resource models are typed (not raw dicts)
matching every other resource port in this project. `extra="allow"` lets
new fhir-server fields pass through without a schema bump.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

# ── Sub-resource response schemas ──────────────────────────────────────────────


class ScheduleIdentifierResponse(BaseModel):
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


class ScheduleServiceCategoryResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class ScheduleServiceTypeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class ScheduleSpecialtyResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class ScheduleActorResponse(BaseModel):
    """
    A single actor reference row as returned by the fhir-server — the
    reference string is split into reference_type + reference_id on read,
    same pattern used by every other resource's reference fields.
    """

    model_config = ConfigDict(extra="allow")

    id: int
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    reference_display: Optional[str] = None


# ── Top-level response ─────────────────────────────────────────────────────────


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    active: Optional[bool] = None
    comment: Optional[str] = None
    planning_horizon_start: Optional[str] = None
    planning_horizon_end: Optional[str] = None

    identifier: Optional[List[ScheduleIdentifierResponse]] = None
    service_category: Optional[List[ScheduleServiceCategoryResponse]] = None
    service_type: Optional[List[ScheduleServiceTypeResponse]] = None
    specialty: Optional[List[ScheduleSpecialtyResponse]] = None
    actor: Optional[List[ScheduleActorResponse]] = None

    user_id: Optional[str] = None
    org_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class PaginatedScheduleResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: List[ScheduleResponse]
