"""
Pydantic models representing the genuine FHIR R4 Schedule resource shape —
the canonical shape shared by every connector and by the GraphQL boundary
itself. Mirrors app.fhir.schemas.organization/location/healthcare_service/
practitioner/practitioner_role's pattern exactly — see those modules'
docstrings for the overall rationale.

Every reusable, non-primitive FHIR datatype (Coding, CodeableConcept,
Period, Identifier, Reference) is imported from app.fhir.schemas.datatypes
rather than redefined here. Schedule has no resource-specific
BackboneElement of its own, unlike PractitionerRole's availableTime/
notAvailable, so this module is simpler than that one.

`FhirScheduleInput` is the write-side counterpart, used by both
createFhirSchedule/updateFhirSchedule (see app.gql.schedule.mutations).

FHIR R4 Schedule resource spec: https://hl7.org/fhir/R4/schedule.html
"""

from pydantic import BaseModel, Field

from app.fhir.schemas.datatypes import (
    FhirCodeableConcept,
    FhirIdentifier,
    FhirMeta,
    FhirPeriod,
    FhirReference,
)


class FhirScheduleResponse(BaseModel):
    resourceType: str = Field(
        default="Schedule",
        description="Always 'Schedule' — identifies the FHIR resource type",
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
            "FhirScheduleInput, since this is server-derived audit/tenant "
            "data, not something a client writes."
        ),
    )
    extension: list[dict] | None = Field(
        default=None,
        description="Resource-level FHIR extensions, as raw [{url, valueType, value}, ...] entries",
    )
    identifier: list[FhirIdentifier] | None = Field(
        default=None, description="External identifiers for this item"
    )
    active: bool | None = Field(
        default=None, description="Whether this schedule record is in active use"
    )
    serviceCategory: list[FhirCodeableConcept] | None = Field(
        default=None,
        description="A high-level category of service(s) that could be provided using this schedule",
    )
    serviceType: list[FhirCodeableConcept] | None = Field(
        default=None,
        description="The specific service(s) that could be provided using this schedule",
    )
    specialty: list[FhirCodeableConcept] | None = Field(
        default=None,
        description="The specialty of a practitioner that would be required to perform the service requested in this schedule",
    )
    actor: list[FhirReference] | None = Field(
        default=None, description="The resource(s) this schedule resource is for"
    )
    planningHorizon: FhirPeriod | None = Field(
        default=None, description="The period of time covered by this schedule's slots"
    )
    comment: str | None = Field(
        default=None, description="Comments on the availability"
    )


class FhirScheduleBundleEntry(BaseModel):
    resource: FhirScheduleResponse = Field(
        description="The FHIR Schedule resource contained in this entry"
    )


class FhirScheduleBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(
        default="searchset", description="Always 'searchset' for search/list results"
    )
    total: int = Field(
        description="Total number of matching resources (before pagination)"
    )
    entry: list[FhirScheduleBundleEntry] | None = Field(
        default=None, description="Results — each entry wraps one Schedule resource"
    )


class FhirScheduleInput(BaseModel):
    """
    The write-side counterpart to FhirScheduleResponse — same genuine FHIR
    R4 Schedule shape, minus `resourceType`/`id`/`meta`. Used as-is for
    BOTH create and update (see module docstring).
    """

    extension: list[dict] | None = Field(default=None)
    identifier: list[FhirIdentifier] | None = Field(default=None)
    active: bool | None = Field(default=None)
    serviceCategory: list[FhirCodeableConcept] | None = Field(default=None)
    serviceType: list[FhirCodeableConcept] | None = Field(default=None)
    specialty: list[FhirCodeableConcept] | None = Field(default=None)
    actor: list[FhirReference] | None = Field(default=None)
    planningHorizon: FhirPeriod | None = Field(default=None)
    comment: str | None = Field(default=None)
