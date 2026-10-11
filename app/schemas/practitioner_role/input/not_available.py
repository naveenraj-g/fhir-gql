"""PractitionerRole.notAvailable — mirrors fhir-server's
app/schemas/practitioner_role/input/not_available.py field-for-field."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PractitionerRoleNotAvailableInput(BaseModel):
    """PractitionerRole.notAvailable — not available during this time due to provided reason (BackboneElement)."""

    model_config = ConfigDict(extra="forbid")
    description: str = Field(
        ...,
        description="The reason that can be presented to the user as to why this time is not available (required).",
    )
    during_start: datetime | None = Field(
        None,
        description="Start of the period of time that this role is not available.",
    )
    during_end: datetime | None = Field(
        None,
        description="End of the period of time that this role is not available.",
    )
