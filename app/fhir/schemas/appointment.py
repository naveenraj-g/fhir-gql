"""
Pydantic models representing the genuine FHIR R4 Appointment resource shape —
the canonical shape shared by every connector and by the GraphQL boundary
itself. Mirrors app.fhir.schemas.organization/location/healthcare_service/
practitioner/practitioner_role/schedule/slot's pattern exactly — see those
modules' docstrings for the overall rationale.

Every reusable, non-primitive FHIR datatype (Coding, CodeableConcept,
Identifier, Reference, Period) is imported from app.fhir.schemas.datatypes
rather than redefined here. `participant` is Appointment's own
resource-specific BackboneElement — the first one in this repo (every
other resource modeled so far reuses only generic datatypes) — so
`FhirAppointmentParticipant` is defined locally, same file, rather than
promoted to app.fhir.schemas.datatypes (it has no meaning outside
Appointment).

`FhirAppointmentInput` is the write-side counterpart, used by both
createFhirAppointment/updateFhirAppointment (see app.gql.appointment.mutations).

FHIR R4 Appointment resource spec: https://hl7.org/fhir/R4/appointment.html
"""

from pydantic import BaseModel, Field

from app.fhir.schemas.datatypes import (
    FhirCodeableConcept,
    FhirIdentifier,
    FhirMeta,
    FhirPeriod,
    FhirReference,
)


class FhirAppointmentParticipant(BaseModel):
    """Appointment.participant (1..*) — participants involved in the
    appointment, and their role in it. Not promoted to
    app.fhir.schemas.datatypes since it has no meaning outside Appointment."""

    type: list[FhirCodeableConcept] | None = Field(
        default=None, description="Role of participant in the appointment"
    )
    actor: FhirReference | None = Field(
        default=None,
        description="Person, Location/HealthcareService or Device that is participating",
    )
    required: str | None = Field(
        default=None, description="required | optional | information-only"
    )
    status: str = Field(description="accepted | declined | tentative | needs-action")
    period: FhirPeriod | None = Field(
        default=None, description="Participation period of the actor"
    )


class FhirAppointmentResponse(BaseModel):
    resourceType: str = Field(
        default="Appointment",
        description="Always 'Appointment' — identifies the FHIR resource type",
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
            "FhirAppointmentInput, since this is server-derived audit/tenant "
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
    status: str = Field(
        description=(
            "proposed | pending | booked | arrived | fulfilled | cancelled | "
            "noshow | entered-in-error | checked-in | waitlist"
        )
    )
    cancelationReason: FhirCodeableConcept | None = Field(
        default=None, description="The coded reason for the appointment being cancelled"
    )
    serviceCategory: list[FhirCodeableConcept] | None = Field(
        default=None, description="A broad categorization of the service"
    )
    serviceType: list[FhirCodeableConcept] | None = Field(
        default=None, description="The specific service that is to be performed"
    )
    specialty: list[FhirCodeableConcept] | None = Field(
        default=None,
        description="The specialty of a practitioner required to perform the service",
    )
    appointmentType: FhirCodeableConcept | None = Field(
        default=None,
        description="The style of appointment or patient that may be booked",
    )
    reasonCode: list[FhirCodeableConcept] | None = Field(
        default=None, description="Coded reason this appointment is scheduled"
    )
    reasonReference: list[FhirReference] | None = Field(
        default=None,
        description="Reason the appointment is to take place (resource reference)",
    )
    priority: int | None = Field(
        default=None, description="The priority of the appointment"
    )
    description: str | None = Field(
        default=None, description="Shown on a subject line in a meeting request, or appointment list"
    )
    supportingInformation: list[FhirReference] | None = Field(
        default=None, description="Additional information to support the appointment"
    )
    start: str | None = Field(
        default=None, description="Date/Time that the appointment is to take place"
    )
    end: str | None = Field(
        default=None, description="Date/Time that the appointment is to conclude"
    )
    minutesDuration: int | None = Field(
        default=None, description="Number of minutes that the appointment is to take"
    )
    slot: list[FhirReference] | None = Field(
        default=None, description="The slots from the participants' schedules that will be filled"
    )
    created: str | None = Field(
        default=None, description="The date that this appointment was initially created"
    )
    comment: str | None = Field(
        default=None, description="Additional comments about the appointment"
    )
    patientInstruction: str | None = Field(
        default=None, description="Detailed information and instructions for the patient"
    )
    basedOn: list[FhirReference] | None = Field(
        default=None, description="The service request this appointment is allocated to assess"
    )
    participant: list[FhirAppointmentParticipant] = Field(
        description="Participants involved in the appointment, and their role in it"
    )
    requestedPeriod: list[FhirPeriod] | None = Field(
        default=None,
        description="Potential date/time interval(s) requested to allocate the appointment within",
    )


class FhirAppointmentBundleEntry(BaseModel):
    resource: FhirAppointmentResponse = Field(
        description="The FHIR Appointment resource contained in this entry"
    )


class FhirAppointmentBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(
        default="searchset", description="Always 'searchset' for search/list results"
    )
    total: int = Field(
        description="Total number of matching resources (before pagination)"
    )
    entry: list[FhirAppointmentBundleEntry] | None = Field(
        default=None, description="Results — each entry wraps one Appointment resource"
    )


class FhirAppointmentInput(BaseModel):
    """
    The write-side counterpart to FhirAppointmentResponse — same genuine
    FHIR R4 Appointment shape, minus `resourceType`/`id`/`meta`. Used as-is
    for BOTH create and update (see module docstring).
    """

    extension: list[dict] | None = Field(default=None)
    identifier: list[FhirIdentifier] | None = Field(default=None)
    status: str | None = Field(default=None)
    cancelationReason: FhirCodeableConcept | None = Field(default=None)
    serviceCategory: list[FhirCodeableConcept] | None = Field(default=None)
    serviceType: list[FhirCodeableConcept] | None = Field(default=None)
    specialty: list[FhirCodeableConcept] | None = Field(default=None)
    appointmentType: FhirCodeableConcept | None = Field(default=None)
    reasonCode: list[FhirCodeableConcept] | None = Field(default=None)
    reasonReference: list[FhirReference] | None = Field(default=None)
    priority: int | None = Field(default=None)
    description: str | None = Field(default=None)
    supportingInformation: list[FhirReference] | None = Field(default=None)
    start: str | None = Field(default=None)
    end: str | None = Field(default=None)
    minutesDuration: int | None = Field(default=None)
    slot: list[FhirReference] | None = Field(default=None)
    created: str | None = Field(default=None)
    comment: str | None = Field(default=None)
    patientInstruction: str | None = Field(default=None)
    basedOn: list[FhirReference] | None = Field(default=None)
    participant: list[FhirAppointmentParticipant] | None = Field(default=None)
    requestedPeriod: list[FhirPeriod] | None = Field(default=None)
