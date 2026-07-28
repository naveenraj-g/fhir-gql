from typing import Optional

import strawberry

from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.practitioner.types.types import PaginatedPractitionerType, PractitionerType
from app.schemas.practitioner.input import ListPractitionersSchema
from app.schemas.practitioner.response import PaginatedPractitionerResponse, PractitionerResponse


def _to_practitioner_type(data: dict) -> PractitionerType:
    """Shared conversion: raw fhir-server dict -> validated PractitionerResponse -> PractitionerType."""
    return PractitionerType.from_pydantic(PractitionerResponse.model_validate(data))


def _to_paginated_practitioner_type(data: dict) -> PaginatedPractitionerType:
    """Shared conversion: raw fhir-server dict -> validated PaginatedPractitionerResponse -> PaginatedPractitionerType."""
    return PaginatedPractitionerType.from_pydantic(PaginatedPractitionerResponse.model_validate(data))


@strawberry.type(description="Query fields for the Practitioner resource.")
class PractitionerQuery:
    """Query fields for the Practitioner resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single Practitioner by its integer ID, including all sub-resource arrays. Requires the `practitioner:read` permission."
    )
    @translate_errors
    async def practitioner(self, info: strawberry.types.Info, practitioner_id: int) -> PractitionerType:
        """Fetch a single Practitioner by its integer ID — mirrors GET /practitioners/{id}."""
        actor = require_gql_permission(info, "practitioner", "read")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.get_by_id(practitioner_id, actor)
        return _to_practitioner_type(data)

    @strawberry.field(
        description=(
            "List Practitioners, optionally filtered by `familyName`/`givenName` (partial, "
            "case-insensitive), `active`, `userId`, or `orgId`, with `limit`/`offset` pagination "
            "(default limit 20, max 200). Requires the `practitioner:read` permission."
        )
    )
    @translate_errors
    async def practitioners(
        self,
        info: strawberry.types.Info,
        family_name: Optional[str] = None,
        given_name: Optional[str] = None,
        active: Optional[bool] = None,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedPractitionerType:
        """List Practitioners with optional filters — mirrors GET /practitioners/."""
        actor = require_gql_permission(info, "practitioner", "read")
        service = get_container(info).practitioner.practitioner_service()
        filters = ListPractitionersSchema(
            family_name=family_name,
            given_name=given_name,
            active=active,
            user_id=user_id,
            org_id=org_id,
            limit=limit,
            offset=offset,
        )
        data = await service.list(filters, actor)
        return _to_paginated_practitioner_type(data)

    @strawberry.field(
        description="Fetch the Practitioner record belonging to the caller's own JWT identity. Requires the `practitioner:read` permission."
    )
    @translate_errors
    async def my_practitioner(self, info: strawberry.types.Info) -> PractitionerType:
        """Fetch the caller's own Practitioner record via JWT identity — mirrors GET /practitioners/me."""
        actor = require_gql_permission(info, "practitioner", "read")
        service = get_container(info).practitioner.practitioner_service()
        data = await service.get_me(actor)
        return _to_practitioner_type(data)
