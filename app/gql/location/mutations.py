import strawberry

from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.location.types.input import LocationCreateInput, LocationPatchInput
from app.gql.location.types.types import LocationType
from app.gql.permissions import require_gql_permission
from app.schemas.location.response import LocationResponse


def _to_location_type(data: dict) -> LocationType:
    """Shared conversion: raw fhir-server dict -> validated LocationResponse -> LocationType."""
    return LocationType.from_pydantic(LocationResponse.model_validate(data))


@strawberry.type(description="Mutation fields for the Location resource.")
class LocationMutation:
    """Mutation fields for the Location resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description=(
            "Create a new Location. `userId` and `orgId` are required for tenant scoping. If "
            "`managingOrganization` is provided, it must reference an existing organization in "
            "the caller's own tenant. If `partOf` is provided, it must reference an existing "
            "Location in the caller's own tenant. `createdBy` is stamped automatically from the "
            "caller's JWT. Requires the `location:create` permission."
        )
    )
    @translate_errors
    async def create_location(
        self, info: strawberry.types.Info, input: LocationCreateInput
    ) -> LocationType:
        """Create a new Location — mirrors POST /locations/, including managingOrganization/partOf validation in LocationService."""
        actor = require_gql_permission(info, "location", "create")
        service = get_container(info).location.location_service()
        dto = input.to_pydantic()
        data = await service.create(dto, actor)
        return _to_location_type(data)

    @strawberry.mutation(
        description=(
            "Partially update a Location's scalar fields. Array sub-resources are not "
            "patchable here (delete and re-create). `partOf` (re-parenting) and "
            "`managingOrganization` ARE patchable and are re-validated for existence/tenant "
            "match; `partOf` changes are additionally checked to avoid a circular hierarchy "
            "(`extensions.code == 409`). Scoped to the caller's organization — raises "
            "`extensions.code == 404` if the Location belongs to a different org. `updatedBy` is "
            "stamped automatically from the caller's JWT. Requires the `location:update` permission."
        )
    )
    @translate_errors
    async def update_location(
        self, info: strawberry.types.Info, location_id: int, input: LocationPatchInput
    ) -> LocationType:
        """Partially update a Location — mirrors PATCH /locations/{id}."""
        actor = require_gql_permission(info, "location", "update")
        service = get_container(info).location.location_service()
        dto = input.to_pydantic()
        data = await service.update(location_id, dto, actor)
        return _to_location_type(data)

    @strawberry.mutation(
        description=(
            "Permanently delete a Location and all its associated child records. Scoped to the "
            "caller's organization — raises `extensions.code == 404` if the Location belongs to "
            "a different org. Irreversible. Requires the `location:delete` permission. Returns "
            "true on success."
        )
    )
    @translate_errors
    async def delete_location(
        self, info: strawberry.types.Info, location_id: int
    ) -> bool:
        """Delete a Location and its child records — mirrors DELETE /locations/{id}. Returns true on success."""
        actor = require_gql_permission(info, "location", "delete")
        service = get_container(info).location.location_service()
        await service.delete(location_id, actor)
        return True
