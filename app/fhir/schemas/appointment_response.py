"""
Pydantic models representing the genuine FHIR R4 AppointmentResponse
resource shape — the canonical shape shared by every connector and by the
GraphQL boundary itself. Mirrors app.fhir.schemas.organization/.../
appointment's pattern exactly — see those modules' docstrings for the
overall rationale.

Every reusable, non-primitive FHIR datatype (Identifier, CodeableConcept,
Reference) is imported from app.fhir.schemas.datatypes rather than
redefined here. AppointmentResponse has no resource-specific
BackboneElement of its own (same as Schedule/Slot) — `participantType` is
a plain 0..* list of the shared FhirCodeableConcept, reused as-is.

`FhirAppointmentResponseInput` is the write-side counterpart, used by both
createFhirAppointmentResponse/updateFhirAppointmentResponse (see
app.gql.appointment_response.mutations).

Per apr-1 ("participantType.exists() or actor.exists()"), at least one of
`participantType`/`actor` must be supplied on create — enforced by base R4
validation downstream (the internal connector's fhir-server), not by this
schema itself.

FHIR R4 AppointmentResponse resource spec:
https://hl7.org/fhir/R4/appointmentresponse.html
"""

from pydantic import BaseModel, Field

from app.fhir.schemas.datatypes import (
    FhirCodeableConcept,
    FhirIdentifier,
    FhirMeta,
    FhirReference,
)


class FhirAppointmentResponseResponse(BaseModel):
    resourceType: str = Field(
        default="AppointmentResponse",
        description="Always 'AppointmentResponse' — identifies the FHIR resource type",
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
            "FhirAppointmentResponseInput, since this is server-derived "
            "audit/tenant data, not something a client writes."
        ),
    )
    extension: list[dict] | None = Field(
        default=None,
        description="Resource-level FHIR extensions, as raw [{url, valueType, value}, ...] entries",
    )
    identifier: list[FhirIdentifier] | None = Field(
        default=None, description="External identifiers for this item"
    )
    appointment: FhirReference = Field(
        description="The appointment that this response is replying to"
    )
    start: str | None = Field(
        default=None, description="Date/Time this response was made"
    )
    end: str | None = Field(
        default=None,
        description="This may be either the same as the appointment start, or different",
    )
    participantType: list[FhirCodeableConcept] | None = Field(
        default=None, description="Role of participant in the appointment"
    )
    actor: FhirReference | None = Field(
        default=None,
        description="Person, Location/HealthcareService or Device that this response is for",
    )
    participantStatus: str = Field(
        description="accepted | declined | tentative | needs-action"
    )
    comment: str | None = Field(
        default=None, description="Additional comments about the response"
    )


class FhirAppointmentResponseBundleEntry(BaseModel):
    resource: FhirAppointmentResponseResponse = Field(
        description="The FHIR AppointmentResponse resource contained in this entry"
    )


class FhirAppointmentResponseBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(
        default="searchset", description="Always 'searchset' for search/list results"
    )
    total: int = Field(
        description="Total number of matching resources (before pagination)"
    )
    entry: list[FhirAppointmentResponseBundleEntry] | None = Field(
        default=None, description="Results — each entry wraps one AppointmentResponse resource"
    )


class FhirAppointmentResponseInput(BaseModel):
    """
    The write-side counterpart to FhirAppointmentResponseResponse — same
    genuine FHIR R4 AppointmentResponse shape, minus
    `resourceType`/`id`/`meta`. Used as-is for BOTH create and update (see
    module docstring).
    """

    extension: list[dict] | None = Field(default=None)
    identifier: list[FhirIdentifier] | None = Field(default=None)
    appointment: FhirReference | None = Field(default=None)
    start: str | None = Field(default=None)
    end: str | None = Field(default=None)
    participantType: list[FhirCodeableConcept] | None = Field(default=None)
    actor: FhirReference | None = Field(default=None)
    participantStatus: str | None = Field(default=None)
    comment: str | None = Field(default=None)
