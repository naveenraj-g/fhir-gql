"""
Pydantic models representing the genuine FHIR R4 Encounter resource shape —
the canonical shape shared by every connector and by the GraphQL boundary
itself. Mirrors app.fhir.schemas.organization/.../appointment_response's
pattern exactly — see those modules' docstrings for the overall rationale.

Every reusable, non-primitive FHIR datatype (Coding, CodeableConcept,
Identifier, Reference, Period) is imported from app.fhir.schemas.datatypes
rather than redefined here. `FhirDuration` is defined locally, same file,
rather than promoted to app.fhir.schemas.datatypes — Encounter.length is
its only user in this codebase so far, same situation as fhir-server's own
app/schemas/encounter/response.py's local FHIRDuration.

Encounter has six of its own resource-specific BackboneElements —
statusHistory, classHistory, participant, diagnosis, hospitalization
(0..1, not a list), and location — all defined locally for the same
reason FhirAppointmentParticipant/FhirPractitionerRoleAvailableTime are:
none has meaning outside Encounter. `class`/`classHistory.class` reuse the
shared `FhirCoding` datatype directly (Encounter.class is `Coding`, not
`CodeableConcept` — the first bare top-level Coding field in this repo).

`FhirEncounterInput` is the write-side counterpart, used by both
createFhirEncounter/updateFhirEncounter (see app.gql.encounter.mutations).

FHIR R4 Encounter resource spec: https://hl7.org/fhir/R4/encounter.html
"""

from pydantic import BaseModel, Field

from app.fhir.schemas.datatypes import (
    FhirCodeableConcept,
    FhirCoding,
    FhirIdentifier,
    FhirMeta,
    FhirPeriod,
    FhirReference,
)


class FhirDuration(BaseModel):
    """Encounter.length — how long the encounter lasted. Same shape as
    Quantity; defined locally since Encounter is its only user so far."""

    value: float | None = Field(default=None, description="Numerical value")
    comparator: str | None = Field(
        default=None, description="< | <= | >= | > — how to understand the value"
    )
    unit: str | None = Field(default=None, description="Unit representation")
    system: str | None = Field(
        default=None, description="System that defines the coded unit form"
    )
    code: str | None = Field(default=None, description="Coded form of the unit")


class FhirEncounterStatusHistory(BaseModel):
    """Encounter.statusHistory (0..*) — list of past encounter statuses."""

    status: str = Field(
        description=(
            "planned | arrived | triaged | in-progress | onleave | finished "
            "| cancelled | entered-in-error | unknown"
        )
    )
    period: FhirPeriod = Field(description="The time that the episode was in the specified status")


class FhirEncounterClassHistory(BaseModel):
    """Encounter.classHistory (0..*) — list of past encounter classes."""

    class_: FhirCoding = Field(
        alias="class", description="inpatient | outpatient | ambulatory | emergency | ..."
    )
    period: FhirPeriod = Field(description="The time that the episode was in the specified class")

    model_config = {"populate_by_name": True}


class FhirEncounterParticipant(BaseModel):
    """Encounter.participant (0..*) — list of participants involved in the encounter."""

    type: list[FhirCodeableConcept] | None = Field(
        default=None, description="Role of participant in encounter"
    )
    period: FhirPeriod | None = Field(
        default=None, description="Period of time during the encounter that the participant participated"
    )
    individual: FhirReference | None = Field(
        default=None, description="Persons involved in the encounter other than the patient"
    )


class FhirEncounterDiagnosis(BaseModel):
    """Encounter.diagnosis (0..*) — the list of diagnosis relevant to this encounter."""

    condition: FhirReference = Field(
        description="The diagnosis or procedure relevant to the encounter"
    )
    use: FhirCodeableConcept | None = Field(
        default=None, description="Role that this diagnosis has within the encounter"
    )
    rank: int | None = Field(default=None, description="Ranking of the diagnosis (for each role type)")


class FhirEncounterHospitalization(BaseModel):
    """Encounter.hospitalization (0..1) — details about the admission to a healthcare service."""

    preAdmissionIdentifier: FhirIdentifier | None = Field(
        default=None, description="Pre-admission identifier"
    )
    origin: FhirReference | None = Field(
        default=None, description="The location/organization from which the patient came before admission"
    )
    admitSource: FhirCodeableConcept | None = Field(
        default=None, description="From where patient was admitted (physician referral, transfer)"
    )
    reAdmission: FhirCodeableConcept | None = Field(
        default=None, description="Whether this hospitalization is a readmission"
    )
    dietPreference: list[FhirCodeableConcept] | None = Field(
        default=None, description="Diet preferences reported by the patient"
    )
    specialCourtesy: list[FhirCodeableConcept] | None = Field(
        default=None, description="Special courtesies (VIP, board member)"
    )
    specialArrangement: list[FhirCodeableConcept] | None = Field(
        default=None, description="Wheelchair, translator, stretcher, etc."
    )
    destination: FhirReference | None = Field(
        default=None, description="Location/organization to which the patient is discharged"
    )
    dischargeDisposition: FhirCodeableConcept | None = Field(
        default=None, description="Category or kind of location after discharge"
    )


class FhirEncounterLocation(BaseModel):
    """Encounter.location (0..*) — list of locations where the patient has been."""

    location: FhirReference = Field(description="Location the encounter takes place")
    status: str | None = Field(
        default=None, description="planned | active | reserved | completed"
    )
    physicalType: FhirCodeableConcept | None = Field(
        default=None, description="The physical type of the location (usually the level in the location hierarchy)"
    )
    period: FhirPeriod | None = Field(
        default=None, description="Time period during which the patient was present at the location"
    )


class FhirEncounterResponse(BaseModel):
    resourceType: str = Field(
        default="Encounter",
        description="Always 'Encounter' — identifies the FHIR resource type",
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
            "FhirEncounterInput, since this is server-derived audit/tenant "
            "data, not something a client writes."
        ),
    )
    extension: list[dict] | None = Field(
        default=None,
        description="Resource-level FHIR extensions, as raw [{url, valueType, value}, ...] entries",
    )
    identifier: list[FhirIdentifier] | None = Field(
        default=None, description="Identifier(s) by which this encounter is known"
    )
    status: str = Field(
        description=(
            "planned | arrived | triaged | in-progress | onleave | finished "
            "| cancelled | entered-in-error | unknown"
        )
    )
    statusHistory: list[FhirEncounterStatusHistory] | None = Field(
        default=None, description="List of past encounter statuses"
    )
    class_: FhirCoding = Field(
        alias="class",
        description="Classification of patient encounter (inpatient | outpatient | ambulatory | emergency | ...)",
    )
    classHistory: list[FhirEncounterClassHistory] | None = Field(
        default=None, description="List of past encounter classes"
    )
    type: list[FhirCodeableConcept] | None = Field(
        default=None, description="Specific type of encounter (e.g. e-mail consultation, surgical day-care)"
    )
    serviceType: FhirCodeableConcept | None = Field(
        default=None, description="Specific type of service"
    )
    priority: FhirCodeableConcept | None = Field(
        default=None, description="Indicates the urgency of the encounter"
    )
    subject: FhirReference | None = Field(
        default=None, description="The patient or group present at the encounter"
    )
    episodeOfCare: list[FhirReference] | None = Field(
        default=None, description="Episode(s) of care that this encounter should be recorded against"
    )
    basedOn: list[FhirReference] | None = Field(
        default=None, description="The ServiceRequest that initiated this encounter"
    )
    participant: list[FhirEncounterParticipant] | None = Field(
        default=None, description="List of participants involved in the encounter"
    )
    appointment: list[FhirReference] | None = Field(
        default=None, description="The appointment that scheduled this encounter"
    )
    period: FhirPeriod | None = Field(
        default=None, description="The start and end time of the encounter"
    )
    length: FhirDuration | None = Field(
        default=None, description="Quantity of time the encounter lasted (less time absent)"
    )
    reasonCode: list[FhirCodeableConcept] | None = Field(
        default=None, description="Coded reason the encounter takes place"
    )
    reasonReference: list[FhirReference] | None = Field(
        default=None, description="Reason the encounter takes place (resource reference)"
    )
    diagnosis: list[FhirEncounterDiagnosis] | None = Field(
        default=None, description="The list of diagnosis relevant to this encounter"
    )
    account: list[FhirReference] | None = Field(
        default=None, description="The set of accounts that may be used for billing for this encounter"
    )
    hospitalization: FhirEncounterHospitalization | None = Field(
        default=None, description="Details about the admission to a healthcare service"
    )
    location: list[FhirEncounterLocation] | None = Field(
        default=None, description="List of locations where the patient has been"
    )
    serviceProvider: FhirReference | None = Field(
        default=None, description="The organization (facility) responsible for this encounter"
    )
    partOf: FhirReference | None = Field(
        default=None, description="Another Encounter this encounter is part of"
    )

    model_config = {"populate_by_name": True}


class FhirEncounterBundleEntry(BaseModel):
    resource: FhirEncounterResponse = Field(
        description="The FHIR Encounter resource contained in this entry"
    )


class FhirEncounterBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(
        default="searchset", description="Always 'searchset' for search/list results"
    )
    total: int = Field(
        description="Total number of matching resources (before pagination)"
    )
    entry: list[FhirEncounterBundleEntry] | None = Field(
        default=None, description="Results — each entry wraps one Encounter resource"
    )


class FhirEncounterInput(BaseModel):
    """
    The write-side counterpart to FhirEncounterResponse — same genuine
    FHIR R4 Encounter shape, minus `resourceType`/`id`/`meta`. Used as-is
    for BOTH create and update (see module docstring).
    """

    extension: list[dict] | None = Field(default=None)
    identifier: list[FhirIdentifier] | None = Field(default=None)
    status: str | None = Field(default=None)
    statusHistory: list[FhirEncounterStatusHistory] | None = Field(default=None)
    class_: FhirCoding | None = Field(default=None, alias="class")
    classHistory: list[FhirEncounterClassHistory] | None = Field(default=None)
    type: list[FhirCodeableConcept] | None = Field(default=None)
    serviceType: FhirCodeableConcept | None = Field(default=None)
    priority: FhirCodeableConcept | None = Field(default=None)
    subject: FhirReference | None = Field(default=None)
    episodeOfCare: list[FhirReference] | None = Field(default=None)
    basedOn: list[FhirReference] | None = Field(default=None)
    participant: list[FhirEncounterParticipant] | None = Field(default=None)
    appointment: list[FhirReference] | None = Field(default=None)
    period: FhirPeriod | None = Field(default=None)
    length: FhirDuration | None = Field(default=None)
    reasonCode: list[FhirCodeableConcept] | None = Field(default=None)
    reasonReference: list[FhirReference] | None = Field(default=None)
    diagnosis: list[FhirEncounterDiagnosis] | None = Field(default=None)
    account: list[FhirReference] | None = Field(default=None)
    hospitalization: FhirEncounterHospitalization | None = Field(default=None)
    location: list[FhirEncounterLocation] | None = Field(default=None)
    serviceProvider: FhirReference | None = Field(default=None)
    partOf: FhirReference | None = Field(default=None)

    model_config = {"populate_by_name": True}
