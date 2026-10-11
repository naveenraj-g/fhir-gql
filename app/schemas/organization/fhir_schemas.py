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


class FhirCodeableConcept(BaseModel):
    coding: list[FhirCoding] | None = Field(
        default=None, description="Code defined by a terminology system"
    )
    text: str | None = Field(
        default=None, description="Plain text representation of the concept"
    )


class FhirPeriod(BaseModel):
    start: str | None = Field(default=None, description="ISO-8601 start of the period")
    end: str | None = Field(
        default=None, description="ISO-8601 end of the period (inclusive)"
    )


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


class FhirContactPoint(BaseModel):
    system: str | None = Field(
        default=None, description="phone | fax | email | pager | url | sms | other"
    )
    value: str | None = Field(
        default=None, description="The actual contact point details"
    )
    use: str | None = Field(
        default=None, description="home | work | temp | old | mobile"
    )
    rank: int | None = Field(
        default=None, description="Preferred order — lower number = higher preference"
    )
    period: FhirPeriod | None = Field(
        default=None, description="Time period when contact point was/is in use"
    )


class FhirAddress(BaseModel):
    use: str | None = Field(
        default=None, description="home | work | temp | old | billing"
    )
    type: str | None = Field(default=None, description="postal | physical | both")
    text: str | None = Field(
        default=None, description="Text representation of the address"
    )
    line: list[str] | None = Field(
        default=None, description="Street name, number, direction, PO Box"
    )
    city: str | None = Field(
        default=None, description="Name of city, town, suburb, village"
    )
    district: str | None = Field(
        default=None, description="District name (county, parish, etc.)"
    )
    state: str | None = Field(
        default=None, description="Sub-unit of country (abbreviation)"
    )
    postalCode: str | None = Field(default=None, description="Postal code for area")
    country: str | None = Field(
        default=None, description="Country (ISO 3166 code preferred)"
    )
    period: FhirPeriod | None = Field(
        default=None, description="Time period when address was/is in use"
    )


class FhirHumanName(BaseModel):
    use: str | None = Field(
        default=None,
        description="usual | official | temp | nickname | anonymous | old | maiden",
    )
    text: str | None = Field(
        default=None, description="Text representation of the full name"
    )
    family: str | None = Field(default=None, description="Family name (surname)")
    given: list[str] | None = Field(
        default=None, description="Given names (including middle names)"
    )
    prefix: list[str] | None = Field(
        default=None, description="Parts that come before the name (titles)"
    )
    suffix: list[str] | None = Field(
        default=None, description="Parts that come after the name (qualifications)"
    )
    period: FhirPeriod | None = Field(
        default=None, description="Time period when name was/is in use"
    )


class FhirOrgContact(BaseModel):
    purpose: FhirCodeableConcept | None = Field(
        default=None, description="The type of contact (ADMIN, BILL, HR, PATINF, PRESS)"
    )
    name: FhirHumanName | None = Field(
        default=None, description="A name associated with the contact"
    )
    telecom: list[FhirContactPoint] | None = Field(
        default=None, description="Contact details for the person"
    )
    address: FhirAddress | None = Field(
        default=None, description="Visiting or postal address for the contact"
    )


class FhirReference(BaseModel):
    reference: str | None = Field(
        default=None, description="Relative URL reference (e.g. 'Endpoint/1')"
    )
    display: str | None = Field(
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
    extension: list[dict] | None = Field(
        default=None,
        description="Resource-level FHIR extensions, as raw [{url, valueType, value}, ...] entries",
    )
    active: bool | None = Field(
        default=None,
        description="Whether the organisation's record is still in active use",
    )
    name: str | None = Field(default=None, description="Name used for the organisation")
    identifier: list[FhirIdentifier] | None = Field(
        default=None, description="Identifies this organisation across multiple systems"
    )
    type: list[FhirCodeableConcept] | None = Field(
        default=None,
        description="Kind(s) of organisation (prov, dept, team, govt, ins, etc.)",
    )
    alias: list[str] | None = Field(
        default=None,
        description="A list of alternate names the organisation is known as",
    )
    telecom: list[FhirContactPoint] | None = Field(
        default=None, description="A contact detail for the organisation"
    )
    address: list[FhirAddress] | None = Field(
        default=None, description="An address for the organisation"
    )
    partOf: FhirReference | None = Field(
        default=None,
        description="The organisation of which this organisation forms a part",
    )
    contact: list[FhirOrgContact] | None = Field(
        default=None, description="Contact for the organisation for a certain purpose"
    )
    endpoint: list[FhirReference] | None = Field(
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
    entry: list[FhirBundleEntry] | None = Field(
        default=None, description="Results — each entry wraps one Organization resource"
    )
