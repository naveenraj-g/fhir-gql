from typing import Annotated

import strawberry

from app.connectors.internal.gql.organization.types.filter import (
    OrganizationFilterInput,
)
from app.connectors.internal.gql.organization.types.response import (
    OrganizationType,
    PaginatedOrganizationType,
)
from app.connectors.internal.schemas.organization.input import ListOrganizationsSchema
from app.connectors.internal.schemas.organization.response import (
    OrganizationResponse,
    PaginatedOrganizationResponse,
)
from app.gql.common.pagination import LimitArg, OffsetArg, SortArg, TotalModeArg
from app.gql.context import get_container
from app.gql.enums import TotalModeEnum
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission


def _to_org_type(data: dict) -> OrganizationType:
    """Shared conversion: raw fhir-server dict -> validated OrganizationResponse -> OrganizationType."""
    return OrganizationType.from_pydantic(OrganizationResponse.model_validate(data))


def _to_paginated_org_type(data: dict) -> PaginatedOrganizationType:
    """Shared conversion: raw fhir-server dict -> validated PaginatedOrganizationResponse -> PaginatedOrganizationType."""
    return PaginatedOrganizationType.from_pydantic(
        PaginatedOrganizationResponse.model_validate(data)
    )


@strawberry.type(description="Query fields for the Organization resource.")
class OrganizationQuery:
    """Query fields for the Organization resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single Organization by its integer ID, scoped to the caller's organization. Requires the `organization:read` permission."
    )
    @translate_errors
    async def organization(
        self,
        info: strawberry.types.Info,
        organization_id: Annotated[
            int, strawberry.argument(description="Public organization identifier.")
        ],
    ) -> OrganizationType:
        """Fetch a single Organization by its integer ID — mirrors GET /organizations/{id}."""
        actor = require_gql_permission(info, "organization", "read")
        service = get_container(info).organization.organization_service()
        data = await service.get_by_id(organization_id, actor)
        return _to_org_type(data)

    @strawberry.field(
        description=(
            "List Organizations, optionally narrowed by `filters` (name, identifier, "
            "orgType, active, address sub-fields, partof/endpoint references — see "
            "OrganizationFilterInput), with `sort` (e.g. `-name`), `totalMode` "
            "(`accurate`|`none`), and `limit`/`offset` pagination (default limit 50, "
            "max 200). `orgId` is not a filter — Organization reads are always scoped "
            "to the caller's own org via their JWT. Requires the `organization:read` "
            "permission."
        )
    )
    @translate_errors
    async def organizations(
        self,
        info: strawberry.types.Info,
        filters: Annotated[
            OrganizationFilterInput | None,
            strawberry.argument(
                description="Search parameters to narrow the Organization list — see OrganizationFilterInput."
            ),
        ] = None,
        sort: SortArg = None,
        total_mode: TotalModeArg = TotalModeEnum.accurate,
        limit: LimitArg = 50,
        offset: OffsetArg = 0,
    ) -> PaginatedOrganizationType:
        """List Organizations with optional filters — mirrors GET /organizations/."""
        actor = require_gql_permission(info, "organization", "read")
        service = get_container(info).organization.organization_service()
        # Default to an all-None filter set when the caller omits `filters` entirely —
        # keeps the ListOrganizationsSchema construction below uniform either way.
        f = filters or OrganizationFilterInput()
        list_filters = ListOrganizationsSchema(
            name=f.name,
            active=f.active,
            identifier=f.identifier,
            org_type=f.org_type,
            address=f.address,
            address_city=f.address_city,
            address_state=f.address_state,
            address_postal_code=f.address_postal_code,
            address_country=f.address_country,
            address_use=f.address_use,
            partof=f.partof,
            endpoint=f.endpoint,
            sort=sort,
            total_mode=total_mode,
            limit=limit,
            offset=offset,
        )
        data = await service.list(list_filters, actor)
        return _to_paginated_org_type(data)
