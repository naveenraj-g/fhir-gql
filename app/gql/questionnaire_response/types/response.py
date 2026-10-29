"""
GraphQL object (output) types for the QuestionnaireResponse resource.

One canonical, genuinely FHIR R4-shaped QuestionnaireResponse — the same
shape regardless of which connector (internal, medplum, ...) is actually
active; mirrors app.gql.questionnaire.types.response's overall pattern —
see that module and app.gql.organization's package docstring for the
overall idea, and app.connectors.base's Protocol docs for how each
connector's own wire conventions get bridged to this one canonical shape.

Declaration order matters for strawberry.experimental.pydantic: leaf
types before the parent model that references them. `FhirCodingType`,
`FhirIdentifierType`, `FhirReferenceType`, `FhirMetaType`,
`FhirAttachmentType` are NOT redeclared here — reused from
app.gql.organization.types.response / app.gql.healthcare_service.types.response.
`FhirQuantityType` and the item/answer family ARE new.

`item`/`answer` are MUTUALLY RECURSIVE (an item's children live either
under item.item or under one of its answers' item[] — see
app.fhir.schemas.questionnaire_response's module docstring for the FHIR
invariant). `FhirQuestionnaireResponseAnswerType` is declared first and
needs an explicit `strawberry.lazy()`-wrapped override for its own `item`
field (forward reference to a type not yet defined);
`FhirQuestionnaireResponseItemType` is declared second and only needs the
override for its own self-referential `item` field — its `answer` field
references the already-defined Answer type, so `all_fields=True` handles
it on its own. See `FhirQuestionnaireResponseAnswerType`'s own docstring
for the full `UnregisteredTypeException`/`UnresolvedFieldTypeError`
reasoning (same as app.gql.questionnaire.types.response.FhirQuestionnaireItemType's).
"""

from __future__ import annotations

from typing import Annotated

import strawberry
from strawberry.scalars import JSON

from app.fhir.schemas.questionnaire_response import (
    FhirQuantity,
    FhirQuestionnaireResponseAnswer,
    FhirQuestionnaireResponseItem,
    FhirQuestionnaireResponseResponse,
)

# Importing these ensures FhirCodingType/FhirIdentifierType/
# FhirReferenceType/FhirMetaType and FhirAttachmentType are registered
# before FhirQuestionnaireResponseType below — see this module's docstring.
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
    model=FhirQuestionnaireResponseAnswer,
    all_fields=True,
    description="One QuestionnaireResponse.item.answer entry — mutually recursive with item (see module docstring).",
)
class FhirQuestionnaireResponseAnswerType:
    """One QuestionnaireResponse.item.answer entry — mutually recursive
    with FhirQuestionnaireResponseItemType.

    `item` is overridden explicitly (rather than left to `all_fields=True`'s
    auto-derivation) because strawberry's pydantic integration tries to
    eagerly resolve the registered strawberry type for a nested Pydantic
    model at DECORATION time — which fails here since
    `FhirQuestionnaireResponseItemType` isn't defined (let alone
    registered) yet when this class is being decorated. A bare
    forward-reference string isn't enough either — see
    app.gql.questionnaire.types.response.FhirQuestionnaireItemType's own
    docstring for the full `UnresolvedFieldTypeError` reasoning;
    `strawberry.lazy(__name__)` sidesteps it the same way there."""

    item: list[
        Annotated["FhirQuestionnaireResponseItemType", strawberry.lazy(__name__)]
    ] | None


@strawberry.experimental.pydantic.type(
    model=FhirQuestionnaireResponseItem,
    all_fields=True,
    description="One QuestionnaireResponse.item entry — recursive (item.item nests to unbounded depth).",
)
class FhirQuestionnaireResponseItemType:
    """One QuestionnaireResponse.item entry — recursive. Only `item`
    (the genuinely self-referential field) needs the `strawberry.lazy()`
    override; `answer` references `FhirQuestionnaireResponseAnswerType`,
    already defined above by the time this class is decorated, so
    `all_fields=True` resolves it without help."""

    item: list[
        Annotated["FhirQuestionnaireResponseItemType", strawberry.lazy(__name__)]
    ] | None


@strawberry.experimental.pydantic.type(
    model=FhirQuestionnaireResponseResponse,
    all_fields=True,
    description=(
        "A full FHIR R4 QuestionnaireResponse resource — the one canonical "
        "shape returned regardless of which connector (internal, medplum, "
        "...) is active."
    ),
)
class FhirQuestionnaireResponseType:
    """A full FHIR R4 QuestionnaireResponse resource."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar, same as Organization's own extension field.
    extension: JSON | None
