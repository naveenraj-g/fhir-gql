from pydantic import Field

from ._shared import _AuditFields


class LocationHoursOfOperationResponse(_AuditFields):
    id: int = Field(..., description="Internal row ID — use for sub-resource lookups.")
    days_of_week: list[str] | None = Field(
        None,
        description="Which days of the week are available between the start and end times — mon|tue|wed|thu|fri|sat|sun.",
    )
    all_day: bool | None = Field(
        None, description="The Location is open all day (24 hours)."
    )
    opening_time: str | None = Field(
        None,
        description="Time that the Location opens, as a wall-clock time (e.g. '09:00:00').",
    )
    closing_time: str | None = Field(
        None,
        description="Time that the Location closes, as a wall-clock time (e.g. '17:30:00').",
    )
