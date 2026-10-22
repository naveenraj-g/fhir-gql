"""
Pydantic models representing the genuine FHIR R4 HealthcareService resource
shape — the canonical shape shared by every connector and by the GraphQL
boundary itself. Mirrors app.fhir.schemas.organization/location's pattern
exactly — see those modules' docstrings for the overall rationale.

Every reusable, non-primitive FHIR datatype (Coding, CodeableConcept,
Period, Identifier, ContactPoint, Reference) is imported from
app.fhir.schemas.datatypes rather than redefined here — category, type,
specialty, serviceProvisionCode, program, characteristic, communication,
and referralMethod are all plain `list[FhirCodeableConcept]`, since
FhirCodeableConcept.coding is already a real 0..* list — there is no
per-field flattening to work around here the way Organization/Location
needed historically.

`FhirAttachment`, `FhirHealthcareServiceEligibility`,
`FhirHealthcareServiceAvailableTime`, and `FhirHealthcareServiceNotAvailable`
stay local: each is HealthcareService's own anonymous BackboneElement/
datatype shape (Attachment is a general FHIR datatype, but nothing else in
this gateway has needed it yet), not reused across other resources.

`FhirHealthcareServiceInput` is the write-side counterpart, used by both
createFhirHealthcareService/updateFhirHealthcareService (see
app.gql.healthcare_service.mutations).

FHIR R4 HealthcareService resource spec:
https://hl7.org/fhir/R4/healthcareservice.html
"""

from pydantic import BaseModel, Field

from app.fhir.schemas.datatypes import (
    FhirCodeableConcept,
    FhirContactPoint,
    FhirIdentifier,
    FhirMeta,
    FhirPeriod,
    FhirReference,
)


class FhirAttachment(BaseModel):
    """HealthcareService.photo (0..1 Attachment)."""

    contentType: str | None = Field(
        default=None, description="Mime type of the content, e.g. image/png"
    )
    language: str | None = Field(
        default=None, description="Human language of the content, as a BCP-47 code"
    )
    data: str | None = Field(default=None, description="The actual data, base64-encoded")
    url: str | None = Field(
        default=None, description="A URI where the data can be found instead of inline"
    )
    size: int | None = Field(
        default=None,
        description="Number of bytes of content, measured after decoding, if applicable",
    )
    hash: str | None = Field(
        default=None, description="Base64-encoded hash (SHA-1) of the data"
    )
    title: str | None = Field(
        default=None, description="Label to display in place of the content"
    )
    creation: str | None = Field(
        default=None, description="ISO 8601 datetime the attachment was first created"
    )


class FhirHealthcareServiceEligibility(BaseModel):
    """HealthcareService.eligibility (0..* BackboneElement)."""

    code: FhirCodeableConcept | None = Field(
        default=None, description="Coding(s) specific to the eligibility"
    )
    comment: str | None = Field(
        default=None,
        description="Describes the eligibility conditions in more detail (markdown)",
    )


class FhirHealthcareServiceAvailableTime(BaseModel):
    """HealthcareService.availableTime (0..* BackboneElement)."""

    daysOfWeek: list[str] | None = Field(
        default=None, description="mon|tue|wed|thu|fri|sat|sun"
    )
    allDay: bool | None = Field(
        default=None, description="The service is available all day"
    )
    availableStartTime: str | None = Field(
        default=None, description="Opening time, ignored if allDay is true"
    )
    availableEndTime: str | None = Field(
        default=None, description="Closing time, ignored if allDay is true"
    )


class FhirHealthcareServiceNotAvailable(BaseModel):
    """HealthcareService.notAvailable (0..* BackboneElement)."""

    description: str | None = Field(
        default=None, description="Reason presented to the user explaining why time not available"
    )
    during: FhirPeriod | None = Field(
        default=None, description="Service not available during this period"
    )


class FhirHealthcareServiceResponse(BaseModel):
    resourceType: str = Field(
        default="HealthcareService",
        description="Always 'HealthcareService' — identifies the FHIR resource type",
    )
    id: str = Field(
        description="Logical FHIR resource ID (string representation of the DB primary key)"
    )
    meta: FhirMeta | None = Field(
        default=None,
        description=(
            "Infrastructure-maintained resource metadata — lastUpdated, plus "
            "org_id/created_by/updated_by/created_at as extensions (FHIR R4's "
            "Meta has no native field for those). Response-only: not part of "
            "FhirHealthcareServiceInput, since this is server-derived "
            "audit/tenant data, not something a client writes."
        ),
    )
    identifier: list[FhirIdentifier] | None = Field(
        default=None, description="External identifiers for this item"
    )
    active: bool | None = Field(
        default=None, description="Whether this healthcareservice record is in active use"
    )
    providedBy: FhirReference | None = Field(
        default=None, description="Organization that provides this service"
    )
    category: list[FhirCodeableConcept] | None = Field(
        default=None, description="Broad category of service being performed or delivered"
    )
    type: list[FhirCodeableConcept] | None = Field(
        default=None, description="Type of service that may be delivered or performed"
    )
    specialty: list[FhirCodeableConcept] | None = Field(
        default=None, description="Collection of specialties handled by the service site"
    )
    location: list[FhirReference] | None = Field(
        default=None, description="Location(s) where this service may be provided"
    )
    name: str | None = Field(
        default=None,
        description="Further description of the service as presented to a consumer while searching",
    )
    comment: str | None = Field(
        default=None, description="Any additional description of the service"
    )
    extraDetails: str | None = Field(
        default=None, description="Extra details about the service (markdown)"
    )
    photo: FhirAttachment | None = Field(
        default=None, description="Facilitates quick identification of the service"
    )
    telecom: list[FhirContactPoint] | None = Field(
        default=None, description="Contact details for the healthcare service"
    )
    coverageArea: list[FhirReference] | None = Field(
        default=None, description="Location(s) this service is available to"
    )
    serviceProvisionCode: list[FhirCodeableConcept] | None = Field(
        default=None, description="Conditions under which the service is available/offered"
    )
    eligibility: list[FhirHealthcareServiceEligibility] | None = Field(
        default=None, description="Specific eligibility requirements for using the service"
    )
    program: list[FhirCodeableConcept] | None = Field(
        default=None, description="Programs that this service is applicable to"
    )
    characteristic: list[FhirCodeableConcept] | None = Field(
        default=None, description="Collection of characteristics (attributes)"
    )
    communication: list[FhirCodeableConcept] | None = Field(
        default=None, description="Languages that people who work at/perform the service can use"
    )
    referralMethod: list[FhirCodeableConcept] | None = Field(
        default=None, description="Ways that the service accepts referrals"
    )
    appointmentRequired: bool | None = Field(
        default=None, description="Whether a prospective consumer will require an appointment"
    )
    availableTime: list[FhirHealthcareServiceAvailableTime] | None = Field(
        default=None, description="Collection of times the healthcare service is available"
    )
    notAvailable: list[FhirHealthcareServiceNotAvailable] | None = Field(
        default=None, description="Not available during this period of time due to the provided reason"
    )
    availabilityExceptions: str | None = Field(
        default=None, description="A description of site availability exceptions"
    )
    endpoint: list[FhirReference] | None = Field(
        default=None,
        description="Technical endpoints providing access to services operated for this healthcare service",
    )


class FhirHealthcareServiceBundleEntry(BaseModel):
    resource: FhirHealthcareServiceResponse = Field(
        description="The FHIR HealthcareService resource contained in this entry"
    )


class FhirHealthcareServiceBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(
        default="searchset", description="Always 'searchset' for search/list results"
    )
    total: int = Field(
        description="Total number of matching resources (before pagination)"
    )
    entry: list[FhirHealthcareServiceBundleEntry] | None = Field(
        default=None, description="Results — each entry wraps one HealthcareService resource"
    )


class FhirHealthcareServiceInput(BaseModel):
    """
    The write-side counterpart to FhirHealthcareServiceResponse — same
    genuine FHIR R4 HealthcareService shape, minus `resourceType`/`id`/
    `meta`. Used as-is for BOTH create and update — see module docstring.
    """

    identifier: list[FhirIdentifier] | None = Field(default=None)
    active: bool | None = Field(default=None)
    providedBy: FhirReference | None = Field(default=None)
    category: list[FhirCodeableConcept] | None = Field(default=None)
    type: list[FhirCodeableConcept] | None = Field(default=None)
    specialty: list[FhirCodeableConcept] | None = Field(default=None)
    location: list[FhirReference] | None = Field(default=None)
    name: str | None = Field(default=None)
    comment: str | None = Field(default=None)
    extraDetails: str | None = Field(default=None)
    photo: FhirAttachment | None = Field(default=None)
    telecom: list[FhirContactPoint] | None = Field(default=None)
    coverageArea: list[FhirReference] | None = Field(default=None)
    serviceProvisionCode: list[FhirCodeableConcept] | None = Field(default=None)
    eligibility: list[FhirHealthcareServiceEligibility] | None = Field(default=None)
    program: list[FhirCodeableConcept] | None = Field(default=None)
    characteristic: list[FhirCodeableConcept] | None = Field(default=None)
    communication: list[FhirCodeableConcept] | None = Field(default=None)
    referralMethod: list[FhirCodeableConcept] | None = Field(default=None)
    appointmentRequired: bool | None = Field(default=None)
    availableTime: list[FhirHealthcareServiceAvailableTime] | None = Field(default=None)
    notAvailable: list[FhirHealthcareServiceNotAvailable] | None = Field(default=None)
    availabilityExceptions: str | None = Field(default=None)
    endpoint: list[FhirReference] | None = Field(default=None)
