"""
Input schemas for the Slot resource endpoints.

Four schemas cover the write surfaces:
  - SlotCreateSchema   — POST /slots body (manual single-slot creation)
  - SlotGenerateSchema — POST /slots/generate body (availability-aware bulk generation)
  - SlotPatchSchema    — PATCH /slots/{id} body
  - ListSlotsSchema    — GET /slots query parameters

Design notes (diverging from the sibling project on purpose):
  - `schedule` is validated for existence + tenant match in SlotService via
    the shared `validate_reference` helper — the sibling never validated it.
  - `start`/`end` are required on SlotCreateSchema — the sibling left them
    Optional even though a boundless Slot isn't practically bookable.
  - `service_category`/`service_type`/`specialty` stay Optional here; when
    omitted, SlotService fills them in from the parent Schedule's own
    (already-derived) stored values — the schema layer doesn't need to know
    about that, it just allows the caller to override per-slot if they want.
  - `status` uses the new `SlotStatus` enum instead of a plain string.
  - user_id/org_id are Optional (matches Organization/HealthcareService/Schedule).
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.enums import IdentifierUse
from app.schemas.slot.enums import SlotStatus

# ── Sub-resource schemas ───────────────────────────────────────────────────────


class SlotIdentifierInput(BaseModel):
    """A business identifier for a Slot."""

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


class SlotServiceCategoryInput(BaseModel):
    """A broad category of service this Slot is for. Defaults from the parent Schedule if omitted."""

    model_config = ConfigDict(extra="forbid")

    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class SlotServiceTypeInput(BaseModel):
    """A specific service type this Slot is for. Defaults from the parent Schedule if omitted."""

    model_config = ConfigDict(extra="forbid")

    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


class SlotSpecialtyInput(BaseModel):
    """A clinical specialty this Slot is for. Defaults from the parent Schedule if omitted."""

    model_config = ConfigDict(extra="forbid")

    coding_system: Optional[str] = None
    coding_code: Optional[str] = None
    coding_display: Optional[str] = None
    text: Optional[str] = None


# ── Top-level schemas ──────────────────────────────────────────────────────────


class SlotCreateSchema(BaseModel):
    """
    Schema for manually creating a single Slot.

    `schedule` is validated for existence + tenant match. `service_category`/
    `service_type`/`specialty`, when omitted, are filled in from the parent
    Schedule's own stored values by SlotService — not by this schema.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "user_id": "user-123",
                "org_id": "org-456",
                "schedule": "Schedule/12",
                "schedule_display": "Dr. Smith — General Practice",
                "status": "free",
                "start": "2024-06-03T09:00:00Z",
                "end": "2024-06-03T09:30:00Z",
                "overbooked": False,
            }
        },
    )

    user_id: Optional[str] = Field(None, description="User identifier for tenant scoping.")
    org_id: Optional[str] = Field(None, description="Organization identifier for tenant scoping.")

    schedule: str = Field(
        ...,
        description="Reference to the parent Schedule, e.g. 'Schedule/12'. Validated for existence + tenant match.",
    )
    schedule_display: Optional[str] = None

    status: SlotStatus = Field(..., description="busy|free|busy-unavailable|busy-tentative|entered-in-error")
    start: datetime = Field(..., description="Start of the time period the slot represents.")
    end: datetime = Field(..., description="End of the time period the slot represents.")

    overbooked: Optional[bool] = Field(False, description="True if the slot has already been overbooked.")
    comment: Optional[str] = None

    appointment_type_system: Optional[str] = None
    appointment_type_code: Optional[str] = None
    appointment_type_display: Optional[str] = None
    appointment_type_text: Optional[str] = None

    identifier: Optional[List[SlotIdentifierInput]] = None
    service_category: Optional[List[SlotServiceCategoryInput]] = Field(
        None, description="Defaults from the parent Schedule's own stored value if omitted."
    )
    service_type: Optional[List[SlotServiceTypeInput]] = Field(
        None, description="Defaults from the parent Schedule's own stored value if omitted."
    )
    specialty: Optional[List[SlotSpecialtyInput]] = Field(
        None, description="Defaults from the parent Schedule's own stored value if omitted."
    )


class SlotGenerateSchema(BaseModel):
    """
    Schema for POST /slots/generate — availability-aware bulk Slot creation.

    The Schedule's PractitionerRole actor must have at least one
    `availability[]` entry with `available_times` declared (enforced in
    SlotService, not here) — slots are only generated inside those declared
    windows, for matching days within [generation_start, generation_end],
    skipping declared `not_available_times` and any already-existing Slot.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: Optional[str] = None
    org_id: Optional[str] = None

    schedule_id: int = Field(..., description="The Schedule to generate Slots for.")
    generation_start: datetime = Field(..., description="Start of the date range to generate slots within.")
    generation_end: datetime = Field(..., description="End of the date range to generate slots within.")
    slot_duration_minutes: int = Field(..., ge=1, le=1440, description="Duration of each generated slot, in minutes.")

    overbooked: Optional[bool] = False
    comment: Optional[str] = None

    appointment_type_system: Optional[str] = None
    appointment_type_code: Optional[str] = None
    appointment_type_display: Optional[str] = None
    appointment_type_text: Optional[str] = None

    service_category: Optional[List[SlotServiceCategoryInput]] = Field(
        None, description="Overrides the Schedule's own stored value for the generated slots, if provided."
    )
    service_type: Optional[List[SlotServiceTypeInput]] = Field(
        None, description="Overrides the Schedule's own stored value for the generated slots, if provided."
    )
    specialty: Optional[List[SlotSpecialtyInput]] = Field(
        None, description="Overrides the Schedule's own stored value for the generated slots, if provided."
    )

    @model_validator(mode="after")
    def _check_range(self) -> "SlotGenerateSchema":
        if self.generation_end <= self.generation_start:
            raise ValueError("generation_end must be after generation_start.")
        return self


class SlotPatchSchema(BaseModel):
    """
    Schema for patching a Slot. `schedule` and the sub-resource arrays are
    create-only; delete and re-create to change those.
    """

    model_config = ConfigDict(extra="forbid")

    status: Optional[SlotStatus] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    overbooked: Optional[bool] = None
    comment: Optional[str] = None

    appointment_type_system: Optional[str] = None
    appointment_type_code: Optional[str] = None
    appointment_type_display: Optional[str] = None
    appointment_type_text: Optional[str] = None


class ListSlotsSchema(BaseModel):
    """Query parameters for listing slots."""

    status: Optional[SlotStatus] = None
    schedule_id: Optional[int] = Field(None, description="Filter to slots on a specific Schedule.")
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    start_after: Optional[datetime] = Field(None, description="Only include slots starting at/after this datetime.")
    start_before: Optional[datetime] = Field(None, description="Only include slots starting before this datetime.")
    limit: int = Field(20, ge=1, le=200)
    offset: int = Field(0, ge=0)
