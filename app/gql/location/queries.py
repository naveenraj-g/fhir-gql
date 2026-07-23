from typing import Optional

import strawberry

from app.gql.context import get_container
from app.gql.enums import LocationStatusEnum
from app.gql.errors import translate_errors
from app.gql.location.types.types import LocationType, PaginatedLocationType
from app.gql.permissions import require_gql_permission
from app.schemas.location.input import ListLocationsSchema
from app.schemas.location.response import LocationResponse, PaginatedLocationResponse


def _to_location_type(data: dict) -> LocationType:
    """Shared conversion: raw fhir-server dict -> validated LocationResponse -> LocationType."""
    return LocationType.from_pydantic(LocationResponse.model_validate(data))


def _to_paginated_location_type(data: dict) -> PaginatedLocationType:
    """Shared conversion: raw fhir-server dict -> validated PaginatedLocationResponse -> PaginatedLocationType."""
    return PaginatedLocationType.from_pydantic(
        PaginatedLocationResponse.model_validate(data)
    )


@strawberry.type(description="Query fields for the Location resource.")
class LocationQuery:
    """Query fields for the Location resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single Location by its integer ID, scoped to the caller's organization. Requires the `location:read` permission."
    )
    @translate_errors
    async def location(
        self, info: strawberry.types.Info, location_id: int
    ) -> LocationType:
        """Fetch a single Location by its integer ID — mirrors GET /locations/{id}."""
        actor = require_gql_permission(info, "location", "read")
        service = get_container(info).location.location_service()
        data = await service.get_by_id(location_id, actor)
        return _to_location_type(data)

    @strawberry.field(
        description=(
            "List Locations, optionally filtered by `orgId` (tenant scoping) and `status`, "
            "with `limit`/`offset` pagination (default limit 20, max 200). Requires the "
            "`location:read` permission."
        )
    )
    @translate_errors
    async def locations(
        self,
        info: strawberry.types.Info,
        org_id: Optional[str] = None,
        status: Optional[LocationStatusEnum] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedLocationType:
        """List Locations with optional filters — mirrors GET /locations/."""
        actor = require_gql_permission(info, "location", "read")
        service = get_container(info).location.location_service()
        filters = ListLocationsSchema(
            org_id=org_id, status=status, limit=limit, offset=offset
        )
        data = await service.list(filters, actor)
        return _to_paginated_location_type(data)
