"""
FHIR R4 CodeableConcept datatype — a value that may be coded by one or more
terminology systems, with an optional plain-text representation.

Spec: https://hl7.org/fhir/R4/datatypes.html#CodeableConcept
"""

from pydantic import BaseModel, Field

from app.fhir.schemas.datatypes.coding import FhirCoding


class FhirCodeableConcept(BaseModel):
    coding: list[FhirCoding] | None = Field(
        default=None, description="Code defined by a terminology system"
    )
    text: str | None = Field(
        default=None, description="Plain text representation of the concept"
    )
