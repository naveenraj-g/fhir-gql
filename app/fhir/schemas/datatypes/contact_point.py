"""
FHIR R4 ContactPoint datatype — details for contacting an entity (phone,
email, fax, ...).

Spec: https://hl7.org/fhir/R4/datatypes.html#ContactPoint
"""

from pydantic import BaseModel, Field

from app.fhir.schemas.datatypes.period import FhirPeriod


class FhirContactPoint(BaseModel):
    system: str | None = Field(
        default=None, description="phone | fax | email | pager | url | sms | other"
    )
    value: str | None = Field(
        default=None, description="The actual contact point details"
    )
    use: str | None = Field(
        default=None, description="home | work | temp | old | mobile"
    )
    rank: int | None = Field(
        default=None, description="Preferred order — lower number = higher preference"
    )
    period: FhirPeriod | None = Field(
        default=None, description="Time period when contact point was/is in use"
    )
