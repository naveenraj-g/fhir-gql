"""Location.hoursOfOperation — mirrors fhir-server's
app/schemas/location/input/hours_of_operation.py field-for-field."""

from datetime import time

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import DayOfWeek


class LocationHoursOfOperationInput(BaseModel):
    """Location.hoursOfOperation — what days/times during a week the location
    is generally open (BackboneElement)."""

    model_config = ConfigDict(extra="forbid")
    days_of_week: list[DayOfWeek] | None = Field(
        None,
        description="Indicates which days of the week are available between the start and end times — mon|tue|wed|thu|fri|sat|sun.",
    )
    all_day: bool | None = Field(
        None, description="The Location is open all day (24 hours)."
    )
    opening_time: time | None = Field(
        None,
        description="Time that the Location opens, as a wall-clock time with no date and no timezone (e.g. '09:00:00').",
    )
    closing_time: time | None = Field(
        None,
        description="Time that the Location closes, as a wall-clock time with no date and no timezone (e.g. '17:30:00').",
    )
