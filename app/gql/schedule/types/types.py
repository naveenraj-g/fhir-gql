"""
GraphQL response (output) types for the Schedule resource, derived from the
existing Pydantic schemas in app/schemas/schedule/response.py via
`strawberry.experimental.pydantic`. Input types live in
app/gql/schedule/types/input.py — this split mirrors the
app/schemas/schedule/{response,input}.py split one layer down.

Unlike every other resource's input types, there are no
`ServiceCategoryInput`/`ServiceTypeInput`/`SpecialtyInput` wrappers —
`service_category`/`service_type`/`specialty` aren't accepted as input at
all (they're derived by ScheduleService from PractitionerRole/
HealthcareService actors), so only their *output* types exist.

Naming convention: `<X>Response` (Pydantic) -> `<X>Type` (GraphQL object type).
"""

import strawberry

from app.schemas.schedule.response import (
    PaginatedScheduleResponse,
    ScheduleActorResponse,
    ScheduleIdentifierResponse,
    ScheduleResponse,
    ScheduleServiceCategoryResponse,
    ScheduleServiceTypeResponse,
    ScheduleSpecialtyResponse,
)

# ── Response (output) types — leaf sub-resources first ───────────────────────


@strawberry.experimental.pydantic.type(model=ScheduleIdentifierResponse, all_fields=True, description="A single Schedule.identifier entry.")
class ScheduleIdentifierType:
    """A single Schedule.identifier entry."""


@strawberry.experimental.pydantic.type(
    model=ScheduleServiceCategoryResponse, all_fields=True,
    description="A single Schedule.serviceCategory entry — derived from the attached HealthcareService actor(s), not client-supplied.",
)
class ScheduleServiceCategoryType:
    """A single Schedule.serviceCategory entry (derived, not client-supplied)."""


@strawberry.experimental.pydantic.type(
    model=ScheduleServiceTypeResponse, all_fields=True,
    description="A single Schedule.serviceType entry — derived from the attached HealthcareService actor(s), not client-supplied.",
)
class ScheduleServiceTypeType:
    """A single Schedule.serviceType entry (derived, not client-supplied)."""


@strawberry.experimental.pydantic.type(
    model=ScheduleSpecialtyResponse, all_fields=True,
    description="A single Schedule.specialty entry — derived from the attached PractitionerRole/HealthcareService actor(s), not client-supplied.",
)
class ScheduleSpecialtyType:
    """A single Schedule.specialty entry (derived, not client-supplied)."""


@strawberry.experimental.pydantic.type(model=ScheduleActorResponse, all_fields=True, description="A single Schedule.actor reference.")
class ScheduleActorType:
    """A single Schedule.actor reference."""


@strawberry.experimental.pydantic.type(
    model=ScheduleResponse, all_fields=True,
    description="A full Schedule resource, including all nested sub-resource arrays.",
)
class ScheduleType:
    """A full Schedule resource, including all nested sub-resource arrays."""


@strawberry.experimental.pydantic.type(model=PaginatedScheduleResponse, all_fields=True, description="Paginated envelope returned by the `schedules` query.")
class PaginatedScheduleType:
    """Paginated envelope returned by the `schedules` list query."""


__all__ = [
    "ScheduleIdentifierType",
    "ScheduleServiceCategoryType",
    "ScheduleServiceTypeType",
    "ScheduleSpecialtyType",
    "ScheduleActorType",
    "ScheduleType",
    "PaginatedScheduleType",
]
