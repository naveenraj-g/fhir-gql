"""
FHIR R4 schema models for Practitioner resources — used only for OpenAPI documentation.

These models are NOT used for runtime validation. The middleware returns a
JSONResponse constructed directly from the fhir-server's response — these
models only document the FHIR R4 shape in Swagger UI.

Reference: https://hl7.org/fhir/R4/practitioner.html
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


class FhirContactPoint(BaseModel):
    system: Optional[str] = Field(default=None, description="phone | fax | email | pager | url | sms | other")
    value: Optional[str] = Field(default=None, description="The actual contact point details")
    use: Optional[str] = Field(default=None, description="home | work | temp | old | mobile")
    rank: Optional[int] = Field(default=None, description="Preferred order — lower number = higher preference")
    period: Optional[FhirPeriod] = Field(default=None, description="Time period when contact was/is in use")


class FhirHumanName(BaseModel):
    use: Optional[str] = Field(default=None, description="usual | official | temp | nickname | anonymous | old | maiden")
    text: Optional[str] = Field(default=None, description="Text representation of the full name")
    family: Optional[str] = Field(default=None, description="Family name (surname)")
    given: Optional[List[str]] = Field(default=None, description="Given names (including middle names)")
    prefix: Optional[List[str]] = Field(default=None, description="Parts that come before the name (titles)")
    suffix: Optional[List[str]] = Field(default=None, description="Parts that come after the name (qualifications)")
    period: Optional[FhirPeriod] = Field(default=None, description="Time period when name was/is in use")


class FhirAddress(BaseModel):
    use: Optional[str] = Field(default=None, description="home | work | temp | old | billing")
    type: Optional[str] = Field(default=None, description="postal | physical | both")
    text: Optional[str] = Field(default=None, description="Text representation of the address")
    line: Optional[List[str]] = Field(default=None, description="Street name, number, direction, etc.")
    city: Optional[str] = Field(default=None, description="Name of city, town, village, etc.")
    district: Optional[str] = Field(default=None, description="District name (county, etc.)")
    state: Optional[str] = Field(default=None, description="Sub-unit of country (state, province)")
    postalCode: Optional[str] = Field(default=None, description="Postal code for area")
    country: Optional[str] = Field(default=None, description="Country (ISO 3166 code preferred)")
    period: Optional[FhirPeriod] = Field(default=None, description="Time period when address was/is in use")


class FhirAttachment(BaseModel):
    contentType: Optional[str] = Field(default=None, description="MIME type of the content")
    language: Optional[str] = Field(default=None, description="BCP-47 language of the content")
    data: Optional[str] = Field(default=None, description="Base64-encoded data")
    url: Optional[str] = Field(default=None, description="URI where the data can be found")
    size: Optional[int] = Field(default=None, description="Number of bytes of content")
    hash: Optional[str] = Field(default=None, description="Base64-encoded SHA-1 hash of the data")
    title: Optional[str] = Field(default=None, description="Label to display in place of the data")
    creation: Optional[str] = Field(default=None, description="Date attachment was first created")


class FhirReference(BaseModel):
    reference: Optional[str] = Field(default=None, description="Relative URL reference (e.g. 'Organization/1')")
    display: Optional[str] = Field(default=None, description="Human-readable text for the reference")


class FhirQualification(BaseModel):
    identifier: Optional[List[FhirIdentifier]] = Field(default=None, description="Identifiers for this qualification (e.g. license number)")
    code: Optional[FhirCodeableConcept] = Field(default=None, description="Coded qualification type (e.g. MD, RN, PharmD)")
    status: Optional[FhirCodeableConcept] = Field(default=None, description="Status of the qualification")
    period: Optional[FhirPeriod] = Field(default=None, description="Period during which the qualification is valid")
    issuer: Optional[FhirReference] = Field(default=None, description="Organisation that issued the qualification")


class FhirCommunication(BaseModel):
    language: Optional[FhirCodeableConcept] = Field(default=None, description="Language as a CodeableConcept (BCP-47)")
    preferred: Optional[bool] = Field(default=None, description="True if this is the preferred communication language")


class FhirPractitionerResponse(BaseModel):
    resourceType: str = Field(default="Practitioner", description="Always 'Practitioner' for this resource type")
    id: Optional[str] = Field(default=None, description="Logical FHIR resource identifier")
    active: Optional[bool] = Field(default=None, description="Whether this practitioner's record is in active use")
    gender: Optional[str] = Field(default=None, description="Administrative gender: male | female | other | unknown")
    birthDate: Optional[str] = Field(default=None, description="Date of birth (ISO 8601)")
    deceasedBoolean: Optional[bool] = Field(default=None, description="Indicates if the practitioner is deceased")
    deceasedDateTime: Optional[str] = Field(default=None, description="Date/time of death (ISO 8601)")
    identifier: Optional[List[FhirIdentifier]] = Field(default=None, description="Identifiers for this practitioner")
    name: Optional[List[FhirHumanName]] = Field(default=None, description="The name(s) associated with the practitioner")
    telecom: Optional[List[FhirContactPoint]] = Field(default=None, description="Contact details (applying to all roles)")
    address: Optional[List[FhirAddress]] = Field(default=None, description="Address(es) not role specific")
    photo: Optional[List[FhirAttachment]] = Field(default=None, description="Image(s) of the practitioner")
    qualification: Optional[List[FhirQualification]] = Field(default=None, description="Certifications, licenses, training")
    communication: Optional[List[FhirCommunication]] = Field(default=None, description="Languages used in patient communication")


class FhirBundleEntry(BaseModel):
    resource: FhirPractitionerResponse = Field(description="The FHIR Practitioner resource contained in this entry")


class FhirBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(default="searchset", description="Always 'searchset' for search/list results")
    total: int = Field(description="Total number of matching resources (before pagination)")
    entry: Optional[List[FhirBundleEntry]] = Field(default=None, description="Results — each entry wraps one Practitioner resource")
