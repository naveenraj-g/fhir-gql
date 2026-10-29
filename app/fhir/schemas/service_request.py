"""
Pydantic models representing the genuine FHIR R4 ServiceRequest resource
shape — the canonical shape shared by every connector and by the GraphQL
boundary itself. Mirrors app.fhir.schemas.questionnaire_response's pattern
— see that module's docstring for the overall rationale.

Every reusable, non-primitive FHIR datatype (Coding, CodeableConcept,
Identifier, Reference, Period, Attachment, Meta) is imported from
app.fhir.schemas.datatypes rather than redefined here. `FhirQuantity`/
`FhirRatio`/`FhirAnnotation` are defined locally — this codebase's first
use of Ratio and Annotation, same situation as
app.fhir.schemas.questionnaire_response.FhirQuantity (no shared Quantity
type yet).

`occurrenceTiming` AND `quantityRatio` are both stored/exposed as a raw
`dict` rather than a typed nested model, for two different reasons:
`occurrenceTiming`'s Timing datatype is NOT flattened at all, mirroring
fhir-server's own deliberate scope decision (see fhir-server's
ServiceRequestModel docstring) — Timing is FHIR's most structurally
complex datatype and is rarely populated in practice. `quantityRatio`
DOES have a real `FhirRatio` Pydantic model defined below (documenting
the {numerator, denominator} shape), but the field itself is typed
`dict`, not `FhirRatio` — nesting a second
`@strawberry.experimental.pydantic.type`-wrapped model (`FhirQuantityType`)
inside another one (`FhirRatio`'s own numerator/denominator) hit a
confirmed-live strawberry bug on the GraphQL side (see
app.gql.service_request.types.response's module docstring), so the
GraphQL-boundary type was changed to raw JSON, and this Pydantic field
was changed to match it rather than silently diverging from what the
GraphQL schema actually serves.

FHIR R4 ServiceRequest resource spec:
https://hl7.org/fhir/R4/servicerequest.html
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.fhir.schemas.datatypes import (
    FhirAttachment,
    FhirCodeableConcept,
    FhirIdentifier,
    FhirMeta,
    FhirPeriod,
    FhirReference,
)


class FhirQuantity(BaseModel):
    """FHIR R4 Quantity — a local, duplicate definition (not shared) same
    as app.fhir.schemas.questionnaire_response.FhirQuantity."""

    value: float | None = Field(default=None, description="Numerical value")
    comparator: str | None = Field(default=None, description="< | <= | >= | > — how to understand the value")
    unit: str | None = Field(default=None, description="Unit representation")
    system: str | None = Field(default=None, description="System that defines the coded unit form")
    code: str | None = Field(default=None, description="Coded form of the unit")


class FhirRatio(BaseModel):
    """FHIR R4 Ratio — this gateway's first use, via
    ServiceRequest.quantityRatio. Not actually used as the field's own
    type below (see FhirServiceRequestResponse/Input's `quantityRatio`
    docstring) — kept only as documentation of the shape."""

    numerator: FhirQuantity | None = Field(default=None)
    denominator: FhirQuantity | None = Field(default=None)


class FhirAnnotation(BaseModel):
    """FHIR R4 Annotation — this gateway's first use, via
    ServiceRequest.note. `authorReference`/`authorString` are the two
    `author[x]` variants."""

    authorReference: FhirReference | None = Field(default=None)
    authorString: str | None = Field(default=None)
    time: str | None = Field(default=None)
    text: str = Field(description="The annotation text (markdown)")


class FhirServiceRequestResponse(BaseModel):
    resourceType: str = Field(default="ServiceRequest", description="Always 'ServiceRequest'")
    id: str = Field(description="Logical FHIR resource ID")
    meta: FhirMeta | None = Field(default=None)
    extension: list[dict] | None = Field(default=None)
    identifier: list[FhirIdentifier] | None = Field(default=None)
    instantiatesCanonical: list[str] | None = Field(default=None)
    instantiatesUri: list[str] | None = Field(default=None)
    basedOn: list[FhirReference] | None = Field(default=None)
    replaces: list[FhirReference] | None = Field(default=None)
    requisition: FhirIdentifier | None = Field(default=None)
    status: str = Field(description="draft | active | on-hold | revoked | completed | entered-in-error | unknown")
    intent: str = Field(description="proposal | plan | directive | order | original-order | reflex-order | filler-order | instance-order | option")
    category: list[FhirCodeableConcept] | None = Field(default=None)
    priority: str | None = Field(default=None, description="routine | urgent | asap | stat")
    doNotPerform: bool | None = Field(default=None)
    code: FhirCodeableConcept | None = Field(default=None)
    orderDetail: list[FhirCodeableConcept] | None = Field(default=None)
    quantityQuantity: FhirQuantity | None = Field(default=None)
    quantityRatio: dict | None = Field(
        default=None,
        description="FHIR Ratio {numerator, denominator}, as a raw dict — see FhirRatio's own docstring for why this isn't a typed nested model here.",
    )
    quantityRange: dict | None = Field(default=None)
    subject: FhirReference = Field(description="Individual/entity the service is for")
    encounter: FhirReference | None = Field(default=None)
    occurrenceDateTime: str | None = Field(default=None)
    occurrencePeriod: FhirPeriod | None = Field(default=None)
    occurrenceTiming: dict | None = Field(default=None, description="Raw Timing BackboneElement, verbatim")
    asNeededBoolean: bool | None = Field(default=None)
    asNeededCodeableConcept: FhirCodeableConcept | None = Field(default=None)
    authoredOn: str | None = Field(default=None)
    requester: FhirReference | None = Field(default=None)
    performerType: FhirCodeableConcept | None = Field(default=None)
    performer: list[FhirReference] | None = Field(default=None)
    locationCode: list[FhirCodeableConcept] | None = Field(default=None)
    locationReference: list[FhirReference] | None = Field(default=None)
    reasonCode: list[FhirCodeableConcept] | None = Field(default=None)
    reasonReference: list[FhirReference] | None = Field(default=None)
    insurance: list[FhirReference] | None = Field(default=None)
    supportingInfo: list[FhirReference] | None = Field(default=None)
    specimen: list[FhirReference] | None = Field(default=None)
    bodySite: list[FhirCodeableConcept] | None = Field(default=None)
    note: list[FhirAnnotation] | None = Field(default=None)
    patientInstruction: str | None = Field(default=None)
    relevantHistory: list[FhirReference] | None = Field(default=None)

    model_config = {"populate_by_name": True}


class FhirServiceRequestBundleEntry(BaseModel):
    resource: FhirServiceRequestResponse = Field(description="The FHIR ServiceRequest resource contained in this entry")


class FhirServiceRequestBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(default="searchset", description="Always 'searchset' for search/list results")
    total: int = Field(description="Total number of matching resources (before pagination)")
    entry: list[FhirServiceRequestBundleEntry] | None = Field(default=None)


class FhirServiceRequestInput(BaseModel):
    """The write-side counterpart to FhirServiceRequestResponse — same
    genuine FHIR R4 shape, minus resourceType/id/meta."""

    extension: list[dict] | None = Field(default=None)
    identifier: list[FhirIdentifier] | None = Field(default=None)
    instantiatesCanonical: list[str] | None = Field(default=None)
    instantiatesUri: list[str] | None = Field(default=None)
    basedOn: list[FhirReference] | None = Field(default=None)
    replaces: list[FhirReference] | None = Field(default=None)
    requisition: FhirIdentifier | None = Field(default=None)
    status: str | None = Field(default=None)
    intent: str | None = Field(default=None)
    category: list[FhirCodeableConcept] | None = Field(default=None)
    priority: str | None = Field(default=None)
    doNotPerform: bool | None = Field(default=None)
    code: FhirCodeableConcept | None = Field(default=None)
    orderDetail: list[FhirCodeableConcept] | None = Field(default=None)
    quantityQuantity: FhirQuantity | None = Field(default=None)
    quantityRatio: dict | None = Field(default=None)
    quantityRange: dict | None = Field(default=None)
    subject: FhirReference | None = Field(default=None)
    encounter: FhirReference | None = Field(default=None)
    occurrenceDateTime: str | None = Field(default=None)
    occurrencePeriod: FhirPeriod | None = Field(default=None)
    occurrenceTiming: dict | None = Field(default=None)
    asNeededBoolean: bool | None = Field(default=None)
    asNeededCodeableConcept: FhirCodeableConcept | None = Field(default=None)
    authoredOn: str | None = Field(default=None)
    requester: FhirReference | None = Field(default=None)
    performerType: FhirCodeableConcept | None = Field(default=None)
    performer: list[FhirReference] | None = Field(default=None)
    locationCode: list[FhirCodeableConcept] | None = Field(default=None)
    locationReference: list[FhirReference] | None = Field(default=None)
    reasonCode: list[FhirCodeableConcept] | None = Field(default=None)
    reasonReference: list[FhirReference] | None = Field(default=None)
    insurance: list[FhirReference] | None = Field(default=None)
    supportingInfo: list[FhirReference] | None = Field(default=None)
    specimen: list[FhirReference] | None = Field(default=None)
    bodySite: list[FhirCodeableConcept] | None = Field(default=None)
    note: list[FhirAnnotation] | None = Field(default=None)
    patientInstruction: str | None = Field(default=None)
    relevantHistory: list[FhirReference] | None = Field(default=None)

    model_config = {"populate_by_name": True}
