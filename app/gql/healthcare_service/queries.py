from typing import Annotated

import strawberry

from app.gql.common.pagination import LimitArg, OffsetArg, SortArg, TotalModeArg
from app.gql.context import get_container
from app.gql.enums import TotalModeEnum
from app.gql.errors import translate_errors
from app.gql.healthcare_service.types.filter import HealthcareServiceFilterInput
from app.gql.healthcare_service.types.response import (
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
        self,
        info: strawberry.types.Info,
        service_id: Annotated[
            int,
            strawberry.argument(description="Public healthcare_service identifier."),
        ],
    ) -> HealthcareServiceType:
        """Fetch a single HealthcareService by its integer ID — mirrors GET /healthcare-services/{id}."""
        actor = require_gql_permission(info, "healthcare_service", "read")
        service = get_container(info).healthcare_service.healthcare_service_service()
        data = await service.get_by_id(service_id, actor)
        return _to_healthcare_service_type(data)

    @strawberry.field(
        description=(
            "List HealthcareServices, optionally narrowed by `filters` (name, identifier, "
            "active, category, serviceType, specialty, characteristic, program, "
            "providedBy/location/coverageArea/endpoint references — see "
            "HealthcareServiceFilterInput), with `sort` (e.g. `-name`), `totalMode` "
            "(`accurate`|`none`), and `limit`/`offset` pagination (default limit 50, "
            "max 200). `orgId` is not a filter — HealthcareService reads are always "
            "scoped to the caller's own org via their JWT. Requires the "
            "`healthcare_service:read` permission."
        )
    )
    @translate_errors
    async def healthcare_services(
        self,
        info: strawberry.types.Info,
        filters: Annotated[
            HealthcareServiceFilterInput | None,
            strawberry.argument(
                description="Search parameters to narrow the HealthcareService list — see HealthcareServiceFilterInput."
            ),
        ] = None,
        sort: SortArg = None,
        total_mode: TotalModeArg = TotalModeEnum.accurate,
        limit: LimitArg = 50,
        offset: OffsetArg = 0,
    ) -> PaginatedHealthcareServiceType:
        """List HealthcareServices with optional filters — mirrors GET /healthcare-services/."""
        actor = require_gql_permission(info, "healthcare_service", "read")
        service = get_container(info).healthcare_service.healthcare_service_service()
        # Default to an all-None filter set when the caller omits `filters` entirely —
        # keeps the ListHealthcareServicesSchema construction below uniform either way.
        f = filters or HealthcareServiceFilterInput()
        list_filters = ListHealthcareServicesSchema(
            name=f.name,
            active=f.active,
            identifier=f.identifier,
            category=f.category,
            service_type=f.service_type,
            specialty=f.specialty,
            characteristic=f.characteristic,
            program=f.program,
            provided_by=f.provided_by,
            location=f.location,
            coverage_area=f.coverage_area,
            endpoint=f.endpoint,
            sort=sort,
            total_mode=total_mode,
            limit=limit,
            offset=offset,
        )
        data = await service.list(list_filters, actor)
        return _to_paginated_healthcare_service_type(data)
