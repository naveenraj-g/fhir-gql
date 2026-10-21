"""
FHIR R4 Coding datatype — a representation of a defined concept using a
symbol from a code system.

Spec: https://hl7.org/fhir/R4/datatypes.html#Coding
"""

from pydantic import BaseModel, Field


class FhirCoding(BaseModel):
    system: str | None = Field(
        default=None,
        description="URI of the code system (e.g. http://terminology.hl7.org/CodeSystem/organization-type)",
    )
    code: str | None = Field(
        default=None, description="Symbol in the code system (e.g. 'prov')"
    )
    display: str | None = Field(
        default=None, description="Human-readable representation of the code"
    )
