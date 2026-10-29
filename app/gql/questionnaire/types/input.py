"""
GraphQL input types for the Questionnaire resource.

Mirrors app.gql.encounter.types.input exactly — see that module and
app.gql.organization's package docstring for the overall idea.
Declaration order matters for strawberry.experimental.pydantic: leaf
types before the parent model that references them. `FhirCodingInput`,
`FhirCodeableConceptInput`, `FhirIdentifierInput`, `FhirReferenceInput`,
`FhirPeriodInput`, `FhirContactPointInput` are reused from
app.gql.organization.types.input; `FhirAttachmentInput` is reused from
app.gql.healthcare_service.types.input. `FhirQuantityInput`/
`FhirRangeInput`/`FhirContactDetailInput`/`FhirUsageContextInput` and the
Questionnaire-item family ARE new — see app.gql.questionnaire.types.response's
docstring for the same reasoning, plus the recursive-type note there (it
applies identically to `FhirQuestionnaireItemInput`).
"""

from __future__ import annotations

from typing import Annotated

import strawberry
from strawberry.scalars import JSON

from app.fhir.schemas.questionnaire import (
    FhirContactDetail,
    FhirQuantity,
    FhirQuestionnaireInput as FhirQuestionnaireInputSchema,
    FhirQuestionnaireItem,
    FhirQuestionnaireItemAnswerOption,
    FhirQuestionnaireItemEnableWhen,
    FhirQuestionnaireItemInitial,
    FhirRange,
    FhirUsageContext,
)

# Importing these ensures FhirCodingInput/FhirCodeableConceptInput/
# FhirIdentifierInput/FhirReferenceInput/FhirPeriodInput/
# FhirContactPointInput and FhirAttachmentInput are registered before
# FhirQuestionnaireInput below — see this module's docstring.
import app.gql.organization.types.input  # noqa: F401
import app.gql.healthcare_service.types.input  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.input(
    model=FhirQuantity,
    all_fields=True,
    description="Input for a FHIR R4 Quantity.",
)
class FhirQuantityInput:
    """Input for a FHIR R4 Quantity."""


@strawberry.experimental.pydantic.input(
    model=FhirRange,
    all_fields=True,
    description="Input for a FHIR R4 Range.",
)
class FhirRangeInput:
    """Input for a FHIR R4 Range."""


@strawberry.experimental.pydantic.input(
    model=FhirContactDetail,
    all_fields=True,
    description="Input for one Questionnaire.contact entry.",
)
class FhirContactDetailInput:
    """Input for one Questionnaire.contact entry."""


@strawberry.experimental.pydantic.input(
    model=FhirUsageContext,
    all_fields=True,
    description="Input for one Questionnaire.useContext entry.",
)
class FhirUsageContextInput:
    """Input for one Questionnaire.useContext entry."""


@strawberry.experimental.pydantic.input(
    model=FhirQuestionnaireItemEnableWhen,
    all_fields=True,
    description="Input for one Questionnaire.item.enableWhen entry.",
)
class FhirQuestionnaireItemEnableWhenInput:
    """Input for one Questionnaire.item.enableWhen entry."""


@strawberry.experimental.pydantic.input(
    model=FhirQuestionnaireItemAnswerOption,
    all_fields=True,
    description="Input for one Questionnaire.item.answerOption entry.",
)
class FhirQuestionnaireItemAnswerOptionInput:
    """Input for one Questionnaire.item.answerOption entry."""


@strawberry.experimental.pydantic.input(
    model=FhirQuestionnaireItemInitial,
    all_fields=True,
    description="Input for one Questionnaire.item.initial entry.",
)
class FhirQuestionnaireItemInitialInput:
    """Input for one Questionnaire.item.initial entry."""


@strawberry.experimental.pydantic.input(
    model=FhirQuestionnaireItem,
    all_fields=True,
    description="Input for one Questionnaire.item entry — recursive (item.item nests to unbounded depth).",
)
class FhirQuestionnaireItemInput:
    """Input for one Questionnaire.item entry — recursive. `item` is
    overridden explicitly, using `strawberry.lazy()` rather than a bare
    forward-reference string — see
    app.gql.questionnaire.types.response.FhirQuestionnaireItemType's
    docstring for why a bare string isn't enough here."""

    item: list[
        Annotated["FhirQuestionnaireItemInput", strawberry.lazy(__name__)]
    ] | None = None


@strawberry.experimental.pydantic.input(
    model=FhirQuestionnaireInputSchema,
    all_fields=True,
    description=(
        "Input for createFhirQuestionnaire/updateFhirQuestionnaire — a "
        "genuine FHIR R4 Questionnaire shape, translated per-connector on "
        "write. See app.connectors.base.QuestionnaireWireTranslator."
    ),
)
class FhirQuestionnaireInput:
    """Input for createFhirQuestionnaire/updateFhirQuestionnaire."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar, same as Organization's own extension field.
    extension: JSON | None = None
