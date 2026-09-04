from typing import Optional

import strawberry

from app.gql.context import get_container
from app.gql.enums import AddressUseEnum
from app.gql.errors import translate_errors
from app.gql.organization.types.types import OrganizationType, PaginatedOrganizationType
from app.gql.permissions import require_gql_permission
from app.schemas.organization.input import ListOrganizationsSchema
from app.schemas.organization.response import OrganizationResponse, PaginatedOrganizationResponse


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
        self, info: strawberry.types.Info, organization_id: int
    ) -> OrganizationType:
        """Fetch a single Organization by its integer ID — mirrors GET /organizations/{id}."""
        actor = require_gql_permission(info, "organization", "read")
        service = get_container(info).organization.organization_service()
        data = await service.get_by_id(organization_id, actor)
        return _to_org_type(data)

    @strawberry.field(
        description=(
            "List Organizations, optionally filtered by `name` (matches name or any alias, "
            "partial case-insensitive), `identifier` (exact business-identifier value), "
            "`orgType` (exact coded organization type — FHIR `type`), `active`, "
            "`address`/`addressCity`/`addressState`/"
            "`addressPostalCode`/`addressCountry`/`addressUse`, `partof`/`endpoint` (FHIR "
            "reference strings, e.g. `Organization/190001`), with `sort` (e.g. "
            "`-name`), `totalMode` (`accurate`|`none`), and `limit`/`offset` pagination "
            "(default limit 50, max 200). `orgId` is not a filter — Organization reads are "
            "always scoped to the caller's own org via their JWT. Requires the "
            "`organization:read` permission."
        )
    )
    @translate_errors
    async def organizations(
        self,
        info: strawberry.types.Info,
        name: Optional[str] = None,
        active: Optional[bool] = None,
        identifier: Optional[str] = None,
        org_type: Optional[str] = None,
        address: Optional[str] = None,
        address_city: Optional[str] = None,
        address_state: Optional[str] = None,
        address_postal_code: Optional[str] = None,
        address_country: Optional[str] = None,
        address_use: Optional[AddressUseEnum] = None,
        partof: Optional[str] = None,
        endpoint: Optional[str] = None,
        sort: Optional[str] = None,
        total_mode: str = "accurate",
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedOrganizationType:
        """List Organizations with optional filters — mirrors GET /organizations/."""
        actor = require_gql_permission(info, "organization", "read")
        service = get_container(info).organization.organization_service()
        filters = ListOrganizationsSchema(
            name=name,
            active=active,
            identifier=identifier,
            org_type=org_type,
            address=address,
            address_city=address_city,
            address_state=address_state,
            address_postal_code=address_postal_code,
            address_country=address_country,
            address_use=address_use,
            partof=partof,
            endpoint=endpoint,
            sort=sort,
            total_mode=total_mode,
            limit=limit,
            offset=offset,
        )
        data = await service.list(filters, actor)
        return _to_paginated_org_type(data)
