"""
FHIR R4 Identifier datatype — a business identifier for a resource, scoped
by system/use rather than this server's own logical ID.

Spec: https://hl7.org/fhir/R4/datatypes.html#Identifier
"""

from pydantic import BaseModel, Field

from app.fhir.schemas.datatypes.codeable_concept import FhirCodeableConcept
from app.fhir.schemas.datatypes.period import FhirPeriod


class FhirIdentifier(BaseModel):
    use: str | None = Field(
        default=None, description="usual | official | temp | secondary | old"
    )
    type: FhirCodeableConcept | None = Field(
        default=None, description="Description of identifier"
    )
    system: str | None = Field(
        default=None, description="URI namespace of the identifier value"
    )
    value: str | None = Field(
        default=None, description="The value that is unique within the system"
    )
    period: FhirPeriod | None = Field(
        default=None, description="Time period when identifier is/was valid"
    )
    assigner: dict | None = Field(
        default=None, description="Organisation that issued the identifier"
    )
