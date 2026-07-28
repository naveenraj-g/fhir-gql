"""
Input schemas for the Schedule resource endpoints.

Three schemas cover the write surfaces:
  - ScheduleCreateSchema  — POST /schedules body
  - SchedulePatchSchema   — PATCH /schedules/{id} body
  - ListSchedulesSchema   — GET /schedules query parameters

Design notes (diverging from the sibling project on purpose):
  - `service_category`/`service_type`/`specialty` are NOT accepted here at
    all — unlike the sibling project's naive passthrough, this project
    derives them in ScheduleService.create() by reading them off whichever
    PractitionerRole/HealthcareService actors are attached (the canonical
    FHIR place those concepts already live), rather than trusting the
    caller to retype them redundantly and possibly inconsistently. They
    still appear on ScheduleResponse as read-only computed output.
  - `actor` is required (`min_length=1`), unlike the sibling's fully
    Optional treatment — this matches FHIR R4's real 1..* cardinality, and
    the derivation feature needs at least one actor to derive from anyway.
    ScheduleService additionally enforces: at most one Practitioner/
    PractitionerRole actor (a Schedule belongs to one provider, not
    several — see app/services/schedule_service.py), and Patient actors
    are mutually exclusive with Practitioner/PractitionerRole/
    HealthcareService actors.
  - user_id/org_id are Optional (matches Organization/HealthcareService).
  - created_by/updated_by are NOT exposed — FhirClient injects them.
  - Fixed FHIR code sets reuse the shared enum in app.schemas.enums
    (IdentifierUse).
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import IdentifierUse

# ── Sub-resource schemas ───────────────────────────────────────────────────────


class ScheduleIdentifierInput(BaseModel):
    """A business identifier for a Schedule."""

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


class ScheduleActorInput(BaseModel):
    """
    A resource this Schedule provides availability for.

    Allowed reference types: Practitioner, PractitionerRole, Location,
    HealthcareService, Patient (all validated for existence + tenant match
    in ScheduleService), plus RelatedPerson/Device (FHIR-allowed but not
    implemented in this project — accepted unvalidated, same treatment as
    Endpoint elsewhere). Any other type is rejected.
    """

    model_config = ConfigDict(extra="forbid")

    reference: str = Field(
        ...,
        description=(
            "FHIR reference string identifying the actor, e.g. 'PractitionerRole/12'. "
            "Allowed types: Practitioner, PractitionerRole, Location, HealthcareService, "
            "Patient, RelatedPerson, Device."
        ),
    )
    reference_display: Optional[str] = None


# ── Top-level schemas ──────────────────────────────────────────────────────────


class ScheduleCreateSchema(BaseModel):
    """
    Schema for creating a Schedule.

    `service_category`/`service_type`/`specialty` are deliberately absent —
    ScheduleService derives them from the attached PractitionerRole/
    HealthcareService actors. `actor` is required (at least one entry, and
    must include a PractitionerRole or HealthcareService so there is
    something to derive from).
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "user_id": "user-123",
                "org_id": "org-456",
                "active": True,
                "comment": "Schedule for Dr. Smith — Mon/Wed/Fri mornings",
                "planning_horizon_start": "2024-01-01T08:00:00Z",
                "planning_horizon_end": "2024-12-31T12:00:00Z",
                "actor": [{"reference": "PractitionerRole/12", "reference_display": "Dr. Smith — General Practice"}],
            }
        },
    )

    user_id: Optional[str] = Field(None, description="User identifier for tenant scoping.")
    org_id: Optional[str] = Field(None, description="Organization identifier for tenant scoping.")

    active: Optional[bool] = None
    comment: Optional[str] = None

    planning_horizon_start: Optional[datetime] = None
    planning_horizon_end: Optional[datetime] = None

    identifier: Optional[List[ScheduleIdentifierInput]] = None

    actor: List[ScheduleActorInput] = Field(
        ...,
        min_length=1,
        description=(
            "The resource(s) this Schedule provides availability for. At least one entry is "
            "required, and at least one must be a PractitionerRole or HealthcareService so "
            "serviceCategory/serviceType/specialty can be derived. At most one Practitioner/"
            "PractitionerRole actor is allowed (a Schedule belongs to one provider), and Patient "
            "actors cannot be mixed with provider actors."
        ),
    )


class SchedulePatchSchema(BaseModel):
    """
    Schema for patching a Schedule. Only these scalar fields are patchable —
    `actor` and the derived service_category/service_type/specialty arrays
    are create-only; delete and re-create to change those.
    """

    model_config = ConfigDict(extra="forbid")

    active: Optional[bool] = None
    comment: Optional[str] = None
    planning_horizon_start: Optional[datetime] = None
    planning_horizon_end: Optional[datetime] = None


class ListSchedulesSchema(BaseModel):
    """Query parameters for listing schedules."""

    active: Optional[bool] = None
    limit: int = Field(20, ge=1, le=200)
    offset: int = Field(0, ge=0)
