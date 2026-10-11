from typing import Annotated

import strawberry

from app.gql.common.pagination import LimitArg, OffsetArg, SortArg, TotalModeArg
from app.gql.context import get_container
from app.gql.enums import TotalModeEnum
from app.gql.errors import translate_errors
from app.gql.location.types.filter import LocationFilterInput
from app.gql.location.types.response import LocationType, PaginatedLocationType
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
        self,
        info: strawberry.types.Info,
        location_id: Annotated[
            int, strawberry.argument(description="Public location identifier.")
        ],
    ) -> LocationType:
        """Fetch a single Location by its integer ID — mirrors GET /locations/{id}."""
        actor = require_gql_permission(info, "location", "read")
        service = get_container(info).location.location_service()
        data = await service.get_by_id(location_id, actor)
        return _to_location_type(data)

    @strawberry.field(
        description=(
            "List Locations, optionally narrowed by `filters` (name, identifier, "
            "status, operationalStatus, locationType, physicalType, address sub-fields, "
            "organization/partof/endpoint references, near — see LocationFilterInput), "
            "with `sort` (e.g. `-name`), `totalMode` (`accurate`|`none`), and "
            "`limit`/`offset` pagination (default limit 50, max 200). `orgId` is not a "
            "filter — Location reads are always scoped to the caller's own org via "
            "their JWT. Requires the `location:read` permission."
        )
    )
    @translate_errors
    async def locations(
        self,
        info: strawberry.types.Info,
        filters: Annotated[
            LocationFilterInput | None,
            strawberry.argument(
                description="Search parameters to narrow the Location list — see LocationFilterInput."
            ),
        ] = None,
        sort: SortArg = None,
        total_mode: TotalModeArg = TotalModeEnum.accurate,
        limit: LimitArg = 50,
        offset: OffsetArg = 0,
    ) -> PaginatedLocationType:
        """List Locations with optional filters — mirrors GET /locations/."""
        actor = require_gql_permission(info, "location", "read")
        service = get_container(info).location.location_service()
        # Default to an all-None filter set when the caller omits `filters` entirely —
        # keeps the ListLocationsSchema construction below uniform either way.
        f = filters or LocationFilterInput()
        list_filters = ListLocationsSchema(
            name=f.name,
            identifier=f.identifier,
            location_status=f.location_status,
            operational_status=f.operational_status,
            location_type=f.location_type,
            physical_type=f.physical_type,
            address=f.address,
            address_city=f.address_city,
            address_state=f.address_state,
            address_postal_code=f.address_postal_code,
            address_country=f.address_country,
            address_use=f.address_use,
            organization=f.organization,
            partof=f.partof,
            endpoint=f.endpoint,
            near=f.near,
            sort=sort,
            total_mode=total_mode,
            limit=limit,
            offset=offset,
        )
        data = await service.list(list_filters, actor)
        return _to_paginated_location_type(data)
