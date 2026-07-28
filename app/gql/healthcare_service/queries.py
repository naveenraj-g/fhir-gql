from typing import Optional

import strawberry

from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.healthcare_service.types.types import (
    HealthcareServiceType,
    PaginatedHealthcareServiceType,
)
from app.gql.permissions import require_gql_permission
from app.schemas.healthcare_service.input import ListHealthcareServicesSchema
from app.schemas.healthcare_service.response import (
    HealthcareServiceResponse,
    PaginatedHealthcareServiceResponse,
)


def _to_healthcare_service_type(data: dict) -> HealthcareServiceType:
    """Shared conversion: raw fhir-server dict -> validated HealthcareServiceResponse -> HealthcareServiceType."""
    return HealthcareServiceType.from_pydantic(
        HealthcareServiceResponse.model_validate(data)
    )


def _to_paginated_healthcare_service_type(data: dict) -> PaginatedHealthcareServiceType:
    """Shared conversion: raw fhir-server dict -> validated PaginatedHealthcareServiceResponse -> PaginatedHealthcareServiceType."""
    return PaginatedHealthcareServiceType.from_pydantic(
        PaginatedHealthcareServiceResponse.model_validate(data)
    )


@strawberry.type(description="Query fields for the HealthcareService resource.")
class HealthcareServiceQuery:
    """Query fields for the HealthcareService resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single HealthcareService by its integer ID, scoped to the caller's organization. Requires the `healthcare_service:read` permission."
    )
    @translate_errors
    async def healthcare_service(
        self, info: strawberry.types.Info, service_id: int
    ) -> HealthcareServiceType:
        """Fetch a single HealthcareService by its integer ID — mirrors GET /healthcare-services/{id}."""
        actor = require_gql_permission(info, "healthcare_service", "read")
        service = get_container(info).healthcare_service.healthcare_service_service()
        data = await service.get_by_id(service_id, actor)
        return _to_healthcare_service_type(data)

    @strawberry.field(
        description=(
            "List HealthcareServices, optionally filtered by `name` (case-insensitive substring) "
            "and `active` status, with `limit`/`offset` pagination (default limit 20, max 200). "
            "Requires the `healthcare_service:read` permission."
        )
    )
    @translate_errors
    async def healthcare_services(
        self,
        info: strawberry.types.Info,
        name: Optional[str] = None,
        active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PaginatedHealthcareServiceType:
        """List HealthcareServices with optional filters — mirrors GET /healthcare-services/."""
        actor = require_gql_permission(info, "healthcare_service", "read")
        service = get_container(info).healthcare_service.healthcare_service_service()
        filters = ListHealthcareServicesSchema(
            name=name, active=active, limit=limit, offset=offset
        )
        data = await service.list(filters, actor)
        return _to_paginated_healthcare_service_type(data)
