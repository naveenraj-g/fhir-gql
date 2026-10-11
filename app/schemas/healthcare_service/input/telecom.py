"""HealthcareService.telecom — mirrors fhir-server's
app/schemas/healthcare_service/input/telecom.py field-for-field."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import ContactPointSystem, ContactPointUse


class HealthcareServiceTelecomInput(BaseModel):
    """HealthcareService.telecom — contact details for the healthcare service (ContactPoint)."""

    model_config = ConfigDict(extra="forbid")
    system: ContactPointSystem = Field(
        ...,
        description="Telecommunications form for the contact point — phone|fax|email|pager|url|sms|other.",
    )
    value: str = Field(
        ...,
        description="The actual contact point details, in a form meaningful to the designated communication system.",
    )
    use: ContactPointUse | None = Field(
        None,
        description="Identifies the purpose for the contact point — home|work|temp|old|mobile.",
    )
    rank: int | None = Field(
        None,
        ge=1,
        description="Specifies a preferred order in which to use a set of contacts. Lower values are more preferred.",
    )
    period_start: datetime | None = Field(
        None,
        description="Start of the time period when this contact point was/is in use.",
    )
    period_end: datetime | None = Field(
        None,
        description="End of the time period when this contact point was/is in use.",
    )
