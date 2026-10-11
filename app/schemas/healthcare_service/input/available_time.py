"""HealthcareService.availableTime — mirrors fhir-server's
app/schemas/healthcare_service/input/available_time.py field-for-field.

fhir-server types `days_of_week` against its own `HealthcareServiceDayOfWeek`
enum (app.schemas.enums on fhir-server) rather than the `LocationDayOfWeek`
Location uses — same mon..sun value set, kept as a separate Python class
there only because that's how fhir-server's own module boundaries fell.
This gateway already shares one `DayOfWeek` GraphQL/Pydantic enum across
Location and HealthcareService (see app/schemas/location/input.py's
docstring) since the wire values are identical — reused here rather than
introducing a duplicate enum with the same members."""

from datetime import time

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import DayOfWeek


class HealthcareServiceAvailableTimeInput(BaseModel):
    """HealthcareService.availableTime — times the service site is available (BackboneElement)."""

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
