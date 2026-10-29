"""
Pydantic models representing the genuine FHIR R4 QuestionnaireResponse
resource shape — the canonical shape shared by every connector and by the
GraphQL boundary itself. Mirrors app.fhir.schemas.questionnaire's pattern
— see that module's docstring for the overall rationale.

Every reusable, non-primitive FHIR datatype (Coding, Identifier, Reference,
Period, Attachment, Meta) is imported from app.fhir.schemas.datatypes
rather than redefined here. `FhirQuantity` is defined locally — same
situation as app.fhir.schemas.questionnaire.FhirQuantity (this codebase
has no shared Quantity type yet).

QuestionnaireResponse.item (0..*) and item.answer (0..*) are MUTUALLY
RECURSIVE — an item's own children live either directly under `item.item`
or under one of its answers' `item[]` (never both, per the FHIR invariant
"Nested item can't be beneath both item and answer"). Both
`FhirQuestionnaireResponseItem` and `FhirQuestionnaireResponseAnswer`
reference each other and need `model_rebuild()` after BOTH classes are
defined for the forward references to resolve — mirrors fhir-server's own
app.fhir.mappers.questionnaire_response package, which models this same
two-table mutual recursion on the DB side.

Every choice-type field (`value[x]`) is rendered as separate,
individually-optional camelCase keys (valueBoolean, valueCoding,
valueQuantity, ...) — the real FHIR R4 JSON wire shape for a choice type
— exactly mirroring fhir-server's own
app.schemas.questionnaire_response.response.answer module.

`FhirQuestionnaireResponseInput` is the write-side counterpart, used by
both createFhirQuestionnaireResponse/updateFhirQuestionnaireResponse (see
app.gql.questionnaire_response.mutations).

FHIR R4 QuestionnaireResponse resource spec:
https://hl7.org/fhir/R4/questionnaireresponse.html
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.fhir.schemas.datatypes import (
    FhirAttachment,
    FhirCoding,
    FhirIdentifier,
    FhirMeta,
    FhirReference,
)


class FhirQuantity(BaseModel):
    """FHIR R4 Quantity — QuestionnaireResponse.item.answer.valueQuantity
    is its only user in this codebase so far, same situation as
    app.fhir.schemas.questionnaire.FhirQuantity (a separate, duplicate
    definition — not shared — same reasoning as fhir-server's own
    resource-scoped Quantity.comparator enum copies)."""

    value: float | None = Field(default=None, description="Numerical value")
    comparator: str | None = Field(
        default=None, description="< | <= | >= | > — how to understand the value"
    )
    unit: str | None = Field(default=None, description="Unit representation")
    system: str | None = Field(default=None, description="System that defines the coded unit form")
    code: str | None = Field(default=None, description="Coded form of the unit")


class FhirQuestionnaireResponseAnswer(BaseModel):
    """QuestionnaireResponse.item.answer (0..*) — mutually recursive with
    FhirQuestionnaireResponseItem's own `item` field (see module
    docstring). Must call `model_rebuild()` after both classes are defined
    (done at the bottom of this module)."""

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
    item: list["FhirQuestionnaireResponseItem"] | None = Field(
        default=None, description="Nested groups/questions under this specific answer"
    )


class FhirQuestionnaireResponseItem(BaseModel):
    """QuestionnaireResponse.item (0..*, RECURSIVE — item.item nests to
    unbounded depth, AND an item's children may instead live under one of
    its answers' item[] — see module docstring). Must call
    `model_rebuild()` after both this class and
    FhirQuestionnaireResponseAnswer are defined."""

    linkId: str = Field(description="The linkId of the item this is answering")
    definition: str | None = Field(default=None, description="ElementDefinition reference matching the linkId")
    text: str | None = Field(default=None, description="Text displayed above the group or question")
    answer: list[FhirQuestionnaireResponseAnswer] | None = Field(default=None)
    item: list["FhirQuestionnaireResponseItem"] | None = Field(
        default=None, description="Nested groups/questions beneath this one"
    )


FhirQuestionnaireResponseAnswer.model_rebuild()
FhirQuestionnaireResponseItem.model_rebuild()


class FhirQuestionnaireResponseResponse(BaseModel):
    resourceType: str = Field(default="QuestionnaireResponse", description="Always 'QuestionnaireResponse'")
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
    identifier: FhirIdentifier | None = Field(default=None, description="A business identifier for this set of answers")
    basedOn: list[FhirReference] | None = Field(default=None)
    partOf: list[FhirReference] | None = Field(default=None)
    questionnaire: str | None = Field(default=None, description="Canonical reference to the Questionnaire this is for")
    status: str = Field(description="in-progress | completed | amended | entered-in-error | stopped")
    subject: FhirReference | None = Field(default=None, description="Who/what the answers apply to")
    encounter: FhirReference | None = Field(default=None)
    authored: str | None = Field(default=None, description="Date the answers were gathered or last changed")
    author: FhirReference | None = Field(default=None, description="Person who received and recorded the answers")
    source: FhirReference | None = Field(default=None, description="The person who answered the questions about the subject")
    item: list[FhirQuestionnaireResponseItem] | None = Field(default=None)

    model_config = {"populate_by_name": True}


class FhirQuestionnaireResponseBundleEntry(BaseModel):
    resource: FhirQuestionnaireResponseResponse = Field(
        description="The FHIR QuestionnaireResponse resource contained in this entry"
    )


class FhirQuestionnaireResponseBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(default="searchset", description="Always 'searchset' for search/list results")
    total: int = Field(description="Total number of matching resources (before pagination)")
    entry: list[FhirQuestionnaireResponseBundleEntry] | None = Field(default=None)


class FhirQuestionnaireResponseInput(BaseModel):
    """
    The write-side counterpart to FhirQuestionnaireResponseResponse — same
    genuine FHIR R4 QuestionnaireResponse shape, minus
    `resourceType`/`id`/`meta`. Used as-is for BOTH create and update (see
    module docstring).
    """

    extension: list[dict] | None = Field(default=None)
    identifier: FhirIdentifier | None = Field(default=None)
    basedOn: list[FhirReference] | None = Field(default=None)
    partOf: list[FhirReference] | None = Field(default=None)
    questionnaire: str | None = Field(default=None)
    status: str | None = Field(default=None)
    subject: FhirReference | None = Field(default=None)
    encounter: FhirReference | None = Field(default=None)
    authored: str | None = Field(default=None)
    author: FhirReference | None = Field(default=None)
    source: FhirReference | None = Field(default=None)
    item: list[FhirQuestionnaireResponseItem] | None = Field(default=None)

    model_config = {"populate_by_name": True}
