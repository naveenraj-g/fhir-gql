"""
Pydantic models representing the FHIR R4 Location resource shape.

These models exist ONLY for OpenAPI documentation purposes — they tell
Swagger UI what the response looks like when the client sends
`Accept: application/fhir+json`. They are never used for runtime validation
because route handlers return JSONResponse directly — same convention as
app/schemas/organization/fhir_schemas.py.

FHIR R4 Location resource spec: https://hl7.org/fhir/R4/location.html
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
    assigner: Optional[str] = Field(
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


class FhirReference(BaseModel):
    reference: Optional[str] = Field(
        default=None, description="Relative URL reference (e.g. 'Organization/1')"
    )
    display: Optional[str] = Field(
        default=None, description="Human-readable text for the reference"
    )


class FhirPosition(BaseModel):
    longitude: float = Field(description="Longitude in WGS84 decimal degrees")
    latitude: float = Field(description="Latitude in WGS84 decimal degrees")
    altitude: Optional[float] = Field(
        default=None, description="Altitude in WGS84 decimal meters"
    )


class FhirHoursOfOperation(BaseModel):
    daysOfWeek: Optional[List[str]] = Field(
        default=None, description="mon | tue | wed | thu | fri | sat | sun"
    )
    allDay: Optional[bool] = Field(
        default=None, description="The location is open all day on the listed days"
    )
    openingTime: Optional[str] = Field(
        default=None, description="Time that the location opens (HH:mm:ss)"
    )
    closingTime: Optional[str] = Field(
        default=None, description="Time that the location closes (HH:mm:ss)"
    )


class FhirLocationResponse(BaseModel):
    resourceType: str = Field(
        default="Location",
        description="Always 'Location' — identifies the FHIR resource type",
    )
    id: str = Field(
        description="Logical FHIR resource ID (string representation of the DB primary key)"
    )
    identifier: Optional[List[FhirIdentifier]] = Field(
        default=None, description="Business identifiers for this location"
    )
    status: Optional[str] = Field(
        default=None, description="active | suspended | inactive"
    )
    operationalStatus: Optional[FhirCoding] = Field(
        default=None, description="Operational status (bed management)"
    )
    name: Optional[str] = Field(
        default=None, description="Name of the location as used by humans"
    )
    alias: Optional[List[str]] = Field(
        default=None, description="Alternate names this location is known as"
    )
    description: Optional[str] = Field(
        default=None, description="Additional details beyond name"
    )
    mode: Optional[str] = Field(default=None, description="instance | kind")
    type: Optional[List[FhirCodeableConcept]] = Field(
        default=None, description="Type of function performed at the location"
    )
    telecom: Optional[List[FhirContactPoint]] = Field(
        default=None, description="Contact details of the location"
    )
    address: Optional[FhirAddress] = Field(
        default=None, description="Physical location address"
    )
    physicalType: Optional[FhirCodeableConcept] = Field(
        default=None, description="Physical form (building, wing, room, etc.)"
    )
    position: Optional[FhirPosition] = Field(
        default=None, description="The absolute geographic location"
    )
    managingOrganization: Optional[FhirReference] = Field(
        default=None, description="Organisation responsible for provisioning and upkeep"
    )
    partOf: Optional[FhirReference] = Field(
        default=None,
        description="Another Location this is physically part of (hierarchical)",
    )
    hoursOfOperation: Optional[List[FhirHoursOfOperation]] = Field(
        default=None, description="Usual operating days/times"
    )
    availabilityExceptions: Optional[str] = Field(
        default=None, description="Description of availability exceptions"
    )
    endpoint: Optional[List[FhirReference]] = Field(
        default=None,
        description="Technical endpoints providing access to services at this location",
    )


class FhirBundleEntry(BaseModel):
    resource: FhirLocationResponse = Field(
        description="The FHIR Location resource contained in this entry"
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
        default=None, description="Results — each entry wraps one Location resource"
    )
