"""PractitionerRole.availableTime — mirrors fhir-server's
app/schemas/practitioner_role/input/available_time.py field-for-field.

fhir-server scopes its days-of-week enum to `PractitionerRoleDayOfWeek`
(app.schemas.enums), but its values (mon..sun) are identical to the
shared `DayOfWeek` enum this gateway already uses for Location's
hoursOfOperation — reused here rather than introducing a duplicate enum,
same precedent set when porting HealthcareService's availableTime.
"""

from datetime import time

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import DayOfWeek


class PractitionerRoleAvailableTimeInput(BaseModel):
    """PractitionerRole.availableTime — times the role is available (BackboneElement)."""

    model_config = ConfigDict(extra="forbid")
    days_of_week: list[DayOfWeek] | None = Field(
        None,
        description="Indicates which days of the week are available between the start/end times, e.g. ['mon', 'wed', 'fri'].",
    )
    all_day: bool | None = Field(
        None,
        description="Is this always available (hence times are irrelevant)? e.g. 24 hour service.",
    )
    available_start_time: time | None = Field(
        None, description="The opening time, in HH:MM:SS format."
    )
    available_end_time: time | None = Field(
        None, description="The closing time, in HH:MM:SS format."
    )
