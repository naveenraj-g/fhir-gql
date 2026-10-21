"""
FHIR R4 HumanName datatype — a name of a human, with its parts.

Spec: https://hl7.org/fhir/R4/datatypes.html#HumanName
"""

from pydantic import BaseModel, Field

from app.fhir.schemas.datatypes.period import FhirPeriod


class FhirHumanName(BaseModel):
    use: str | None = Field(
        default=None,
        description="usual | official | temp | nickname | anonymous | old | maiden",
    )
    text: str | None = Field(
        default=None, description="Text representation of the full name"
    )
    family: str | None = Field(default=None, description="Family name (surname)")
    given: list[str] | None = Field(
        default=None, description="Given names (including middle names)"
    )
    prefix: list[str] | None = Field(
        default=None, description="Parts that come before the name (titles)"
    )
    suffix: list[str] | None = Field(
        default=None, description="Parts that come after the name (qualifications)"
    )
    period: FhirPeriod | None = Field(
        default=None, description="Time period when name was/is in use"
    )
