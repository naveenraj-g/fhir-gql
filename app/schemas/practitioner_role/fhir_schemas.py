"""
Pydantic models representing the FHIR R4 PractitionerRole resource shape.

These models exist ONLY for OpenAPI documentation purposes — they tell
Swagger UI what the response looks like when the client sends
`Accept: application/fhir+json`. They are never used for runtime validation.

Note: the availability grouping (FhirPRAvailability containing availableTime
and notAvailableTime arrays) is an R5-style extension used in this
implementation, ported as-is from the sibling project.

Reference: https://hl7.org/fhir/R4/practitionerrole.html
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
    reference: Optional[str] = Field(default=None, description="Relative or absolute URL of the referenced resource")
    display: Optional[str] = Field(default=None, description="Human-readable text for the reference")


class FhirPRContactName(BaseModel):
    use: Optional[str] = Field(default=None, description="usual | official | temp | nickname | anonymous | old | maiden")
    text: Optional[str] = Field(default=None, description="Full name as display string")
    family: Optional[str] = Field(default=None, description="Family name (surname)")
    given: Optional[List[str]] = Field(default=None, description="Given names (first/middle)")
    prefix: Optional[List[str]] = Field(default=None, description="Name prefixes (titles)")
    suffix: Optional[List[str]] = Field(default=None, description="Name suffixes")
    period: Optional[FhirPeriod] = Field(default=None, description="Time period when name was/is in use")


class FhirPRContactTelecom(BaseModel):
    system: Optional[str] = Field(default=None, description="phone | fax | email | pager | url | sms | other")
    value: Optional[str] = Field(default=None, description="The actual contact point details")
    use: Optional[str] = Field(default=None, description="home | work | temp | old | mobile")
    rank: Optional[int] = Field(default=None, description="Preferred order (1 = highest)")
    period: Optional[FhirPeriod] = Field(default=None, description="Time period when contact was/is in use")


class FhirPRContact(BaseModel):
    purpose: Optional[FhirCodeableConcept] = Field(default=None, description="The type of contact (e.g. ADMIN, BILL, PATINF)")
    name: Optional[List[FhirPRContactName]] = Field(default=None, description="Name(s) of the contact person")
    telecom: Optional[List[FhirPRContactTelecom]] = Field(default=None, description="Contact details for this contact")
    address: Optional[dict] = Field(default=None, description="Address for this contact (FHIR Address datatype)")
    organization: Optional[FhirReference] = Field(default=None, description="Organisation associated with this contact")
    period: Optional[FhirPeriod] = Field(default=None, description="Validity period for this contact")


class FhirPRAvailableTime(BaseModel):
    daysOfWeek: Optional[List[str]] = Field(default=None, description="mon | tue | wed | thu | fri | sat | sun")
    allDay: Optional[bool] = Field(default=None, description="True if available all day")
    availableStartTime: Optional[str] = Field(default=None, description="Opening time (HH:mm:ss)")
    availableEndTime: Optional[str] = Field(default=None, description="Closing time (HH:mm:ss)")


class FhirPRNotAvailableTime(BaseModel):
    description: Optional[str] = Field(default=None, description="Reason for unavailability")
    during: Optional[FhirPeriod] = Field(default=None, description="Period during which unavailable")


class FhirPRAvailability(BaseModel):
    availableTime: Optional[List[FhirPRAvailableTime]] = Field(default=None, description="Times when the practitioner is available")
    notAvailableTime: Optional[List[FhirPRNotAvailableTime]] = Field(default=None, description="Times when the practitioner is not available")


class FhirPractitionerRoleResponse(BaseModel):
    resourceType: str = Field(default="PractitionerRole", description="Always 'PractitionerRole' for this resource type")
    id: Optional[str] = Field(default=None, description="Logical FHIR resource identifier")
    identifier: Optional[List[FhirIdentifier]] = Field(default=None, description="Business identifiers for this practitioner role")
    active: Optional[bool] = Field(default=None, description="Whether this practitioner role record is active")
    period: Optional[FhirPeriod] = Field(default=None, description="The period during which the practitioner is authorised to perform this role")
    practitioner: Optional[FhirReference] = Field(default=None, description="Practitioner providing services in this role")
    organization: Optional[FhirReference] = Field(default=None, description="Organisation where the practitioner performs this role")
    code: Optional[List[FhirCodeableConcept]] = Field(default=None, description="Roles which this practitioner is authorised to perform")
    specialty: Optional[List[FhirCodeableConcept]] = Field(default=None, description="Specific specialties associated with this role")
    location: Optional[List[FhirReference]] = Field(default=None, description="Location(s) where the practitioner provides this role")
    healthcareService: Optional[List[FhirReference]] = Field(default=None, description="HealthcareService(s) that the practitioner provides in this role")
    characteristic: Optional[List[FhirCodeableConcept]] = Field(default=None, description="Collection of characteristics for this role")
    communication: Optional[List[FhirCodeableConcept]] = Field(default=None, description="Languages the practitioner uses for patient communication in this role")
    contact: Optional[List[FhirPRContact]] = Field(default=None, description="Contact details for this specific role")
    availability: Optional[List[FhirPRAvailability]] = Field(default=None, description="Availability schedule — times when the practitioner is and is not available")
    availabilityExceptions: Optional[str] = Field(default=None, description="Description of availability exceptions")
    endpoint: Optional[List[FhirReference]] = Field(default=None, description="Technical endpoints providing electronic access for this role")


class FhirBundleEntry(BaseModel):
    resource: FhirPractitionerRoleResponse = Field(description="The FHIR PractitionerRole resource contained in this entry")


class FhirBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(default="searchset", description="Always 'searchset' for search/list results")
    total: int = Field(description="Total number of matching resources (before pagination)")
    entry: Optional[List[FhirBundleEntry]] = Field(default=None, description="Results — each entry wraps one PractitionerRole resource")
