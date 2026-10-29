"""
Pydantic models representing the genuine FHIR R4 Observation resource
shape — the canonical shape shared by every connector and by the
GraphQL boundary itself. Mirrors app.fhir.schemas.medication_request's
pattern — see that module's docstring for the overall rationale.

Every reusable, non-primitive FHIR datatype (CodeableConcept,
Identifier, Reference, Period, Meta) is imported from
app.fhir.schemas.datatypes rather than redefined here. `FhirAnnotation`
is redefined locally (not shared) — same situation as
app.fhir.schemas.service_request's/medication_request's own copies.

Observation is the most Quantity-heavy resource built in this gateway
so far: `value[x]` (11 variants, including Quantity/Range/Ratio/
SampledData) appears BOTH on the root resource AND identically on its
own `component` (0..*), and `referenceRange` (with its own `low`/
`high`/`age` Quantity-shaped fields) ALSO appears on both root and
component. Every one of those Quantity/Range/Ratio/SampledData-shaped
fields — on root AND on component — is stored/exposed as a raw `dict`
rather than a typed nested model, for the same confirmed-live
strawberry bug documented in app.fhir.schemas.medication_request's own
docstring (nesting the same `@strawberry.experimental.pydantic.type`-
wrapped Quantity model inside another wrapped type reproduces
"Expected value of type 'FhirQuantityType' but got: <FhirQuantityType
instance>"). Unlike ServiceRequest's `quantityQuantity` (which stays
a real `FhirQuantityType` because it is that schema's ONLY nested
Quantity-shaped occurrence anywhere), Observation has many — root
`valueQuantity` plus component's own identical field plus `referenceRange.low`/
`.high`/`.age` at both levels — so, to keep every occurrence
consistent rather than typing only the handful that happen not to
collide with another, there is no local `FhirQuantityType`/
`FhirRangeType`/`FhirRatioType`/`FhirSampledDataType` anywhere in this
resource's GraphQL layer at all, matching MedicationRequest's own
final choice. `FhirCodeableConcept`/`FhirReference`/`FhirPeriod` are
unaffected and stay fully typed — CodeableConcept and Period are
reused dozens of times across this codebase's other resources with no
such issue; the bug is specific to the Quantity-based datatypes.

FHIR R4 Observation resource spec:
https://hl7.org/fhir/R4/observation.html
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
    """FHIR R4 Annotation — via Observation.note. `authorReference`/
    `authorString` are the two `author[x]` variants. Field-for-field
    identical to app.fhir.schemas.service_request.FhirAnnotation (not
    shared)."""

    authorReference: FhirReference | None = Field(default=None)
    authorString: str | None = Field(default=None)
    time: str | None = Field(default=None)
    text: str = Field(description="The annotation text (markdown)")


class FhirObservationReferenceRange(BaseModel):
    """Observation.referenceRange (0..*) — reused identically for
    Observation.component.referenceRange. `low`/`high`/`age` are raw
    dicts — see this module's own docstring for why."""

    low: dict | None = Field(default=None, description="FHIR SimpleQuantity, as a raw dict — see module docstring for why")
    high: dict | None = Field(default=None, description="FHIR SimpleQuantity, as a raw dict — see module docstring for why")
    type: FhirCodeableConcept | None = Field(default=None)
    appliesTo: list[FhirCodeableConcept] | None = Field(default=None)
    age: dict | None = Field(default=None, description="FHIR Range, as a raw dict — see module docstring for why")
    text: str | None = Field(default=None)


class FhirObservationComponent(BaseModel):
    """Observation.component (0..*). `value[x]` reuses the identical
    11-variant choice shape as the root resource's own `value[x]` —
    see this module's own docstring for why every Quantity/Range/
    Ratio/SampledData-shaped variant is a raw dict here too."""

    code: FhirCodeableConcept
    valueQuantity: dict | None = Field(default=None, description="FHIR Quantity, as a raw dict — see module docstring for why")
    valueCodeableConcept: FhirCodeableConcept | None = Field(default=None)
    valueString: str | None = Field(default=None)
    valueBoolean: bool | None = Field(default=None)
    valueInteger: int | None = Field(default=None)
    valueRange: dict | None = Field(default=None, description="FHIR Range, as a raw dict — see module docstring for why")
    valueRatio: dict | None = Field(default=None, description="FHIR Ratio {numerator, denominator}, as a raw dict — see module docstring for why")
    valueSampledData: dict | None = Field(default=None, description="FHIR SampledData, as a raw dict — see module docstring for why")
    valueTime: str | None = Field(default=None)
    valueDateTime: str | None = Field(default=None)
    valuePeriod: FhirPeriod | None = Field(default=None)
    dataAbsentReason: FhirCodeableConcept | None = Field(default=None)
    interpretation: list[FhirCodeableConcept] | None = Field(default=None)
    referenceRange: list[FhirObservationReferenceRange] | None = Field(default=None)


class FhirObservationResponse(BaseModel):
    resourceType: str = Field(default="Observation", description="Always 'Observation'")
    id: str = Field(description="Logical FHIR resource ID")
    meta: FhirMeta | None = Field(default=None)
    extension: list[dict] | None = Field(default=None)
    identifier: list[FhirIdentifier] | None = Field(default=None)
    basedOn: list[FhirReference] | None = Field(default=None)
    partOf: list[FhirReference] | None = Field(default=None)
    status: str = Field(description="registered | preliminary | final | amended | corrected | cancelled | entered-in-error | unknown")
    category: list[FhirCodeableConcept] | None = Field(default=None)
    code: FhirCodeableConcept = Field(description="What was observed (the observation 'name')")
    subject: FhirReference | None = Field(default=None)
    focus: list[FhirReference] | None = Field(default=None)
    encounter: FhirReference | None = Field(default=None)
    effectiveDateTime: str | None = Field(default=None)
    effectivePeriod: FhirPeriod | None = Field(default=None)
    effectiveTiming: dict | None = Field(default=None, description="Raw Timing BackboneElement, verbatim")
    effectiveInstant: str | None = Field(default=None)
    issued: str | None = Field(default=None)
    performer: list[FhirReference] | None = Field(default=None)
    valueQuantity: dict | None = Field(default=None, description="FHIR Quantity, as a raw dict — see module docstring for why")
    valueCodeableConcept: FhirCodeableConcept | None = Field(default=None)
    valueString: str | None = Field(default=None)
    valueBoolean: bool | None = Field(default=None)
    valueInteger: int | None = Field(default=None)
    valueRange: dict | None = Field(default=None, description="FHIR Range, as a raw dict — see module docstring for why")
    valueRatio: dict | None = Field(default=None, description="FHIR Ratio {numerator, denominator}, as a raw dict — see module docstring for why")
    valueSampledData: dict | None = Field(default=None, description="FHIR SampledData, as a raw dict — see module docstring for why")
    valueTime: str | None = Field(default=None)
    valueDateTime: str | None = Field(default=None)
    valuePeriod: FhirPeriod | None = Field(default=None)
    dataAbsentReason: FhirCodeableConcept | None = Field(default=None)
    interpretation: list[FhirCodeableConcept] | None = Field(default=None)
    note: list[FhirAnnotation] | None = Field(default=None)
    bodySite: FhirCodeableConcept | None = Field(default=None)
    method: FhirCodeableConcept | None = Field(default=None)
    specimen: FhirReference | None = Field(default=None)
    device: FhirReference | None = Field(default=None)
    referenceRange: list[FhirObservationReferenceRange] | None = Field(default=None)
    hasMember: list[FhirReference] | None = Field(default=None)
    derivedFrom: list[FhirReference] | None = Field(default=None)
    component: list[FhirObservationComponent] | None = Field(default=None)

    model_config = {"populate_by_name": True}


class FhirObservationBundleEntry(BaseModel):
    resource: FhirObservationResponse = Field(description="The FHIR Observation resource contained in this entry")


class FhirObservationBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(default="searchset", description="Always 'searchset' for search/list results")
    total: int = Field(description="Total number of matching resources (before pagination)")
    entry: list[FhirObservationBundleEntry] | None = Field(default=None)


class FhirObservationInput(BaseModel):
    """The write-side counterpart to FhirObservationResponse — same
    genuine FHIR R4 shape, minus resourceType/id/meta."""

    extension: list[dict] | None = Field(default=None)
    identifier: list[FhirIdentifier] | None = Field(default=None)
    basedOn: list[FhirReference] | None = Field(default=None)
    partOf: list[FhirReference] | None = Field(default=None)
    status: str | None = Field(default=None)
    category: list[FhirCodeableConcept] | None = Field(default=None)
    code: FhirCodeableConcept | None = Field(default=None)
    subject: FhirReference | None = Field(default=None)
    focus: list[FhirReference] | None = Field(default=None)
    encounter: FhirReference | None = Field(default=None)
    effectiveDateTime: str | None = Field(default=None)
    effectivePeriod: FhirPeriod | None = Field(default=None)
    effectiveTiming: dict | None = Field(default=None)
    effectiveInstant: str | None = Field(default=None)
    issued: str | None = Field(default=None)
    performer: list[FhirReference] | None = Field(default=None)
    valueQuantity: dict | None = Field(default=None)
    valueCodeableConcept: FhirCodeableConcept | None = Field(default=None)
    valueString: str | None = Field(default=None)
    valueBoolean: bool | None = Field(default=None)
    valueInteger: int | None = Field(default=None)
    valueRange: dict | None = Field(default=None)
    valueRatio: dict | None = Field(default=None)
    valueSampledData: dict | None = Field(default=None)
    valueTime: str | None = Field(default=None)
    valueDateTime: str | None = Field(default=None)
    valuePeriod: FhirPeriod | None = Field(default=None)
    dataAbsentReason: FhirCodeableConcept | None = Field(default=None)
    interpretation: list[FhirCodeableConcept] | None = Field(default=None)
    note: list[FhirAnnotation] | None = Field(default=None)
    bodySite: FhirCodeableConcept | None = Field(default=None)
    method: FhirCodeableConcept | None = Field(default=None)
    specimen: FhirReference | None = Field(default=None)
    device: FhirReference | None = Field(default=None)
    referenceRange: list[FhirObservationReferenceRange] | None = Field(default=None)
    hasMember: list[FhirReference] | None = Field(default=None)
    derivedFrom: list[FhirReference] | None = Field(default=None)
    component: list[FhirObservationComponent] | None = Field(default=None)

    model_config = {"populate_by_name": True}
