"""
Pydantic models representing the genuine FHIR R4 Slot resource shape — the
canonical shape shared by every connector and by the GraphQL boundary
itself. Mirrors app.fhir.schemas.organization/location/healthcare_service/
practitioner/practitioner_role/schedule's pattern exactly — see those
modules' docstrings for the overall rationale.

Every reusable, non-primitive FHIR datatype (Coding, CodeableConcept,
Identifier, Reference) is imported from app.fhir.schemas.datatypes rather
than redefined here. Slot has no resource-specific BackboneElement of its
own, same as Schedule — `appointmentType` is a plain 0..1
FhirCodeableConcept (reused as-is, not a local type).

`FhirSlotInput` is the write-side counterpart, used by both
createFhirSlot/updateFhirSlot (see app.gql.slot.mutations).

FHIR R4 Slot resource spec: https://hl7.org/fhir/R4/slot.html
"""

from pydantic import BaseModel, Field

from app.fhir.schemas.datatypes import (
    FhirCodeableConcept,
    FhirIdentifier,
    FhirMeta,
    FhirReference,
)


class FhirSlotResponse(BaseModel):
    resourceType: str = Field(
        default="Slot",
        description="Always 'Slot' — identifies the FHIR resource type",
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
            "FhirSlotInput, since this is server-derived audit/tenant data, "
            "not something a client writes."
        ),
    )
    extension: list[dict] | None = Field(
        default=None,
        description="Resource-level FHIR extensions, as raw [{url, valueType, value}, ...] entries",
    )
    identifier: list[FhirIdentifier] | None = Field(
        default=None, description="External identifiers for this item"
    )
    serviceCategory: list[FhirCodeableConcept] | None = Field(
        default=None, description="A broad categorization of the service for this slot"
    )
    serviceType: list[FhirCodeableConcept] | None = Field(
        default=None,
        description="The type of appointments that can be booked into this slot",
    )
    specialty: list[FhirCodeableConcept] | None = Field(
        default=None,
        description="The specialty of a practitioner that would be required to perform the service requested in this slot",
    )
    appointmentType: FhirCodeableConcept | None = Field(
        default=None,
        description="The style of appointment or patient that may be booked in the slot (not service type)",
    )
    schedule: FhirReference = Field(
        description="The schedule resource that this slot defines an interval of status information"
    )
    status: str = Field(
        description="busy | free | busy-unavailable | busy-tentative | entered-in-error"
    )
    start: str = Field(description="Date/Time that the slot is to begin")
    end: str = Field(description="Date/Time that the slot is to conclude")
    overbooked: bool | None = Field(
        default=None,
        description="This slot has already been overbooked, appointments are unlikely to be accepted for this time",
    )
    comment: str | None = Field(
        default=None,
        description="Comments on the slot to describe any extended information",
    )


class FhirSlotBundleEntry(BaseModel):
    resource: FhirSlotResponse = Field(
        description="The FHIR Slot resource contained in this entry"
    )


class FhirSlotBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(
        default="searchset", description="Always 'searchset' for search/list results"
    )
    total: int = Field(
        description="Total number of matching resources (before pagination)"
    )
    entry: list[FhirSlotBundleEntry] | None = Field(
        default=None, description="Results — each entry wraps one Slot resource"
    )


class FhirSlotInput(BaseModel):
    """
    The write-side counterpart to FhirSlotResponse — same genuine FHIR R4
    Slot shape, minus `resourceType`/`id`/`meta`. Used as-is for BOTH
    create and update (see module docstring).
    """

    extension: list[dict] | None = Field(default=None)
    identifier: list[FhirIdentifier] | None = Field(default=None)
    serviceCategory: list[FhirCodeableConcept] | None = Field(default=None)
    serviceType: list[FhirCodeableConcept] | None = Field(default=None)
    specialty: list[FhirCodeableConcept] | None = Field(default=None)
    appointmentType: FhirCodeableConcept | None = Field(default=None)
    schedule: FhirReference | None = Field(default=None)
    status: str | None = Field(default=None)
    start: str | None = Field(default=None)
    end: str | None = Field(default=None)
    overbooked: bool | None = Field(default=None)
    comment: str | None = Field(default=None)
