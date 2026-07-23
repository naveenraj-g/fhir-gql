"""
Pydantic models representing the FHIR R4 Organization resource shape.

These models exist ONLY for OpenAPI documentation purposes — they tell
Swagger UI what the response looks like when the client sends
`Accept: application/fhir+json`. They are never used for runtime validation
because route handlers return JSONResponse directly (bypassing
response_model validation by design) — same convention as
app/schemas/patient/fhir_schemas.py.

FHIR R4 Organization resource spec: https://hl7.org/fhir/R4/organization.html
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class FhirCoding(BaseModel):
    system: Optional[str] = Field(
        default=None,
        description="URI of the code system (e.g. http://terminology.hl7.org/CodeSystem/organization-type)",
    )
    code: Optional[str] = Field(
        default=None, description="Symbol in the code system (e.g. 'prov')"
    )
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


class FhirIdentifier(BaseModel):
    use: Optional[str] = Field(
        default=None, description="usual | official | temp | secondary | old"
    )
    type: Optional[FhirCodeableConcept] = Field(
        default=None, description="Description of identifier"
    )
    system: Optional[str] = Field(
        default=None, description="URI namespace of the identifier value"
    )
    value: Optional[str] = Field(
        default=None, description="The value that is unique within the system"
    )
    period: Optional[FhirPeriod] = Field(
        default=None, description="Time period when identifier is/was valid"
    )
    assigner: Optional[dict] = Field(
        default=None, description="Organisation that issued the identifier"
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
        default=None, description="Time period when contact point was/is in use"
    )


class FhirAddress(BaseModel):
    use: Optional[str] = Field(
        default=None, description="home | work | temp | old | billing"
    )
    type: Optional[str] = Field(default=None, description="postal | physical | both")
    text: Optional[str] = Field(
        default=None, description="Text representation of the address"
    )
    line: Optional[List[str]] = Field(
        default=None, description="Street name, number, direction, PO Box"
    )
    city: Optional[str] = Field(
        default=None, description="Name of city, town, suburb, village"
    )
    district: Optional[str] = Field(
        default=None, description="District name (county, parish, etc.)"
    )
    state: Optional[str] = Field(
        default=None, description="Sub-unit of country (abbreviation)"
    )
    postalCode: Optional[str] = Field(default=None, description="Postal code for area")
    country: Optional[str] = Field(
        default=None, description="Country (ISO 3166 code preferred)"
    )
    period: Optional[FhirPeriod] = Field(
        default=None, description="Time period when address was/is in use"
    )


class FhirHumanName(BaseModel):
    use: Optional[str] = Field(
        default=None,
        description="usual | official | temp | nickname | anonymous | old | maiden",
    )
    text: Optional[str] = Field(
        default=None, description="Text representation of the full name"
    )
    family: Optional[str] = Field(default=None, description="Family name (surname)")
    given: Optional[List[str]] = Field(
        default=None, description="Given names (including middle names)"
    )
    prefix: Optional[List[str]] = Field(
        default=None, description="Parts that come before the name (titles)"
    )
    suffix: Optional[List[str]] = Field(
        default=None, description="Parts that come after the name (qualifications)"
    )
    period: Optional[FhirPeriod] = Field(
        default=None, description="Time period when name was/is in use"
    )


class FhirOrgContact(BaseModel):
    purpose: Optional[FhirCodeableConcept] = Field(
        default=None, description="The type of contact (ADMIN, BILL, HR, PATINF, PRESS)"
    )
    name: Optional[FhirHumanName] = Field(
        default=None, description="A name associated with the contact"
    )
    telecom: Optional[List[FhirContactPoint]] = Field(
        default=None, description="Contact details for the person"
    )
    address: Optional[FhirAddress] = Field(
        default=None, description="Visiting or postal address for the contact"
    )


class FhirReference(BaseModel):
    reference: Optional[str] = Field(
        default=None, description="Relative URL reference (e.g. 'Endpoint/1')"
    )
    display: Optional[str] = Field(
        default=None, description="Human-readable text for the reference"
    )


class FhirOrgResponse(BaseModel):
    resourceType: str = Field(
        default="Organization",
        description="Always 'Organization' — identifies the FHIR resource type",
    )
    id: str = Field(
        description="Logical FHIR resource ID (string representation of the DB primary key)"
    )
    active: Optional[bool] = Field(
        default=None,
        description="Whether the organisation's record is still in active use",
    )
    name: Optional[str] = Field(
        default=None, description="Name used for the organisation"
    )
    identifier: Optional[List[FhirIdentifier]] = Field(
        default=None, description="Identifies this organisation across multiple systems"
    )
    type: Optional[List[FhirCodeableConcept]] = Field(
        default=None,
        description="Kind(s) of organisation (prov, dept, team, govt, ins, etc.)",
    )
    alias: Optional[List[str]] = Field(
        default=None,
        description="A list of alternate names the organisation is known as",
    )
    telecom: Optional[List[FhirContactPoint]] = Field(
        default=None, description="A contact detail for the organisation"
    )
    address: Optional[List[FhirAddress]] = Field(
        default=None, description="An address for the organisation"
    )
    partOf: Optional[FhirReference] = Field(
        default=None,
        description="The organisation of which this organisation forms a part",
    )
    contact: Optional[List[FhirOrgContact]] = Field(
        default=None, description="Contact for the organisation for a certain purpose"
    )
    endpoint: Optional[List[FhirReference]] = Field(
        default=None,
        description="Technical endpoints providing access to services operated for the organisation",
    )


class FhirBundleEntry(BaseModel):
    resource: FhirOrgResponse = Field(
        description="The FHIR Organization resource contained in this entry"
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
        default=None, description="Results — each entry wraps one Organization resource"
    )
