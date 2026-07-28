import strawberry

from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.healthcare_service.types.input import (
    HealthcareServiceCreateInput,
    HealthcareServicePatchInput,
)
from app.gql.healthcare_service.types.types import HealthcareServiceType
from app.gql.permissions import require_gql_permission
from app.schemas.healthcare_service.response import HealthcareServiceResponse


def _to_healthcare_service_type(data: dict) -> HealthcareServiceType:
    """Shared conversion: raw fhir-server dict -> validated HealthcareServiceResponse -> HealthcareServiceType."""
    return HealthcareServiceType.from_pydantic(
        HealthcareServiceResponse.model_validate(data)
    )


@strawberry.type(description="Mutation fields for the HealthcareService resource.")
class HealthcareServiceMutation:
    """Mutation fields for the HealthcareService resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description=(
            "Create a new HealthcareService. If `providedBy` is set, it must reference an "
            "existing organization in the caller's own tenant. If `location`/`coverageArea` "
            "entries are set, each must reference an existing Location in the caller's own "
            "tenant. `createdBy` is stamped automatically from the caller's JWT. Requires the "
            "`healthcare_service:create` permission."
        )
    )
    @translate_errors
    async def create_healthcare_service(
        self, info: strawberry.types.Info, input: HealthcareServiceCreateInput
    ) -> HealthcareServiceType:
        """Create a new HealthcareService — mirrors POST /healthcare-services/, including reference validation in HealthcareServiceService."""
        actor = require_gql_permission(info, "healthcare_service", "create")
        service = get_container(info).healthcare_service.healthcare_service_service()
        dto = input.to_pydantic()
        data = await service.create(dto, actor)
        return _to_healthcare_service_type(data)

    @strawberry.mutation(
        description=(
            "Partially update a HealthcareService's scalar and photo fields. `providedBy`, "
            "`location`, `coverageArea`, and array sub-resources are not patchable here (delete "
            "and re-create). Scoped to the caller's organization — raises "
            "`extensions.code == 404` if the HealthcareService belongs to a different org. "
            "`updatedBy` is stamped automatically from the caller's JWT. Requires the "
            "`healthcare_service:update` permission."
        )
    )
    @translate_errors
    async def update_healthcare_service(
        self,
        info: strawberry.types.Info,
        service_id: int,
        input: HealthcareServicePatchInput,
    ) -> HealthcareServiceType:
        """Partially update a HealthcareService — mirrors PATCH /healthcare-services/{id}."""
        actor = require_gql_permission(info, "healthcare_service", "update")
        service = get_container(info).healthcare_service.healthcare_service_service()
        dto = input.to_pydantic()
        data = await service.update(service_id, dto, actor)
        return _to_healthcare_service_type(data)

    @strawberry.mutation(
        description=(
            "Permanently delete a HealthcareService and all its associated child records. Scoped "
            "to the caller's organization — raises `extensions.code == 404` if the "
            "HealthcareService belongs to a different org. Irreversible. Requires the "
            "`healthcare_service:delete` permission. Returns true on success."
        )
    )
    @translate_errors
    async def delete_healthcare_service(
        self, info: strawberry.types.Info, service_id: int
    ) -> bool:
        """Delete a HealthcareService and its child records — mirrors DELETE /healthcare-services/{id}. Returns true on success."""
        actor = require_gql_permission(info, "healthcare_service", "delete")
        service = get_container(info).healthcare_service.healthcare_service_service()
        await service.delete(service_id, actor)
        return True
