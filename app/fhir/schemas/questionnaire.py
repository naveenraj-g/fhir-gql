"""
Pydantic models representing the genuine FHIR R4 Questionnaire resource
shape — the canonical shape shared by every connector and by the GraphQL
boundary itself. Mirrors app.fhir.schemas.encounter's pattern exactly — see
that module's docstring for the overall rationale.

Every reusable, non-primitive FHIR datatype (Coding, CodeableConcept,
Identifier, Reference, Period, Attachment) is imported from
app.fhir.schemas.datatypes rather than redefined here. `FhirQuantity`/
`FhirRange`/`FhirContactDetail`/`FhirUsageContext` are defined locally, same
file, rather than promoted to app.fhir.schemas.datatypes — Questionnaire is
their only user in this codebase so far, same situation as
app.fhir.schemas.encounter.FhirDuration.

Questionnaire.item (0..*) is RECURSIVE — item.item nests to unbounded
depth, so `FhirQuestionnaireItem` references itself and needs
`model_rebuild()` after class definition for the forward reference to
resolve. Every choice-type field (`answer[x]`, `value[x]`) is rendered as
separate, individually-optional camelCase keys (answerBoolean,
answerCoding, answerQuantity, ...) — the real FHIR R4 JSON wire shape for
a choice type — exactly mirroring fhir-server's own
app.schemas.questionnaire.response.fhir_item module.

`FhirQuestionnaireInput` is the write-side counterpart, used by both
createFhirQuestionnaire/updateFhirQuestionnaire (see
app.gql.questionnaire.mutations).

FHIR R4 Questionnaire resource spec: https://hl7.org/fhir/R4/questionnaire.html
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.fhir.schemas.datatypes import (
    FhirAttachment,
    FhirCodeableConcept,
    FhirCoding,
    FhirContactPoint,
    FhirIdentifier,
    FhirMeta,
    FhirPeriod,
    FhirReference,
)


class FhirQuantity(BaseModel):
    """FHIR R4 Quantity — Questionnaire is its only user in this codebase
    so far, same situation as app.fhir.schemas.encounter.FhirDuration."""

    value: float | None = Field(default=None, description="Numerical value")
    comparator: str | None = Field(
        default=None, description="< | <= | >= | > — how to understand the value"
    )
    unit: str | None = Field(default=None, description="Unit representation")
    system: str | None = Field(default=None, description="System that defines the coded unit form")
    code: str | None = Field(default=None, description="Coded form of the unit")


class FhirRange(BaseModel):
    """FHIR R4 Range — a set of ordered Quantities."""

    low: FhirQuantity | None = Field(default=None, description="Low limit")
    high: FhirQuantity | None = Field(default=None, description="High limit")


class FhirContactDetail(BaseModel):
    """FHIR R4 ContactDetail — https://hl7.org/fhir/R4/metadatatypes.html#ContactDetail"""

    name: str | None = Field(default=None, description="Name of an individual to contact")
    telecom: list[FhirContactPoint] | None = Field(
        default=None, description="Contact details for individual or organization"
    )


class FhirUsageContext(BaseModel):
    """FHIR R4 UsageContext — https://hl7.org/fhir/R4/metadatatypes.html#UsageContext.
    `value[x]` rendered as separate camelCase keys — exactly one is ever
    populated."""

    code: FhirCoding = Field(description="Type of context being specified")
    valueCodeableConcept: FhirCodeableConcept | None = Field(default=None)
    valueQuantity: FhirQuantity | None = Field(default=None)
    valueRange: FhirRange | None = Field(default=None)
    valueReference: FhirReference | None = Field(default=None)


class FhirQuestionnaireItemEnableWhen(BaseModel):
    """Questionnaire.item.enableWhen (0..*)."""

    question: str = Field(description="The linkId of the question whose answer this condition is based on")
    operator: str = Field(description="exists | = | != | > | < | >= | <=")
    answerBoolean: bool | None = Field(default=None)
    answerDecimal: float | None = Field(default=None)
    answerInteger: int | None = Field(default=None)
    answerDate: str | None = Field(default=None)
    answerDateTime: str | None = Field(default=None)
    answerTime: str | None = Field(default=None)
    answerString: str | None = Field(default=None)
    answerCoding: FhirCoding | None = Field(default=None)
    answerQuantity: FhirQuantity | None = Field(default=None)
    answerReference: FhirReference | None = Field(default=None)


class FhirQuestionnaireItemAnswerOption(BaseModel):
    """Questionnaire.item.answerOption (0..*)."""

    valueInteger: int | None = Field(default=None)
    valueDate: str | None = Field(default=None)
    valueTime: str | None = Field(default=None)
    valueString: str | None = Field(default=None)
    valueCoding: FhirCoding | None = Field(default=None)
    valueReference: FhirReference | None = Field(default=None)
    initialSelected: bool | None = Field(default=None, description="Whether this option is selected by default")


class FhirQuestionnaireItemInitial(BaseModel):
    """Questionnaire.item.initial (0..*)."""

    valueBoolean: bool | None = Field(default=None)
    valueDecimal: float | None = Field(default=None)
    valueInteger: int | None = Field(default=None)
    valueDate: str | None = Field(default=None)
    valueDateTime: str | None = Field(default=None)
    valueTime: str | None = Field(default=None)
    valueString: str | None = Field(default=None)
    valueUri: str | None = Field(default=None)
    valueAttachment: FhirAttachment | None = Field(default=None)
    valueCoding: FhirCoding | None = Field(default=None)
    valueQuantity: FhirQuantity | None = Field(default=None)
    valueReference: FhirReference | None = Field(default=None)


class FhirQuestionnaireItem(BaseModel):
    """Questionnaire.item (0..*, RECURSIVE — item.item nests to unbounded
    depth). Must call `model_rebuild()` after class definition so the
    `list[FhirQuestionnaireItem]` forward reference below resolves."""

    linkId: str = Field(description="Unique id for this item in this questionnaire")
    definition: str | None = Field(default=None)
    code: list[FhirCoding] | None = Field(default=None, description="Terminology code(s) for this item")
    prefix: str | None = Field(default=None, description="e.g. '1(a)'")
    text: str | None = Field(default=None)
    type: str = Field(
        description=(
            "group | display | boolean | decimal | integer | date | dateTime | time "
            "| string | text | url | choice | open-choice | attachment | reference | quantity"
        )
    )
    enableWhen: list[FhirQuestionnaireItemEnableWhen] | None = Field(default=None)
    enableBehavior: str | None = Field(default=None, description="all | any")
    required: bool | None = Field(default=None)
    repeats: bool | None = Field(default=None)
    readOnly: bool | None = Field(default=None)
    maxLength: int | None = Field(default=None)
    answerValueSet: str | None = Field(default=None)
    answerOption: list[FhirQuestionnaireItemAnswerOption] | None = Field(default=None)
    initial: list[FhirQuestionnaireItemInitial] | None = Field(default=None)
    item: list[FhirQuestionnaireItem] | None = Field(default=None, description="Nested questions/groups")


FhirQuestionnaireItem.model_rebuild()


class FhirQuestionnaireResponse(BaseModel):
    resourceType: str = Field(default="Questionnaire", description="Always 'Questionnaire'")
    id: str = Field(description="Logical FHIR resource ID (string representation of the DB primary key)")
    meta: FhirMeta | None = Field(
        default=None,
        description=(
            "Infrastructure-maintained resource metadata — lastUpdated, plus "
            "tenant_id/created_by/updated_by/created_at as extensions. "
            "Response-only."
        ),
    )
    extension: list[dict] | None = Field(default=None)
    url: str | None = Field(default=None, description="Canonical identifier for this questionnaire")
    identifier: list[FhirIdentifier] | None = Field(default=None)
    version: str | None = Field(default=None)
    name: str | None = Field(default=None)
    title: str | None = Field(default=None)
    derivedFrom: list[str] | None = Field(default=None, description="Canonical references to Questionnaire(s) this is based on")
    status: str = Field(description="draft | active | retired | unknown")
    experimental: bool | None = Field(default=None)
    subjectType: list[str] | None = Field(default=None)
    date: str | None = Field(default=None)
    publisher: str | None = Field(default=None)
    contact: list[FhirContactDetail] | None = Field(default=None)
    description: str | None = Field(default=None)
    useContext: list[FhirUsageContext] | None = Field(default=None)
    jurisdiction: list[FhirCodeableConcept] | None = Field(default=None)
    purpose: str | None = Field(default=None)
    copyright: str | None = Field(default=None)
    approvalDate: str | None = Field(default=None)
    lastReviewDate: str | None = Field(default=None)
    effectivePeriod: FhirPeriod | None = Field(default=None)
    code: list[FhirCoding] | None = Field(default=None, description="Concept representing the overall questionnaire")
    item: list[FhirQuestionnaireItem] | None = Field(default=None, description="Questions and sections")

    model_config = {"populate_by_name": True}


class FhirQuestionnaireBundleEntry(BaseModel):
    resource: FhirQuestionnaireResponse = Field(
        description="The FHIR Questionnaire resource contained in this entry"
    )


class FhirQuestionnaireBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(default="searchset", description="Always 'searchset' for search/list results")
    total: int = Field(description="Total number of matching resources (before pagination)")
    entry: list[FhirQuestionnaireBundleEntry] | None = Field(default=None)


class FhirQuestionnaireInput(BaseModel):
    """
    The write-side counterpart to FhirQuestionnaireResponse — same genuine
    FHIR R4 Questionnaire shape, minus `resourceType`/`id`/`meta`. Used
    as-is for BOTH create and update (see module docstring).
    """

    extension: list[dict] | None = Field(default=None)
    url: str | None = Field(default=None)
    identifier: list[FhirIdentifier] | None = Field(default=None)
    version: str | None = Field(default=None)
    name: str | None = Field(default=None)
    title: str | None = Field(default=None)
    derivedFrom: list[str] | None = Field(default=None)
    status: str | None = Field(default=None)
    experimental: bool | None = Field(default=None)
    subjectType: list[str] | None = Field(default=None)
    date: str | None = Field(default=None)
    publisher: str | None = Field(default=None)
    contact: list[FhirContactDetail] | None = Field(default=None)
    description: str | None = Field(default=None)
    useContext: list[FhirUsageContext] | None = Field(default=None)
    jurisdiction: list[FhirCodeableConcept] | None = Field(default=None)
    purpose: str | None = Field(default=None)
    copyright: str | None = Field(default=None)
    approvalDate: str | None = Field(default=None)
    lastReviewDate: str | None = Field(default=None)
    effectivePeriod: FhirPeriod | None = Field(default=None)
    code: list[FhirCoding] | None = Field(default=None)
    item: list[FhirQuestionnaireItem] | None = Field(default=None)

    model_config = {"populate_by_name": True}
