"""
Plain JSON response schemas for the Slot resource.

Sub-resource models are typed (not raw dicts), matching every other
resource port in this project. `extra="allow"` lets new fhir-server fields
pass through without a schema bump.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

# ── Sub-resource response schemas ──────────────────────────────────────────────


class SlotIdentifierResponse(BaseModel):
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


class SlotServiceCategoryResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class SlotServiceTypeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class SlotSpecialtyResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


# ── Top-level response ─────────────────────────────────────────────────────────


class SlotResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    schedule_type: Optional[str] = None
    schedule_id: Optional[int] = None
    schedule_display: Optional[str] = None

    status: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    overbooked: Optional[bool] = None
    comment: Optional[str] = None

    appointment_type_system: Optional[str] = None
    appointment_type_code: Optional[str] = None
    appointment_type_display: Optional[str] = None
    appointment_type_text: Optional[str] = None

    identifier: Optional[List[SlotIdentifierResponse]] = None
    service_category: Optional[List[SlotServiceCategoryResponse]] = None
    service_type: Optional[List[SlotServiceTypeResponse]] = None
    specialty: Optional[List[SlotSpecialtyResponse]] = None

    user_id: Optional[str] = None
    org_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class PaginatedSlotResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: List[SlotResponse]


class SlotGenerateResponse(BaseModel):
    """
    Result of POST /slots/generate.

    `skipped_count` (this project's addition — not in the sibling) counts
    computed windows that were dropped because they overlapped an
    already-existing Slot on the Schedule, keeping generate() safely
    re-callable to extend a date range without duplicating slots.
    """

    schedule_id: int
    generated_count: int
    skipped_count: int
    failed_count: int
    slot_ids: List[int]
    generation_start: str
    generation_end: str
    slot_duration_minutes: int
    errors: List[str]
