"""
Pydantic models representing the genuine FHIR R4 MedicationRequest
resource shape — the canonical shape shared by every connector and by
the GraphQL boundary itself. Mirrors app.fhir.schemas.service_request's
pattern — see that module's docstring for the overall rationale.

Every reusable, non-primitive FHIR datatype (Coding, CodeableConcept,
Identifier, Reference, Period, Meta) is imported from
app.fhir.schemas.datatypes rather than redefined here. `FhirAnnotation`
is redefined locally (not shared) — same situation as
app.fhir.schemas.service_request's own copy, there being no shared
Annotation type yet.

`dosageInstruction.timing`/`.doseAndRate`/`.maxDosePerPeriod`,
`dosageInstruction.maxDosePerAdministration`/`.maxDosePerLifetime`
(each a plain SimpleQuantity), and every Quantity/Duration-shaped field
on `dispenseRequest`/`dispenseRequest.initialFill` are ALL stored/
exposed as a raw `dict` rather than a typed nested model. Timing/
doseAndRate have no precedent-worthy flattening shape in this gateway
yet; the Quantity-shaped fields hit a confirmed-live strawberry bug —
nesting the same `@strawberry.experimental.pydantic.type`-wrapped
Quantity model as two or more sibling fields within one parent wrapped
type (`FhirMedicationRequestDosage.maxDosePerAdministration`/
`.maxDosePerLifetime`; `FhirMedicationRequestDispenseRequest.quantity`/
`.dispenseInterval`/`.expectedSupplyDuration`; `FhirMedicationRequestInitialFill.quantity`/
`.duration`) reproduces the exact same "Expected value of type
'FhirQuantityType' but got: <FhirQuantityType instance>" error first
seen on ServiceRequest.quantityRatio's numerator/denominator — confirmed
live via an actual `createFhirMedicationRequest` GraphQL call, not just
inferred from the ServiceRequest precedent. Raw JSON sidesteps it
everywhere a Quantity-shaped field has a same-typed sibling.

FHIR R4 MedicationRequest resource spec:
https://hl7.org/fhir/R4/medicationrequest.html
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.fhir.schemas.datatypes import (
    FhirCodeableConcept,
    FhirIdentifier,
    FhirMeta,
    FhirPeriod,
    FhirReference,
)


class FhirAnnotation(BaseModel):
    """FHIR R4 Annotation — via MedicationRequest.note. `authorReference`/
    `authorString` are the two `author[x]` variants. Field-for-field
    identical to app.fhir.schemas.service_request.FhirAnnotation (not
    shared)."""

    authorReference: FhirReference | None = Field(default=None)
    authorString: str | None = Field(default=None)
    time: str | None = Field(default=None)
    text: str = Field(description="The annotation text (markdown)")


class FhirMedicationRequestDosage(BaseModel):
    """FHIR R4 Dosage — https://hl7.org/fhir/R4/datatypes.html#Dosage —
    this gateway's first use. `timing`/`doseAndRate`/`maxDosePerPeriod`
    are raw dicts — see this module's own docstring for why."""

    sequence: int | None = Field(default=None)
    text: str | None = Field(default=None)
    additionalInstruction: list[FhirCodeableConcept] | None = Field(default=None)
    patientInstruction: str | None = Field(default=None)
    timing: dict | None = Field(default=None, description="Raw Timing BackboneElement, verbatim")
    asNeededBoolean: bool | None = Field(default=None)
    asNeededCodeableConcept: FhirCodeableConcept | None = Field(default=None)
    site: FhirCodeableConcept | None = Field(default=None)
    route: FhirCodeableConcept | None = Field(default=None)
    method: FhirCodeableConcept | None = Field(default=None)
    doseAndRate: list[dict] | None = Field(default=None, description="Raw dose[x]/rate[x] BackboneElements, verbatim")
    maxDosePerPeriod: dict | None = Field(default=None, description="FHIR Ratio {numerator, denominator}, as a raw dict")
    maxDosePerAdministration: dict | None = Field(default=None, description="FHIR SimpleQuantity, as a raw dict — see module docstring for why")
    maxDosePerLifetime: dict | None = Field(default=None, description="FHIR SimpleQuantity, as a raw dict — see module docstring for why")


class FhirMedicationRequestInitialFill(BaseModel):
    quantity: dict | None = Field(default=None, description="FHIR SimpleQuantity, as a raw dict — see module docstring for why")
    duration: dict | None = Field(default=None, description="FHIR Duration, as a raw dict — see module docstring for why")


class FhirMedicationRequestDispenseRequest(BaseModel):
    initialFill: FhirMedicationRequestInitialFill | None = Field(default=None)
    dispenseInterval: dict | None = Field(default=None, description="FHIR Duration, as a raw dict — see module docstring for why")
    validityPeriod: FhirPeriod | None = Field(default=None)
    numberOfRepeatsAllowed: int | None = Field(default=None)
    quantity: dict | None = Field(default=None, description="FHIR SimpleQuantity, as a raw dict — see module docstring for why")
    expectedSupplyDuration: dict | None = Field(default=None, description="FHIR Duration, as a raw dict — see module docstring for why")
    performer: FhirReference | None = Field(default=None)


class FhirMedicationRequestSubstitution(BaseModel):
    allowedBoolean: bool | None = Field(default=None)
    allowedCodeableConcept: FhirCodeableConcept | None = Field(default=None)
    reason: FhirCodeableConcept | None = Field(default=None)


class FhirMedicationRequestResponse(BaseModel):
    resourceType: str = Field(default="MedicationRequest", description="Always 'MedicationRequest'")
    id: str = Field(description="Logical FHIR resource ID")
    meta: FhirMeta | None = Field(default=None)
    extension: list[dict] | None = Field(default=None)
    identifier: list[FhirIdentifier] | None = Field(default=None)
    status: str = Field(description="active | on-hold | cancelled | completed | entered-in-error | stopped | draft | unknown")
    statusReason: FhirCodeableConcept | None = Field(default=None)
    intent: str = Field(description="proposal | plan | order | original-order | reflex-order | filler-order | instance-order | option")
    category: list[FhirCodeableConcept] | None = Field(default=None)
    priority: str | None = Field(default=None, description="routine | urgent | asap | stat")
    doNotPerform: bool | None = Field(default=None)
    reportedBoolean: bool | None = Field(default=None)
    reportedReference: FhirReference | None = Field(default=None)
    medicationCodeableConcept: FhirCodeableConcept | None = Field(default=None)
    medicationReference: FhirReference | None = Field(default=None)
    subject: FhirReference = Field(description="Individual/entity the medication is for")
    encounter: FhirReference | None = Field(default=None)
    supportingInformation: list[FhirReference] | None = Field(default=None)
    authoredOn: str | None = Field(default=None)
    requester: FhirReference | None = Field(default=None)
    performer: FhirReference | None = Field(default=None)
    performerType: FhirCodeableConcept | None = Field(default=None)
    recorder: FhirReference | None = Field(default=None)
    reasonCode: list[FhirCodeableConcept] | None = Field(default=None)
    reasonReference: list[FhirReference] | None = Field(default=None)
    instantiatesCanonical: list[str] | None = Field(default=None)
    instantiatesUri: list[str] | None = Field(default=None)
    basedOn: list[FhirReference] | None = Field(default=None)
    groupIdentifier: FhirIdentifier | None = Field(default=None)
    courseOfTherapyType: FhirCodeableConcept | None = Field(default=None)
    insurance: list[FhirReference] | None = Field(default=None)
    note: list[FhirAnnotation] | None = Field(default=None)
    dosageInstruction: list[FhirMedicationRequestDosage] | None = Field(default=None)
    dispenseRequest: FhirMedicationRequestDispenseRequest | None = Field(default=None)
    substitution: FhirMedicationRequestSubstitution | None = Field(default=None)
    priorPrescription: FhirReference | None = Field(default=None)
    detectedIssue: list[FhirReference] | None = Field(default=None)
    eventHistory: list[FhirReference] | None = Field(default=None)

    model_config = {"populate_by_name": True}


class FhirMedicationRequestBundleEntry(BaseModel):
    resource: FhirMedicationRequestResponse = Field(description="The FHIR MedicationRequest resource contained in this entry")


class FhirMedicationRequestBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(default="searchset", description="Always 'searchset' for search/list results")
    total: int = Field(description="Total number of matching resources (before pagination)")
    entry: list[FhirMedicationRequestBundleEntry] | None = Field(default=None)


class FhirMedicationRequestInput(BaseModel):
    """The write-side counterpart to FhirMedicationRequestResponse — same
    genuine FHIR R4 shape, minus resourceType/id/meta."""

    extension: list[dict] | None = Field(default=None)
    identifier: list[FhirIdentifier] | None = Field(default=None)
    status: str | None = Field(default=None)
    statusReason: FhirCodeableConcept | None = Field(default=None)
    intent: str | None = Field(default=None)
    category: list[FhirCodeableConcept] | None = Field(default=None)
    priority: str | None = Field(default=None)
    doNotPerform: bool | None = Field(default=None)
    reportedBoolean: bool | None = Field(default=None)
    reportedReference: FhirReference | None = Field(default=None)
    medicationCodeableConcept: FhirCodeableConcept | None = Field(default=None)
    medicationReference: FhirReference | None = Field(default=None)
    subject: FhirReference | None = Field(default=None)
    encounter: FhirReference | None = Field(default=None)
    supportingInformation: list[FhirReference] | None = Field(default=None)
    authoredOn: str | None = Field(default=None)
    requester: FhirReference | None = Field(default=None)
    performer: FhirReference | None = Field(default=None)
    performerType: FhirCodeableConcept | None = Field(default=None)
    recorder: FhirReference | None = Field(default=None)
    reasonCode: list[FhirCodeableConcept] | None = Field(default=None)
    reasonReference: list[FhirReference] | None = Field(default=None)
    instantiatesCanonical: list[str] | None = Field(default=None)
    instantiatesUri: list[str] | None = Field(default=None)
    basedOn: list[FhirReference] | None = Field(default=None)
    groupIdentifier: FhirIdentifier | None = Field(default=None)
    courseOfTherapyType: FhirCodeableConcept | None = Field(default=None)
    insurance: list[FhirReference] | None = Field(default=None)
    note: list[FhirAnnotation] | None = Field(default=None)
    dosageInstruction: list[FhirMedicationRequestDosage] | None = Field(default=None)
    dispenseRequest: FhirMedicationRequestDispenseRequest | None = Field(default=None)
    substitution: FhirMedicationRequestSubstitution | None = Field(default=None)
    priorPrescription: FhirReference | None = Field(default=None)
    detectedIssue: list[FhirReference] | None = Field(default=None)
    eventHistory: list[FhirReference] | None = Field(default=None)

    model_config = {"populate_by_name": True}
