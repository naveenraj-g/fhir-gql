"""
GraphQL response (output) types for the Slot resource, derived from the
existing Pydantic schemas in app/schemas/slot/response.py via
`strawberry.experimental.pydantic`. Input types live in
app/gql/slot/types/input.py — this split mirrors the
app/schemas/slot/{response,input}.py split one layer down.

Naming convention: `<X>Response` (Pydantic) -> `<X>Type` (GraphQL object type).
"""

import strawberry

from app.schemas.slot.response import (
    PaginatedSlotResponse,
    SlotGenerateResponse,
    SlotIdentifierResponse,
    SlotResponse,
    SlotServiceCategoryResponse,
    SlotServiceTypeResponse,
    SlotSpecialtyResponse,
)

# ── Response (output) types — leaf sub-resources first ───────────────────────


@strawberry.experimental.pydantic.type(model=SlotIdentifierResponse, all_fields=True, description="A single Slot.identifier entry.")
class SlotIdentifierType:
    """A single Slot.identifier entry."""


@strawberry.experimental.pydantic.type(
    model=SlotServiceCategoryResponse, all_fields=True,
    description="A single Slot.serviceCategory entry — defaults from the parent Schedule if not overridden.",
)
class SlotServiceCategoryType:
    """A single Slot.serviceCategory entry."""


@strawberry.experimental.pydantic.type(
    model=SlotServiceTypeResponse, all_fields=True,
    description="A single Slot.serviceType entry — defaults from the parent Schedule if not overridden.",
)
class SlotServiceTypeType:
    """A single Slot.serviceType entry."""


@strawberry.experimental.pydantic.type(
    model=SlotSpecialtyResponse, all_fields=True,
    description="A single Slot.specialty entry — defaults from the parent Schedule if not overridden.",
)
class SlotSpecialtyType:
    """A single Slot.specialty entry."""


@strawberry.experimental.pydantic.type(
    model=SlotResponse, all_fields=True,
    description="A full Slot resource, including all nested sub-resource arrays.",
)
class SlotType:
    """A full Slot resource, including all nested sub-resource arrays."""


@strawberry.experimental.pydantic.type(model=PaginatedSlotResponse, all_fields=True, description="Paginated envelope returned by the `slots` query.")
class PaginatedSlotType:
    """Paginated envelope returned by the `slots` list query."""


@strawberry.experimental.pydantic.type(
    model=SlotGenerateResponse, all_fields=True,
    description="Result of `generateSlots` — how many Slots were created, skipped as duplicates, or failed.",
)
class SlotGenerateResultType:
    """Result of `generateSlots` — created/skipped/failed counts and the new Slot ids."""


__all__ = [
    "SlotIdentifierType",
    "SlotServiceCategoryType",
    "SlotServiceTypeType",
    "SlotSpecialtyType",
    "SlotType",
    "PaginatedSlotType",
    "SlotGenerateResultType",
]
