from typing import Optional

import strawberry

from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.organization.types.types import OrgType, PaginatedOrgType
from app.gql.permissions import require_gql_permission
from app.schemas.organization.input import ListOrgsSchema, MeOrgsSchema
from app.schemas.organization.response import OrgResponse, PaginatedOrgResponse


def _to_org_type(data: dict) -> OrgType:
    """Shared conversion: raw fhir-server dict -> validated OrgResponse -> OrgType."""
    return OrgType.from_pydantic(OrgResponse.model_validate(data))


def _to_paginated_org_type(data: dict) -> PaginatedOrgType:
    """Shared conversion: raw fhir-server dict -> validated PaginatedOrgResponse -> PaginatedOrgType."""
    return PaginatedOrgType.from_pydantic(PaginatedOrgResponse.model_validate(data))


@strawberry.type(description="Query fields for the Organization resource.")
class OrganizationQuery:
    """Query fields for the Organization resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single Organization by its integer ID, scoped to the caller's organization. Requires the `org:read` permission."
    )
    @translate_errors
    async def organization(
        self, info: strawberry.types.Info, organization_id: int
    ) -> OrgType:
        """Fetch a single Organization by its integer ID — mirrors GET /organizations/{id}."""
        actor = require_gql_permission(info, "org", "read")
        service = get_container(info).organization.organization_service()
        data = await service.get_by_id(organization_id, actor)
        return _to_org_type(data)

    @strawberry.field(
        description=(
            "List Organizations, optionally filtered by `name` (case-insensitive substring), "
            "`active` status, `userId`, or `orgId`, with `limit`/`offset` pagination "
            "(default limit 50, max 200). Requires the `org:read` permission."
        )
    )
    @translate_errors
    async def organizations(
        self,
        info: strawberry.types.Info,
        name: Optional[str] = None,
        active: Optional[bool] = None,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedOrgType:
        """List Organizations with optional filters — mirrors GET /organizations/."""
        actor = require_gql_permission(info, "org", "read")
        service = get_container(info).organization.organization_service()
        filters = ListOrgsSchema(
            name=name,
            active=active,
            user_id=user_id,
            org_id=org_id,
            limit=limit,
            offset=offset,
        )
        data = await service.list(filters, actor)
        return _to_paginated_org_type(data)

    @strawberry.field(
        description=(
            "List Organizations scoped to the caller's own JWT identity — `userId`/`orgId` "
            "are resolved from the token and cannot be overridden by the caller. Requires the "
            "`org:read` permission."
        )
    )
    @translate_errors
    async def my_organizations(
        self,
        info: strawberry.types.Info,
        active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedOrgType:
        """List Organizations scoped to the caller's own JWT identity — mirrors GET /organizations/me."""
        actor = require_gql_permission(info, "org", "read")
        service = get_container(info).organization.organization_service()
        filters = MeOrgsSchema(active=active, limit=limit, offset=offset)
        data = await service.get_me(filters, actor)
        return _to_paginated_org_type(data)
