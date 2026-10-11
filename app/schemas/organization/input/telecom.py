"""Organization.telecom — mirrors fhir-server's
app/schemas/organization/input/telecom.py field-for-field."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import ContactPointSystem, ContactPointUse


class OrganizationTelecomInput(BaseModel):
    """Organization.telecom — a contact detail for the organization (ContactPoint)."""

    model_config = ConfigDict(extra="forbid")
    system: ContactPointSystem = Field(
        ...,
        description="Telecommunications form for the contact point — what communications system is required to make use of it: phone|fax|email|pager|url|sms|other.",
    )
    value: str = Field(
        ...,
        description="The actual contact point details, in a form meaningful to the designated communication system (e.g. a phone number or email address).",
    )
    use: ContactPointUse | None = Field(
        None,
        description="Identifies the purpose for the contact point — home|work|temp|old|mobile.",
    )
    rank: int | None = Field(
        None,
        ge=1,
        description="Specifies a preferred order in which to use a set of contacts. Lower values are more preferred than higher values.",
    )
    period_start: datetime | None = Field(
        None,
        description="Start of the time period when this contact point was/is in use.",
    )
    period_end: datetime | None = Field(
        None,
        description="End of the time period when this contact point was/is in use.",
    )
