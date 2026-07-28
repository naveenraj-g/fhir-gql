"""
Pydantic models representing the FHIR R4 Schedule resource shape.

These models exist ONLY for OpenAPI documentation purposes — they tell
Swagger UI what the response looks like when the client sends
`Accept: application/fhir+json`. They are never used for runtime validation.

Reference: https://hl7.org/fhir/R4/schedule.html
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class FhirCoding(BaseModel):
    system: Optional[str] = Field(default=None, description="URI of the code system")
    code: Optional[str] = Field(default=None, description="Symbol in the code system")
    display: Optional[str] = Field(default=None, description="Human-readable representation of the code")


class FhirCodeableConcept(BaseModel):
    coding: Optional[List[FhirCoding]] = Field(default=None, description="Code defined by a terminology system")
    text: Optional[str] = Field(default=None, description="Plain text representation of the concept")


class FhirPeriod(BaseModel):
    start: Optional[str] = Field(default=None, description="ISO-8601 start of the period")
    end: Optional[str] = Field(default=None, description="ISO-8601 end of the period (inclusive)")


class FhirIdentifier(BaseModel):
    use: Optional[str] = Field(default=None, description="usual | official | temp | secondary | old")
    type: Optional[FhirCodeableConcept] = Field(default=None, description="Description of identifier type")
    system: Optional[str] = Field(default=None, description="The namespace for the identifier value")
    value: Optional[str] = Field(default=None, description="The value that is unique within the system")
    period: Optional[FhirPeriod] = Field(default=None, description="Time period when identifier was/is valid")
    assigner: Optional[str] = Field(default=None, description="Organisation that issued the identifier")


class FhirReference(BaseModel):
    reference: Optional[str] = Field(default=None, description="Relative URL reference (e.g. 'PractitionerRole/12')")
    display: Optional[str] = Field(default=None, description="Human-readable text for the reference")


class FhirScheduleResponse(BaseModel):
    resourceType: str = Field(default="Schedule", description="Always 'Schedule' for this resource type")
    id: Optional[str] = Field(default=None, description="Logical FHIR resource identifier")
    identifier: Optional[List[FhirIdentifier]] = Field(default=None, description="External identifiers for this Schedule")
    active: Optional[bool] = Field(default=None, description="Whether the schedule is still being used")
    serviceCategory: Optional[List[FhirCodeableConcept]] = Field(default=None, description="High-level category of the service covered by the schedule (derived from PractitionerRole/HealthcareService actors)")
    serviceType: Optional[List[FhirCodeableConcept]] = Field(default=None, description="Specific service within the broader category (derived)")
    specialty: Optional[List[FhirCodeableConcept]] = Field(default=None, description="Type of specialist required to perform the service (derived)")
    actor: Optional[List[FhirReference]] = Field(default=None, description="The resource(s) this schedule provides availability information for")
    planningHorizon: Optional[FhirPeriod] = Field(default=None, description="The period of time that the slots attached to this schedule cover")
    comment: Optional[str] = Field(default=None, description="Comments on the availability of slots")


class FhirBundleEntry(BaseModel):
    resource: FhirScheduleResponse = Field(description="The FHIR Schedule resource contained in this entry")


class FhirBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(default="searchset", description="Always 'searchset' for search/list results")
    total: int = Field(description="Total number of matching resources (before pagination)")
    entry: Optional[List[FhirBundleEntry]] = Field(default=None, description="Results — each entry wraps one Schedule resource")
