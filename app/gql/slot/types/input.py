"""
GraphQL input type for the Slot resource.

Mirrors app.gql.organization.types.input/app.gql.location.types.input/
app.gql.healthcare_service.types.input/app.gql.practitioner.types.input/
app.gql.practitioner_role.types.input/app.gql.schedule.types.input exactly
— see those modules and app.gql.organization's package docstring for the
overall idea. `FhirCodeableConceptInput`, `FhirIdentifierInput`,
`FhirReferenceInput` are reused from app.gql.organization.types.input
rather than redeclared — Slot uses the exact same underlying Pydantic
models, so a second strawberry.experimental.pydantic.input registration
for the same model would conflict rather than add anything.
"""

import strawberry
from strawberry.scalars import JSON

from app.fhir.schemas.slot import FhirSlotInput as FhirSlotInputSchema

# Importing this ensures FhirCodeableConceptInput/FhirIdentifierInput/
# FhirReferenceInput are registered before FhirSlotInput below — see this
# module's docstring.
import app.gql.organization.types.input  # noqa: F401


@strawberry.experimental.pydantic.input(
    model=FhirSlotInputSchema,
    all_fields=True,
    description=(
        "Input for createFhirSlot/updateFhirSlot — a genuine FHIR R4 Slot "
        "shape, translated per-connector on write. See "
        "app.connectors.base.SlotWireTranslator."
    ),
)
class FhirSlotInput:
    """Input for createFhirSlot/updateFhirSlot."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar, same as Organization's own extension/assigner fields.
    extension: JSON | None = None
