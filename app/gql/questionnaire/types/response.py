"""
GraphQL object (output) types for the Questionnaire resource.

One canonical, genuinely FHIR R4-shaped Questionnaire — the same shape
regardless of which connector (internal, medplum, ...) is actually
active; mirrors app.gql.encounter.types.response exactly — see that
module and app.gql.organization's package docstring for the overall
idea, and app.connectors.base.QuestionnaireWireTranslator for how each
connector's own wire conventions get bridged to this one canonical shape.

Declaration order matters for strawberry.experimental.pydantic: leaf
types before the parent model that references them. `FhirCodingType`,
`FhirCodeableConceptType`, `FhirIdentifierType`, `FhirReferenceType`,
`FhirMetaType`, `FhirPeriodType`, `FhirContactPointType` are NOT
redeclared here — reused from app.gql.organization.types.response.
`FhirAttachmentType` is reused from app.gql.healthcare_service.types.response.
`FhirQuantityType`/`FhirRangeType`/`FhirContactDetailType`/
`FhirUsageContextType` and the Questionnaire-item family ARE new.

`Questionnaire.item` is RECURSIVE (item.item nests to unbounded depth) —
see `FhirQuestionnaireItemType`'s own docstring below for why its `item`
field needs an explicit `strawberry.lazy()`-wrapped override instead of
being left to `all_fields=True`'s auto-derivation.
"""

from __future__ import annotations

from typing import Annotated

import strawberry
from strawberry.scalars import JSON

from app.fhir.schemas.questionnaire import (
    FhirContactDetail,
    FhirQuantity,
    FhirQuestionnaireItem,
    FhirQuestionnaireItemAnswerOption,
    FhirQuestionnaireItemEnableWhen,
    FhirQuestionnaireItemInitial,
    FhirQuestionnaireResponse,
    FhirRange,
    FhirUsageContext,
)

# Importing these ensures FhirCodingType/FhirCodeableConceptType/
# FhirIdentifierType/FhirReferenceType/FhirMetaType/FhirPeriodType/
# FhirContactPointType and FhirAttachmentType are registered before
# FhirQuestionnaireType below — see this module's docstring.
import app.gql.organization.types.response  # noqa: F401
import app.gql.healthcare_service.types.response  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.type(
    model=FhirQuantity,
    all_fields=True,
    description="FHIR R4 Quantity.",
)
class FhirQuantityType:
    """FHIR R4 Quantity."""


@strawberry.experimental.pydantic.type(
    model=FhirRange,
    all_fields=True,
    description="FHIR R4 Range.",
)
class FhirRangeType:
    """FHIR R4 Range."""


@strawberry.experimental.pydantic.type(
    model=FhirContactDetail,
    all_fields=True,
    description="Questionnaire.contact entry.",
)
class FhirContactDetailType:
    """Questionnaire.contact entry."""


@strawberry.experimental.pydantic.type(
    model=FhirUsageContext,
    all_fields=True,
    description="One Questionnaire.useContext entry.",
)
class FhirUsageContextType:
    """One Questionnaire.useContext entry."""


@strawberry.experimental.pydantic.type(
    model=FhirQuestionnaireItemEnableWhen,
    all_fields=True,
    description="One Questionnaire.item.enableWhen entry.",
)
class FhirQuestionnaireItemEnableWhenType:
    """One Questionnaire.item.enableWhen entry."""


@strawberry.experimental.pydantic.type(
    model=FhirQuestionnaireItemAnswerOption,
    all_fields=True,
    description="One Questionnaire.item.answerOption entry.",
)
class FhirQuestionnaireItemAnswerOptionType:
    """One Questionnaire.item.answerOption entry."""


@strawberry.experimental.pydantic.type(
    model=FhirQuestionnaireItemInitial,
    all_fields=True,
    description="One Questionnaire.item.initial entry.",
)
class FhirQuestionnaireItemInitialType:
    """One Questionnaire.item.initial entry."""


@strawberry.experimental.pydantic.type(
    model=FhirQuestionnaireItem,
    all_fields=True,
    description="One Questionnaire.item entry — recursive (item.item nests to unbounded depth).",
)
class FhirQuestionnaireItemType:
    """One Questionnaire.item entry — recursive.

    `item` is overridden explicitly (rather than left to `all_fields=True`'s
    auto-derivation) because strawberry's pydantic integration tries to
    eagerly resolve the registered strawberry type for a nested Pydantic
    model at DECORATION time — which fails for a genuinely self-referential
    model, since this very class isn't registered against
    `FhirQuestionnaireItem` until the decorator finishes running (see
    `UnregisteredTypeException` if this override is removed).

    A bare forward-reference string (`list["FhirQuestionnaireItemType"]`)
    still isn't enough on its own: `strawberry.experimental.pydantic.type`
    builds the actual class via `dataclasses.make_dataclass()`
    (`strawberry/experimental/pydantic/object_type.py`), which sets the
    resulting class's `__module__` to wherever `make_dataclass` itself was
    called from (strawberry's own internal module) rather than this one —
    so a plain string annotation resolves against the WRONG module's
    globals at schema-build time and raises `UnresolvedFieldTypeError`.
    `strawberry.lazy(__name__)` sidesteps this by carrying the target
    module path as data instead of relying on `__module__` introspection."""

    item: list[
        Annotated["FhirQuestionnaireItemType", strawberry.lazy(__name__)]
    ] | None


@strawberry.experimental.pydantic.type(
    model=FhirQuestionnaireResponse,
    all_fields=True,
    description=(
        "A full FHIR R4 Questionnaire resource — the one canonical shape "
        "returned regardless of which connector (internal, medplum, ...) is "
        "active."
    ),
)
class FhirQuestionnaireType:
    """A full FHIR R4 Questionnaire resource."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar, same as Organization's own extension field.
    extension: JSON | None
