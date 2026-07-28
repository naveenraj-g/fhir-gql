from typing import Optional

import strawberry

from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.practitioner_role.types.types import (
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
    return PractitionerRoleType.from_pydantic(PractitionerRoleResponse.model_validate(data))


def _to_paginated_practitioner_role_type(data: dict) -> PaginatedPractitionerRoleType:
    """Shared conversion: raw fhir-server dict -> validated PaginatedPractitionerRoleResponse -> PaginatedPractitionerRoleType."""
    return PaginatedPractitionerRoleType.from_pydantic(PaginatedPractitionerRoleResponse.model_validate(data))


def _to_paginated_booking_type(data: dict) -> PaginatedPractitionerRoleBookingType:
    """Shared conversion: raw fhir-server dict -> validated PaginatedPractitionerRoleBookingResponse -> PaginatedPractitionerRoleBookingType."""
    return PaginatedPractitionerRoleBookingType.from_pydantic(PaginatedPractitionerRoleBookingResponse.model_validate(data))


@strawberry.type(description="Query fields for the PractitionerRole resource.")
class PractitionerRoleQuery:
    """Query fields for the PractitionerRole resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single PractitionerRole by its integer ID, including all child arrays. Requires the `practitioner_role:read` permission."
    )
    @translate_errors
    async def practitioner_role(self, info: strawberry.types.Info, resource_id: int) -> PractitionerRoleType:
        """Fetch a single PractitionerRole by its integer ID — mirrors GET /practitioner-roles/{id}."""
        actor = require_gql_permission(info, "practitioner_role", "read")
        service = get_container(info).practitioner_role.practitioner_role_service()
        data = await service.get_by_id(resource_id, actor)
        return _to_practitioner_role_type(data)

    @strawberry.field(
        description=(
            "List PractitionerRoles, optionally filtered by `active`, `practitionerId`, `userId`, "
            "or `orgId`, with `limit`/`offset` pagination (default limit 20, max 200). Requires "
            "the `practitioner_role:read` permission."
        )
    )
    @translate_errors
    async def practitioner_roles(
        self,
        info: strawberry.types.Info,
        active: Optional[bool] = None,
        practitioner_id: Optional[int] = None,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedPractitionerRoleType:
        """List PractitionerRoles with optional filters — mirrors GET /practitioner-roles/."""
        actor = require_gql_permission(info, "practitioner_role", "read")
        service = get_container(info).practitioner_role.practitioner_role_service()
        filters = ListPractitionerRolesSchema(
            active=active, practitioner_id=practitioner_id, user_id=user_id, org_id=org_id, limit=limit, offset=offset
        )
        data = await service.list(filters, actor)
        return _to_paginated_practitioner_role_type(data)

    @strawberry.field(
        description=(
            "List practitioners available for appointment booking — active PractitionerRoles "
            "enriched with the linked Practitioner's name, gender, photo, and qualifications, "
            "plus enriched Location/HealthcareService data. Filter by `specialtyCode` and/or "
            "`dayOfWeek`. Requires the `practitioner_role:read` permission."
        )
    )
    @translate_errors
    async def practitioner_roles_for_booking(
        self,
        info: strawberry.types.Info,
        specialty_code: Optional[str] = None,
        day_of_week: Optional[str] = None,
        org_id: Optional[str] = None,
        active: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedPractitionerRoleBookingType:
        """List practitioners enriched for booking UIs — mirrors GET /practitioner-roles/booking."""
        actor = require_gql_permission(info, "practitioner_role", "read")
        service = get_container(info).practitioner_role.practitioner_role_service()
        data = await service.list_for_booking(
            active=active, specialty_code=specialty_code, day_of_week=day_of_week, org_id=org_id, limit=limit, offset=offset
        )
        return _to_paginated_booking_type(data)
