import strawberry

from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.organization.types.input import PatchOrgInput, RegisterOrgInput
from app.gql.organization.types.types import OrgType
from app.gql.permissions import require_gql_permission
from app.schemas.organization.response import OrgResponse


def _to_org_type(data: dict) -> OrgType:
    """Shared conversion: raw fhir-server dict -> validated OrgResponse -> OrgType."""
    return OrgType.from_pydantic(OrgResponse.model_validate(data))


@strawberry.type(description="Mutation fields for the Organization resource.")
class OrganizationMutation:
    """Mutation fields for the Organization resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description=(
            "Create a new Organization. Enforces that `name` and `type` are provided (FHIR "
            "leaves both optional). Deduplicates by name — a case-insensitive match against an "
            "existing organization raises a GraphQL error with `extensions.code == 409`. If "
            "`partof` is provided, it must reference an existing organization in the caller's "
            "own tenant — `extensions.code == 404` otherwise. "
            "`createdBy` is stamped automatically from the caller's JWT. Requires the "
            "`org:create` permission."
        )
    )
    @translate_errors
    async def register_organization(
        self, info: strawberry.types.Info, input: RegisterOrgInput
    ) -> OrgType:
        """Create a new Organization — mirrors POST /organizations/, including the duplicate-name 409 check in OrganizationsService."""
        actor = require_gql_permission(info, "org", "create")
        service = get_container(info).organization.organization_service()
        dto = input.to_pydantic()
        data = await service.register(dto, actor)
        return _to_org_type(data)

    @strawberry.mutation(
        description=(
            "Partially update an Organization's `active`, `name`, or `partofDisplay` fields — "
            "at least one must be set. Child arrays are not patchable here (see "
            "`PatchOrgInput`). Scoped to the caller's organization — raises a 404 GraphQL "
            "error if the organization belongs to a different org. `updatedBy` is stamped "
            "automatically from the caller's JWT. Requires the `org:update` permission."
        )
    )
    @translate_errors
    async def update_organization(
        self, info: strawberry.types.Info, organization_id: int, input: PatchOrgInput
    ) -> OrgType:
        """Partially update an Organization — mirrors PATCH /organizations/{id}."""
        actor = require_gql_permission(info, "org", "update")
        service = get_container(info).organization.organization_service()
        dto = input.to_pydantic()
        data = await service.update(organization_id, dto, actor)
        return _to_org_type(data)

    @strawberry.mutation(
        description=(
            "Permanently delete an Organization and all its associated child records. "
            "Scoped to the caller's organization — raises a 404 GraphQL error if the "
            "organization belongs to a different org. Irreversible. Requires the "
            "`org:delete` permission. Returns true on success."
        )
    )
    @translate_errors
    async def delete_organization(
        self, info: strawberry.types.Info, organization_id: int
    ) -> bool:
        """Delete an Organization and its child records — mirrors DELETE /organizations/{id}. Returns true on success."""
        actor = require_gql_permission(info, "org", "delete")
        service = get_container(info).organization.organization_service()
        await service.delete(organization_id, actor)
        return True
