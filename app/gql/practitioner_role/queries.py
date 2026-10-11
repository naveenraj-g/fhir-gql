from typing import Annotated

import strawberry

from app.gql.common.pagination import LimitArg, OffsetArg, SortArg, TotalModeArg
from app.gql.context import get_container
from app.gql.enums import TotalModeEnum
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.practitioner_role.types.filter import PractitionerRoleFilterInput
from app.gql.practitioner_role.types.response import (
    PaginatedPractitionerRoleBookingType,
    PaginatedPractitionerRoleType,
    PractitionerRoleType,
)
from app.schemas.practitioner_role.input import ListPractitionerRolesSchema
from app.schemas.practitioner_role.response import (
    PaginatedPractitionerRoleBookingResponse,
    PaginatedPractitionerRoleResponse,
    PractitionerRoleResponse,
)


def _to_practitioner_role_type(data: dict) -> PractitionerRoleType:
    """Shared conversion: raw fhir-server dict -> validated PractitionerRoleResponse -> PractitionerRoleType."""
    return PractitionerRoleType.from_pydantic(
        PractitionerRoleResponse.model_validate(data)
    )


def _to_paginated_practitioner_role_type(data: dict) -> PaginatedPractitionerRoleType:
    """Shared conversion: raw fhir-server dict -> validated PaginatedPractitionerRoleResponse -> PaginatedPractitionerRoleType."""
    return PaginatedPractitionerRoleType.from_pydantic(
        PaginatedPractitionerRoleResponse.model_validate(data)
    )


def _to_paginated_booking_type(data: dict) -> PaginatedPractitionerRoleBookingType:
    """Shared conversion: raw fhir-server dict -> validated PaginatedPractitionerRoleBookingResponse -> PaginatedPractitionerRoleBookingType."""
    return PaginatedPractitionerRoleBookingType.from_pydantic(
        PaginatedPractitionerRoleBookingResponse.model_validate(data)
    )


@strawberry.type(description="Query fields for the PractitionerRole resource.")
class PractitionerRoleQuery:
    """Query fields for the PractitionerRole resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single PractitionerRole by its integer ID, scoped to the caller's organization. Requires the `practitioner_role:read` permission."
    )
    @translate_errors
    async def practitioner_role(
        self,
        info: strawberry.types.Info,
        resource_id: Annotated[
            int,
            strawberry.argument(description="Public practitioner_role identifier."),
        ],
    ) -> PractitionerRoleType:
        """Fetch a single PractitionerRole by its integer ID — mirrors GET /practitioner-roles/{id}."""
        actor = require_gql_permission(info, "practitioner_role", "read")
        service = get_container(info).practitioner_role.practitioner_role_service()
        data = await service.get_by_id(resource_id, actor)
        return _to_practitioner_role_type(data)

    @strawberry.field(
        description=(
            "List PractitionerRoles, optionally narrowed by `filters` (active, date, "
            "email, phone, telecom, identifier, role, specialty, practitioner/"
            "organization/location/service/endpoint references — see "
            "PractitionerRoleFilterInput), with `sort` (e.g. `-created_at`), `totalMode` "
            "(`accurate`|`none`), and `limit`/`offset` pagination (default limit 50, max "
            "200). `orgId` is not a filter — PractitionerRole reads are always scoped to "
            "the caller's own org via their JWT. Requires the `practitioner_role:read` "
            "permission."
        )
    )
    @translate_errors
    async def practitioner_roles(
        self,
        info: strawberry.types.Info,
        filters: Annotated[
            PractitionerRoleFilterInput | None,
            strawberry.argument(
                description="Search parameters to narrow the PractitionerRole list — see PractitionerRoleFilterInput."
            ),
        ] = None,
        sort: SortArg = None,
        total_mode: TotalModeArg = TotalModeEnum.accurate,
        limit: LimitArg = 50,
        offset: OffsetArg = 0,
    ) -> PaginatedPractitionerRoleType:
        """List PractitionerRoles with optional filters — mirrors GET /practitioner-roles/."""
        actor = require_gql_permission(info, "practitioner_role", "read")
        service = get_container(info).practitioner_role.practitioner_role_service()
        # Default to an all-None filter set when the caller omits `filters` entirely —
        # keeps the ListPractitionerRolesSchema construction below uniform either way.
        f = filters or PractitionerRoleFilterInput()
        list_filters = ListPractitionerRolesSchema(
            active=f.active,
            date=f.date,
            email=f.email,
            phone=f.phone,
            telecom=f.telecom,
            identifier=f.identifier,
            role=f.role,
            specialty=f.specialty,
            practitioner=f.practitioner,
            organization=f.organization,
            location=f.location,
            service=f.service,
            endpoint=f.endpoint,
            sort=sort,
            total_mode=total_mode,
            limit=limit,
            offset=offset,
        )
        data = await service.list(list_filters, actor)
        return _to_paginated_practitioner_role_type(data)

    @strawberry.field(
        description=(
            "List practitioners available for appointment booking — active PractitionerRoles "
            "enriched with the linked Practitioner's name, gender, photo, and qualifications, "
            "plus enriched Location/HealthcareService data. NOT part of the current "
            "fhir-server API (no `/practitioner-roles/booking` route exists) — calling this "
            "will 404 against a real fhir-server instance; kept as-is, out of scope for the "
            "JWT-rollout/schema-restructure work applied to the rest of this resource. "
            "Filter by `specialtyCode` and/or `dayOfWeek`. Requires the "
            "`practitioner_role:read` permission."
        )
    )
    @translate_errors
    async def practitioner_roles_for_booking(
        self,
        info: strawberry.types.Info,
        specialty_code: Annotated[
            str | None,
            strawberry.argument(description="Exact match on a coded specialty."),
        ] = None,
        day_of_week: Annotated[
            str | None,
            strawberry.argument(
                description="Filter to roles available on this day — mon|tue|wed|thu|fri|sat|sun."
            ),
        ] = None,
        org_id: Annotated[
            str | None,
            strawberry.argument(
                description="Filter by organization ID (tenant scoping)."
            ),
        ] = None,
        active: Annotated[
            bool, strawberry.argument(description="Filter by active status.")
        ] = True,
        limit: Annotated[int, strawberry.argument(description="Page size.")] = 50,
        offset: Annotated[
            int, strawberry.argument(description="Number of rows to skip.")
        ] = 0,
    ) -> PaginatedPractitionerRoleBookingType:
        """List practitioners enriched for booking UIs — mirrors GET /practitioner-roles/booking (not present on fhir-server)."""
        actor = require_gql_permission(info, "practitioner_role", "read")
        service = get_container(info).practitioner_role.practitioner_role_service()
        data = await service.list_for_booking(
            active=active,
            specialty_code=specialty_code,
            day_of_week=day_of_week,
            org_id=org_id,
            limit=limit,
            offset=offset,
        )
        return _to_paginated_booking_type(data)
