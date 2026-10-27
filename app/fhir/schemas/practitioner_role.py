"""
Pydantic models representing the genuine FHIR R4 PractitionerRole resource
shape — the canonical shape shared by every connector and by the GraphQL
boundary itself. Mirrors app.fhir.schemas.organization/location/
healthcare_service/practitioner's pattern exactly — see those modules'
docstrings for the overall rationale.

Every reusable, non-primitive FHIR datatype (Coding, CodeableConcept,
Period, Identifier, ContactPoint, Reference) is imported from
app.fhir.schemas.datatypes rather than redefined here.
`FhirPractitionerRoleAvailableTime`/`FhirPractitionerRoleNotAvailable` stay
local: they're PractitionerRole's own `availableTime`/`notAvailable`
BackboneElements (anonymous nested structures the R4 spec defines
specifically for this resource), not reused across other resources.

`FhirPractitionerRoleInput` is the write-side counterpart, used by both
createFhirPractitionerRole/updateFhirPractitionerRole (see
app.gql.practitioner_role.mutations).

FHIR R4 PractitionerRole resource spec:
https://hl7.org/fhir/R4/practitionerrole.html
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


class FhirPractitionerRoleAvailableTime(BaseModel):
    """PractitionerRole.availableTime (0..* BackboneElement) — times the
    practitioner is available at this location/role."""

    daysOfWeek: list[str] | None = Field(
        default=None, description="mon | tue | wed | thu | fri | sat | sun"
    )
    allDay: bool | None = Field(
        default=None,
        description="Is this always available (hence times are irrelevant)?",
    )
    availableStartTime: str | None = Field(
        default=None, description="The opening time, HH:MM:SS"
    )
    availableEndTime: str | None = Field(
        default=None, description="The closing time, HH:MM:SS"
    )


class FhirPractitionerRoleNotAvailable(BaseModel):
    """PractitionerRole.notAvailable (0..* BackboneElement) — not available
    during this period, for the given reason."""

    description: str | None = Field(
        default=None,
        description="The reason presented to the user as to why this time is not available",
    )
    during: FhirPeriod | None = Field(
        default=None, description="Service is not available during this period"
    )


class FhirPractitionerRoleResponse(BaseModel):
    resourceType: str = Field(
        default="PractitionerRole",
        description="Always 'PractitionerRole' — identifies the FHIR resource type",
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
            "FhirPractitionerRoleInput, since this is server-derived "
            "audit/tenant data, not something a client writes."
        ),
    )
    extension: list[dict] | None = Field(
        default=None,
        description="Resource-level FHIR extensions, as raw [{url, valueType, value}, ...] entries",
    )
    identifier: list[FhirIdentifier] | None = Field(
        default=None, description="Business identifiers for this role"
    )
    active: bool | None = Field(
        default=None, description="Whether this practitioner role record is in active use"
    )
    period: FhirPeriod | None = Field(
        default=None, description="The period during which this role is valid"
    )
    practitioner: FhirReference | None = Field(
        default=None, description="The practitioner who performs this role"
    )
    organization: FhirReference | None = Field(
        default=None, description="The organization this role is associated with"
    )
    code: list[FhirCodeableConcept] | None = Field(
        default=None, description="Roles which this practitioner may perform"
    )
    specialty: list[FhirCodeableConcept] | None = Field(
        default=None, description="Specific specialty of the practitioner"
    )
    location: list[FhirReference] | None = Field(
        default=None,
        description="The location(s) at which this practitioner provides care",
    )
    healthcareService: list[FhirReference] | None = Field(
        default=None,
        description=(
            "The list of healthcare services that this worker provides for "
            "this role's organization/location(s)"
        ),
    )
    telecom: list[FhirContactPoint] | None = Field(
        default=None, description="Contact details specific to the role"
    )
    availableTime: list[FhirPractitionerRoleAvailableTime] | None = Field(
        default=None,
        description="Times the practitioner is available at this location/role",
    )
    notAvailable: list[FhirPractitionerRoleNotAvailable] | None = Field(
        default=None,
        description="The practitioner is not available during this period, for the given reason",
    )
    availabilityExceptions: str | None = Field(
        default=None, description="A description of site availability exceptions"
    )
    endpoint: list[FhirReference] | None = Field(
        default=None,
        description="Technical endpoints providing access to services operated for this role",
    )


class FhirPractitionerRoleBundleEntry(BaseModel):
    resource: FhirPractitionerRoleResponse = Field(
        description="The FHIR PractitionerRole resource contained in this entry"
    )


class FhirPractitionerRoleBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(
        default="searchset", description="Always 'searchset' for search/list results"
    )
    total: int = Field(
        description="Total number of matching resources (before pagination)"
    )
    entry: list[FhirPractitionerRoleBundleEntry] | None = Field(
        default=None, description="Results — each entry wraps one PractitionerRole resource"
    )


class FhirPractitionerRoleInput(BaseModel):
    """
    The write-side counterpart to FhirPractitionerRoleResponse — same
    genuine FHIR R4 PractitionerRole shape, minus `resourceType`/`id`/`meta`.
    Used as-is for BOTH create and update (see module docstring).
    """

    extension: list[dict] | None = Field(default=None)
    identifier: list[FhirIdentifier] | None = Field(default=None)
    active: bool | None = Field(default=None)
    period: FhirPeriod | None = Field(default=None)
    practitioner: FhirReference | None = Field(default=None)
    organization: FhirReference | None = Field(default=None)
    code: list[FhirCodeableConcept] | None = Field(default=None)
    specialty: list[FhirCodeableConcept] | None = Field(default=None)
    location: list[FhirReference] | None = Field(default=None)
    healthcareService: list[FhirReference] | None = Field(default=None)
    telecom: list[FhirContactPoint] | None = Field(default=None)
    availableTime: list[FhirPractitionerRoleAvailableTime] | None = Field(default=None)
    notAvailable: list[FhirPractitionerRoleNotAvailable] | None = Field(default=None)
    availabilityExceptions: str | None = Field(default=None)
    endpoint: list[FhirReference] | None = Field(default=None)
