"""
Pydantic models representing the genuine FHIR R4 DiagnosticReport
resource shape — the canonical shape shared by every connector and by
the GraphQL boundary itself. Mirrors app.fhir.schemas.observation's
overall pattern — see that module's docstring for the general rationale
(no Quantity/Range/Ratio/SampledData-shaped fields exist on this
resource at all, so the strawberry nested-pydantic-type bug documented
there never comes up here — every field below can be a genuinely typed
nested model).

Every reusable, non-primitive FHIR datatype (CodeableConcept,
Identifier, Reference, Period, Meta, Attachment) is imported from
app.fhir.schemas.datatypes rather than redefined here.

FHIR R4 DiagnosticReport resource spec:
https://hl7.org/fhir/R4/diagnosticreport.html
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


class FhirDiagnosticReportMedia(BaseModel):
    """DiagnosticReport.media (0..*) — key images associated with the
    report."""

    comment: str | None = Field(default=None)
    link: FhirReference


class FhirDiagnosticReportResponse(BaseModel):
    resourceType: str = Field(default="DiagnosticReport", description="Always 'DiagnosticReport'")
    id: str = Field(description="Logical FHIR resource ID")
    meta: FhirMeta | None = Field(default=None)
    extension: list[dict] | None = Field(default=None)
    identifier: list[FhirIdentifier] | None = Field(default=None)
    basedOn: list[FhirReference] | None = Field(default=None)
    status: str = Field(description="registered | partial | preliminary | final | amended | corrected | appended | cancelled | entered-in-error | unknown")
    category: list[FhirCodeableConcept] | None = Field(default=None)
    code: FhirCodeableConcept = Field(description="Name/code for this diagnostic report")
    subject: FhirReference | None = Field(default=None)
    encounter: FhirReference | None = Field(default=None)
    effectiveDateTime: str | None = Field(default=None)
    effectivePeriod: FhirPeriod | None = Field(default=None)
    issued: str | None = Field(default=None)
    performer: list[FhirReference] | None = Field(default=None)
    resultsInterpreter: list[FhirReference] | None = Field(default=None)
    specimen: list[FhirReference] | None = Field(default=None)
    result: list[FhirReference] | None = Field(default=None)
    imagingStudy: list[FhirReference] | None = Field(default=None)
    media: list[FhirDiagnosticReportMedia] | None = Field(default=None)
    conclusion: str | None = Field(default=None)
    conclusionCode: list[FhirCodeableConcept] | None = Field(default=None)
    presentedForm: list[FhirAttachment] | None = Field(default=None)

    model_config = {"populate_by_name": True}


class FhirDiagnosticReportBundleEntry(BaseModel):
    resource: FhirDiagnosticReportResponse = Field(description="The FHIR DiagnosticReport resource contained in this entry")


class FhirDiagnosticReportBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(default="searchset", description="Always 'searchset' for search/list results")
    total: int = Field(description="Total number of matching resources (before pagination)")
    entry: list[FhirDiagnosticReportBundleEntry] | None = Field(default=None)


class FhirDiagnosticReportInput(BaseModel):
    """The write-side counterpart to FhirDiagnosticReportResponse — same
    genuine FHIR R4 shape, minus resourceType/id/meta."""

    extension: list[dict] | None = Field(default=None)
    identifier: list[FhirIdentifier] | None = Field(default=None)
    basedOn: list[FhirReference] | None = Field(default=None)
    status: str | None = Field(default=None)
    category: list[FhirCodeableConcept] | None = Field(default=None)
    code: FhirCodeableConcept | None = Field(default=None)
    subject: FhirReference | None = Field(default=None)
    encounter: FhirReference | None = Field(default=None)
    effectiveDateTime: str | None = Field(default=None)
    effectivePeriod: FhirPeriod | None = Field(default=None)
    issued: str | None = Field(default=None)
    performer: list[FhirReference] | None = Field(default=None)
    resultsInterpreter: list[FhirReference] | None = Field(default=None)
    specimen: list[FhirReference] | None = Field(default=None)
    result: list[FhirReference] | None = Field(default=None)
    imagingStudy: list[FhirReference] | None = Field(default=None)
    media: list[FhirDiagnosticReportMedia] | None = Field(default=None)
    conclusion: str | None = Field(default=None)
    conclusionCode: list[FhirCodeableConcept] | None = Field(default=None)
    presentedForm: list[FhirAttachment] | None = Field(default=None)

    model_config = {"populate_by_name": True}
