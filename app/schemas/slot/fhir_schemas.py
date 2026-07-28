"""
Pydantic models representing the FHIR R4 Slot resource shape.

These models exist ONLY for OpenAPI documentation purposes — they tell
Swagger UI what the response looks like when the client sends
`Accept: application/fhir+json`. They are never used for runtime validation.

Reference: https://hl7.org/fhir/R4/slot.html
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


class FhirIdentifier(BaseModel):
    use: Optional[str] = Field(default=None, description="usual | official | temp | secondary | old")
    type: Optional[FhirCodeableConcept] = Field(default=None, description="Description of identifier type")
    system: Optional[str] = Field(default=None, description="The namespace for the identifier value")
    value: Optional[str] = Field(default=None, description="The value that is unique within the system")
    assigner: Optional[str] = Field(default=None, description="Organisation that issued the identifier")


class FhirReference(BaseModel):
    reference: Optional[str] = Field(default=None, description="Relative URL reference (e.g. 'Schedule/12')")
    display: Optional[str] = Field(default=None, description="Human-readable text for the reference")


class FhirSlotResponse(BaseModel):
    resourceType: str = Field(default="Slot", description="Always 'Slot' for this resource type")
    id: Optional[str] = Field(default=None, description="Logical FHIR resource identifier")
    identifier: Optional[List[FhirIdentifier]] = Field(default=None, description="External identifiers for this Slot")
    serviceCategory: Optional[List[FhirCodeableConcept]] = Field(default=None, description="Broad category of service, defaults from the parent Schedule")
    serviceType: Optional[List[FhirCodeableConcept]] = Field(default=None, description="Specific service type, defaults from the parent Schedule")
    specialty: Optional[List[FhirCodeableConcept]] = Field(default=None, description="Clinical specialty, defaults from the parent Schedule")
    appointmentType: Optional[FhirCodeableConcept] = Field(default=None, description="The style of appointment or patient this slot is expected to accommodate")
    schedule: Optional[FhirReference] = Field(default=None, description="The Schedule resource this Slot belongs to")
    status: Optional[str] = Field(default=None, description="busy | free | busy-unavailable | busy-tentative | entered-in-error")
    start: Optional[str] = Field(default=None, description="Start of the time period the slot represents (ISO 8601)")
    end: Optional[str] = Field(default=None, description="End of the time period the slot represents (ISO 8601)")
    overbooked: Optional[bool] = Field(default=None, description="True if the slot has already been overbooked")
    comment: Optional[str] = Field(default=None, description="Comments on the slot to describe any extended information")


class FhirBundleEntry(BaseModel):
    resource: FhirSlotResponse = Field(description="The FHIR Slot resource contained in this entry")


class FhirBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(default="searchset", description="Always 'searchset' for search/list results")
    total: int = Field(description="Total number of matching resources (before pagination)")
    entry: Optional[List[FhirBundleEntry]] = Field(default=None, description="Results — each entry wraps one Slot resource")
