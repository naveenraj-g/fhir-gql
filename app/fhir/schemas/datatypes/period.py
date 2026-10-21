"""
FHIR R4 Period datatype — a time range defined by start and end dates.

Spec: https://hl7.org/fhir/R4/datatypes.html#Period
"""

from pydantic import BaseModel, Field


class FhirPeriod(BaseModel):
    start: str | None = Field(default=None, description="ISO-8601 start of the period")
    end: str | None = Field(
        default=None, description="ISO-8601 end of the period (inclusive)"
    )
