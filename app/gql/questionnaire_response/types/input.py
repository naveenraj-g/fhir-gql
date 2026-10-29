"""
GraphQL input types for the QuestionnaireResponse resource.

Mirrors app.gql.questionnaire.types.input exactly — see that module and
app.gql.questionnaire_response.types.response's docstring for the overall
idea and the mutual-recursion reasoning (applies identically here, to
`FhirQuestionnaireResponseAnswerInput`/`FhirQuestionnaireResponseItemInput`).
`FhirCodingInput`, `FhirIdentifierInput`, `FhirReferenceInput` are reused
from app.gql.organization.types.input; `FhirAttachmentInput` is reused
from app.gql.healthcare_service.types.input. `FhirQuantityInput` and the
item/answer family ARE new.
"""

from __future__ import annotations

from typing import Annotated

import strawberry
from strawberry.scalars import JSON

from app.fhir.schemas.questionnaire_response import (
    FhirQuantity,
    FhirQuestionnaireResponseAnswer,
    FhirQuestionnaireResponseInput as FhirQuestionnaireResponseInputSchema,
    FhirQuestionnaireResponseItem,
)

# Importing these ensures FhirCodingInput/FhirIdentifierInput/
# FhirReferenceInput and FhirAttachmentInput are registered before
# FhirQuestionnaireResponseInput below — see this module's docstring.
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
    model=FhirQuestionnaireResponseAnswer,
    all_fields=True,
    description="Input for one QuestionnaireResponse.item.answer entry — mutually recursive with item.",
)
class FhirQuestionnaireResponseAnswerInput:
    """Input for one QuestionnaireResponse.item.answer entry — mutually
    recursive with FhirQuestionnaireResponseItemInput. `item` is
    overridden explicitly using `strawberry.lazy()` — see
    app.gql.questionnaire_response.types.response.FhirQuestionnaireResponseAnswerType's
    docstring for why a bare forward-reference string isn't enough here."""

    item: list[
        Annotated["FhirQuestionnaireResponseItemInput", strawberry.lazy(__name__)]
    ] | None = None


@strawberry.experimental.pydantic.input(
    model=FhirQuestionnaireResponseItem,
    all_fields=True,
    description="Input for one QuestionnaireResponse.item entry — recursive (item.item nests to unbounded depth).",
)
class FhirQuestionnaireResponseItemInput:
    """Input for one QuestionnaireResponse.item entry — recursive. Only
    `item` (self-referential) needs the override; `answer` references the
    already-defined Answer input type above."""

    item: list[
        Annotated["FhirQuestionnaireResponseItemInput", strawberry.lazy(__name__)]
    ] | None = None


@strawberry.experimental.pydantic.input(
    model=FhirQuestionnaireResponseInputSchema,
    all_fields=True,
    description=(
        "Input for createFhirQuestionnaireResponse/updateFhirQuestionnaireResponse "
        "— a genuine FHIR R4 QuestionnaireResponse shape, translated per-connector "
        "on write. See app.connectors.internal.translators.questionnaire_response "
        "and app.connectors.medplum.translators.questionnaire_response."
    ),
)
class FhirQuestionnaireResponseInput:
    """Input for createFhirQuestionnaireResponse/updateFhirQuestionnaireResponse."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar, same as Organization's own extension field.
    extension: JSON | None = None
