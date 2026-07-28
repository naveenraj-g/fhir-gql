"""
GraphQL input types for the Schedule resource, derived from the existing
Pydantic schemas in app/schemas/schedule/input.py via
`strawberry.experimental.pydantic`. Output types live in
app/gql/schedule/types/types.py.

Naming convention:
  - `ScheduleIdentifierInput`/`ScheduleActorInput` (Pydantic, already end in
    "Input") are imported under a `...Schema` alias so the plain name is
    free for this module's GraphQL wrapper class, same collision-handling
    pattern used throughout this project's other resource ports.
"""

import strawberry

# Registers IdentifierUse/etc. as GraphQL enums (side-effect import) —
# required before wrapping any input schema whose fields use them.
import app.gql.enums  # noqa: F401
from app.schemas.schedule.input import ScheduleCreateSchema, SchedulePatchSchema
from app.schemas.schedule.input import ScheduleActorInput as ScheduleActorInputSchema
from app.schemas.schedule.input import ScheduleIdentifierInput as ScheduleIdentifierInputSchema

# ── Input types — leaf sub-resources first ───────────────────────────────────


@strawberry.experimental.pydantic.input(model=ScheduleIdentifierInputSchema, all_fields=True, description="Input for one Schedule.identifier entry.")
class ScheduleIdentifierInput:
    """Input for one Schedule.identifier entry."""


@strawberry.experimental.pydantic.input(
    model=ScheduleActorInputSchema, all_fields=True,
    description=(
        "Input for one Schedule.actor reference. Allowed types: Practitioner, PractitionerRole, "
        "Location, HealthcareService, Patient (validated for existence + tenant match), plus "
        "RelatedPerson/Device (accepted unvalidated, not implemented in this project)."
    ),
)
class ScheduleActorInput:
    """Input for one Schedule.actor reference."""


@strawberry.experimental.pydantic.input(
    model=ScheduleCreateSchema, all_fields=True,
    description=(
        "Input for `createSchedule`. `actor` is required (at least one entry, including at "
        "least one PractitionerRole or HealthcareService) — `serviceCategory`/`serviceType`/"
        "`specialty` are NOT accepted here; they're derived automatically from those actors. A "
        "Schedule belongs to at most one provider: at most one Practitioner/PractitionerRole "
        "actor is allowed, and Patient actors cannot be mixed with provider actors. "
        "`createdBy` is stamped automatically from the caller's JWT — do not supply it."
    ),
)
class ScheduleCreateInput:
    """Input for `createSchedule` — mirrors ScheduleCreateSchema."""


@strawberry.experimental.pydantic.input(
    model=SchedulePatchSchema, all_fields=True,
    description=(
        "Input for `updateSchedule` — every field optional, at least one must be set. `actor` "
        "and the derived serviceCategory/serviceType/specialty arrays are create-only — delete "
        "and re-create to change those."
    ),
)
class SchedulePatchInput:
    """Input for `updateSchedule` — every field optional, at least one must be set (enforced in ScheduleService)."""


# `ListSchedulesSchema` is a query-parameter schema, not a mutation payload
# — exposed as plain field arguments on the `schedules` query instead,
# matching every other resource's `List*Schema` treatment.
__all__ = [
    "ScheduleIdentifierInput",
    "ScheduleActorInput",
    "ScheduleCreateInput",
    "SchedulePatchInput",
]
