"""
Pydantic models representing the FHIR R4 HealthcareService resource shape.

These models exist ONLY for OpenAPI documentation purposes — they tell
Swagger UI what the response looks like when the client sends
`Accept: application/fhir+json`. They are never used for runtime validation
because route handlers return JSONResponse directly — same convention as
app/schemas/organization/fhir_schemas.py.

FHIR R4 HealthcareService resource spec: https://hl7.org/fhir/R4/healthcareservice.html
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class FhirCoding(BaseModel):
    system: Optional[str] = Field(default=None, description="URI of the code system")
    code: Optional[str] = Field(default=None, description="Symbol in the code system")
    display: Optional[str] = Field(
        default=None, description="Human-readable representation of the code"
    )


class FhirCodeableConcept(BaseModel):
    coding: Optional[List[FhirCoding]] = Field(
        default=None, description="Code defined by a terminology system"
    )
    text: Optional[str] = Field(
        default=None, description="Plain text representation of the concept"
    )


class FhirPeriod(BaseModel):
    start: Optional[str] = Field(
        default=None, description="ISO-8601 start of the period"
    )
    end: Optional[str] = Field(
        default=None, description="ISO-8601 end of the period (inclusive)"
    )


class FhirReference(BaseModel):
    reference: Optional[str] = Field(default=None, description="Relative URL reference")
    display: Optional[str] = Field(
        default=None, description="Human-readable text for the reference"
    )


class FhirContactPoint(BaseModel):
    system: Optional[str] = Field(
        default=None, description="phone | fax | email | pager | url | sms | other"
    )
    value: Optional[str] = Field(
        default=None, description="The actual contact point details"
    )
    use: Optional[str] = Field(
        default=None, description="home | work | temp | old | mobile"
    )
    rank: Optional[int] = Field(
        default=None, description="Preferred order — lower number = higher preference"
    )
    period: Optional[FhirPeriod] = Field(
        default=None, description="Time period when the contact was/is in use"
    )


class FhirIdentifier(BaseModel):
    use: Optional[str] = Field(
        default=None, description="usual | official | temp | secondary | old"
    )
    type: Optional[FhirCodeableConcept] = Field(
        default=None, description="Description of identifier type"
    )
    system: Optional[str] = Field(
        default=None, description="The namespace for the identifier value"
    )
    value: Optional[str] = Field(default=None, description="The value that is unique")
    period: Optional[FhirPeriod] = Field(
        default=None, description="Time period when identifier was valid"
    )
    assigner: Optional[str] = Field(
        default=None, description="Organisation that issued the identifier"
    )


class FhirAttachment(BaseModel):
    contentType: Optional[str] = Field(
        default=None, description="MIME type of the content"
    )
    language: Optional[str] = Field(
        default=None, description="BCP-47 language of the content"
    )
    data: Optional[str] = Field(default=None, description="Base64-encoded data")
    url: Optional[str] = Field(
        default=None, description="URI where the data can be found"
    )
    size: Optional[int] = Field(default=None, description="Number of bytes of content")
    hash: Optional[str] = Field(
        default=None, description="Base64-encoded SHA-1 hash of the data"
    )
    title: Optional[str] = Field(
        default=None, description="Label to display in place of the data"
    )
    creation: Optional[str] = Field(
        default=None, description="Date attachment was first created"
    )


class FhirHSAvailableTime(BaseModel):
    daysOfWeek: Optional[List[str]] = Field(
        default=None, description="mon | tue | wed | thu | fri | sat | sun"
    )
    allDay: Optional[bool] = Field(
        default=None, description="Service is available all day"
    )
    availableStartTime: Optional[str] = Field(
        default=None, description="Opening time (HH:mm:ss)"
    )
    availableEndTime: Optional[str] = Field(
        default=None, description="Closing time (HH:mm:ss)"
    )


class FhirHSNotAvailable(BaseModel):
    description: Optional[str] = Field(
        default=None, description="Reason why the service is unavailable"
    )
    during: Optional[FhirPeriod] = Field(
        default=None, description="The period during which the service is unavailable"
    )


class FhirHSEligibility(BaseModel):
    code: Optional[FhirCodeableConcept] = Field(
        default=None, description="Coded value for eligibility"
    )
    comment: Optional[str] = Field(
        default=None, description="Describes the eligibility conditions in detail"
    )


class FhirHealthcareServiceResponse(BaseModel):
    resourceType: str = Field(
        default="HealthcareService",
        description="Always 'HealthcareService' for this resource type",
    )
    id: Optional[str] = Field(
        default=None, description="Logical FHIR resource identifier"
    )
    identifier: Optional[List[FhirIdentifier]] = Field(
        default=None, description="External identifiers for this service"
    )
    active: Optional[bool] = Field(
        default=None, description="Whether this service is currently active"
    )
    providedBy: Optional[FhirReference] = Field(
        default=None, description="Organisation that provides this service"
    )
    category: Optional[List[FhirCodeableConcept]] = Field(
        default=None, description="Broad category of service"
    )
    type: Optional[List[FhirCodeableConcept]] = Field(
        default=None, description="Type of service delivered"
    )
    specialty: Optional[List[FhirCodeableConcept]] = Field(
        default=None, description="Specialties handled by the service"
    )
    location: Optional[List[FhirReference]] = Field(
        default=None, description="Location(s) where the service may be provided"
    )
    name: Optional[str] = Field(
        default=None, description="Description of service as presented to a consumer"
    )
    comment: Optional[str] = Field(
        default=None, description="Additional description of the service"
    )
    extraDetails: Optional[str] = Field(
        default=None, description="Extra details about the service"
    )
    photo: Optional[FhirAttachment] = Field(
        default=None, description="Facilitates quick identification of the service"
    )
    telecom: Optional[List[FhirContactPoint]] = Field(
        default=None, description="Contacts related to the healthcare service"
    )
    coverageArea: Optional[List[FhirReference]] = Field(
        default=None, description="Location(s) service is intended for/available to"
    )
    serviceProvisionCode: Optional[List[FhirCodeableConcept]] = Field(
        default=None, description="Conditions under which service is available"
    )
    eligibility: Optional[List[FhirHSEligibility]] = Field(
        default=None, description="Specific eligibility requirements"
    )
    program: Optional[List[FhirCodeableConcept]] = Field(
        default=None, description="Programs that this service is applicable to"
    )
    characteristic: Optional[List[FhirCodeableConcept]] = Field(
        default=None, description="Collection of characteristics (attributes)"
    )
    communication: Optional[List[FhirCodeableConcept]] = Field(
        default=None, description="The language(s) this service is offered in"
    )
    referralMethod: Optional[List[FhirCodeableConcept]] = Field(
        default=None, description="Ways that the service accepts referrals"
    )
    appointmentRequired: Optional[bool] = Field(
        default=None, description="If an appointment is required for access"
    )
    availableTime: Optional[List[FhirHSAvailableTime]] = Field(
        default=None, description="Times the service is available"
    )
    notAvailable: Optional[List[FhirHSNotAvailable]] = Field(
        default=None,
        description="Not available during this time due to provided reason",
    )
    availabilityExceptions: Optional[str] = Field(
        default=None, description="Description of availability exceptions"
    )
    endpoint: Optional[List[FhirReference]] = Field(
        default=None,
        description="Technical endpoints providing access to electronic services",
    )


class FhirBundleEntry(BaseModel):
    resource: FhirHealthcareServiceResponse = Field(
        description="The FHIR HealthcareService resource contained in this entry"
    )


class FhirBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(
        default="searchset", description="Always 'searchset' for search/list results"
    )
    total: int = Field(
        description="Total number of matching resources (before pagination)"
    )
    entry: Optional[List[FhirBundleEntry]] = Field(
        default=None,
        description="Results — each entry wraps one HealthcareService resource",
    )
