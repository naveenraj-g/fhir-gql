"""
GraphQL input types for the Slot resource, derived from the existing
Pydantic schemas in app/schemas/slot/input.py via
`strawberry.experimental.pydantic`. Output types live in
app/gql/slot/types/types.py.

Naming convention:
  - `SlotIdentifierInput`/`SlotServiceCategoryInput`/`SlotServiceTypeInput`/
    `SlotSpecialtyInput` (Pydantic, already end in "Input") are imported
    under a `...Schema` alias so the plain name is free for this module's
    GraphQL wrapper class, same collision-handling pattern used throughout
    this project's other resource ports.
"""

import strawberry

# Registers SlotStatus/IdentifierUse/etc. as GraphQL enums (side-effect
# import) — required before wrapping any input schema whose fields use them.
import app.gql.enums  # noqa: F401
from app.schemas.slot.input import SlotCreateSchema, SlotGenerateSchema, SlotPatchSchema
from app.schemas.slot.input import SlotIdentifierInput as SlotIdentifierInputSchema
from app.schemas.slot.input import SlotServiceCategoryInput as SlotServiceCategoryInputSchema
from app.schemas.slot.input import SlotServiceTypeInput as SlotServiceTypeInputSchema
from app.schemas.slot.input import SlotSpecialtyInput as SlotSpecialtyInputSchema

# ── Input types — leaf sub-resources first ───────────────────────────────────


@strawberry.experimental.pydantic.input(model=SlotIdentifierInputSchema, all_fields=True, description="Input for one Slot.identifier entry.")
class SlotIdentifierInput:
    """Input for one Slot.identifier entry."""


@strawberry.experimental.pydantic.input(
    model=SlotServiceCategoryInputSchema, all_fields=True,
    description="Input for one Slot.serviceCategory entry. Defaults from the parent Schedule if omitted entirely.",
)
class SlotServiceCategoryInput:
    """Input for one Slot.serviceCategory entry."""


@strawberry.experimental.pydantic.input(
    model=SlotServiceTypeInputSchema, all_fields=True,
    description="Input for one Slot.serviceType entry. Defaults from the parent Schedule if omitted entirely.",
)
class SlotServiceTypeInput:
    """Input for one Slot.serviceType entry."""


@strawberry.experimental.pydantic.input(
    model=SlotSpecialtyInputSchema, all_fields=True,
    description="Input for one Slot.specialty entry. Defaults from the parent Schedule if omitted entirely.",
)
class SlotSpecialtyInput:
    """Input for one Slot.specialty entry."""


@strawberry.experimental.pydantic.input(
    model=SlotCreateSchema, all_fields=True,
    description=(
        "Input for `createSlot`. `schedule` must reference an existing Schedule in the caller's "
        "own tenant. If `serviceCategory`/`serviceType`/`specialty` are omitted, they default "
        "from the parent Schedule's own stored values. `createdBy` is stamped automatically from "
        "the caller's JWT — do not supply it."
    ),
)
class SlotCreateInput:
    """Input for `createSlot` — mirrors SlotCreateSchema."""


@strawberry.experimental.pydantic.input(
    model=SlotPatchSchema, all_fields=True,
    description=(
        "Input for `updateSlot` — every field optional, at least one must be set. `schedule` and "
        "the sub-resource arrays are create-only — delete and re-create to change those."
    ),
)
class SlotPatchInput:
    """Input for `updateSlot` — every field optional, at least one must be set (enforced in SlotService)."""


@strawberry.experimental.pydantic.input(
    model=SlotGenerateSchema, all_fields=True,
    description=(
        "Input for `generateSlots` — availability-aware bulk Slot generation. The Schedule's "
        "actor must be a PractitionerRole with declared availability; slots are only created "
        "inside its declared weekly hours, excluding leave periods and any already-existing Slot."
    ),
)
class SlotGenerateInput:
    """Input for `generateSlots` — mirrors SlotGenerateSchema."""


# `ListSlotsSchema` is a query-parameter schema, not a mutation payload —
# exposed as plain field arguments on the `slots` query instead, matching
# every other resource's `List*Schema` treatment.
__all__ = [
    "SlotIdentifierInput",
    "SlotServiceCategoryInput",
    "SlotServiceTypeInput",
    "SlotSpecialtyInput",
    "SlotCreateInput",
    "SlotPatchInput",
    "SlotGenerateInput",
]
