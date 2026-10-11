from typing import Annotated

import strawberry

from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.organization.types.input import (
    OrganizationCreateInput,
    OrganizationPatchInput,
)
from app.gql.organization.types.response import OrganizationType
from app.gql.permissions import require_gql_permission
from app.schemas.organization.response import OrganizationResponse


def _to_org_type(data: dict) -> OrganizationType:
    """Shared conversion: raw fhir-server dict -> validated OrganizationResponse -> OrganizationType."""
    return OrganizationType.from_pydantic(OrganizationResponse.model_validate(data))


@strawberry.type(description="Mutation fields for the Organization resource.")
class OrganizationMutation:
    """Mutation fields for the Organization resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description=(
            "Create a new Organization and any combination of its sub-resources "
            "(identifier, type, alias, telecom, address, contact, endpoint) atomically in one "
            "request. If `partof` is provided, fhir-server validates it exists, belongs to the "
            "caller's own tenant, and (on update) wouldn't create a circular hierarchy — a "
            "GraphQL error with `extensions.code == 404`/`422` otherwise. `createdBy` is "
            "stamped automatically from the caller's JWT. Requires the `organization:create` "
            "permission."
        )
    )
    @translate_errors
    async def create_organization(
        self,
        info: strawberry.types.Info,
        input: Annotated[
            OrganizationCreateInput,
            strawberry.argument(
                description="The Organization (and any sub-resources) to create."
            ),
        ],
    ) -> OrganizationType:
        """Create a new Organization — mirrors POST /organizations/."""
        actor = require_gql_permission(info, "organization", "create")
        service = get_container(info).organization.organization_service()
        dto = input.to_pydantic()
        data = await service.create(dto, actor)
        return _to_org_type(data)

    @strawberry.mutation(
        description=(
            "Partially update an Organization. Only supplied fields are written; every "
            "supplied sub-resource list (identifier, type, alias, telecom, address, contact, "
            "endpoint — even `[]`) replaces the corresponding rows wholesale. `partof` may be "
            "set to null to clear the parent link. Scoped to the caller's organization — "
            "raises a 404 GraphQL error if the organization belongs to a different org. "
            "`updatedBy` is stamped automatically from the caller's JWT. Requires the "
            "`organization:update` permission."
        )
    )
    @translate_errors
    async def update_organization(
        self,
        info: strawberry.types.Info,
        organization_id: Annotated[
            int, strawberry.argument(description="Public organization identifier.")
        ],
        input: Annotated[
            OrganizationPatchInput,
            strawberry.argument(description="Fields to update — only these are written."),
        ],
    ) -> OrganizationType:
        """Partially update an Organization — mirrors PATCH /organizations/{id}."""
        actor = require_gql_permission(info, "organization", "update")
        service = get_container(info).organization.organization_service()
        dto = input.to_pydantic()
        data = await service.update(organization_id, dto, actor)
        return _to_org_type(data)

    @strawberry.mutation(
        description=(
            "Permanently delete an Organization and all its associated child records. "
            "Scoped to the caller's organization — raises a 404 GraphQL error if the "
            "organization belongs to a different org. Irreversible. Requires the "
            "`organization:delete` permission. Returns true on success."
        )
    )
    @translate_errors
    async def delete_organization(
        self,
        info: strawberry.types.Info,
        organization_id: Annotated[
            int, strawberry.argument(description="Public organization identifier.")
        ],
    ) -> bool:
        """Delete an Organization and its child records — mirrors DELETE /organizations/{id}. Returns true on success."""
        actor = require_gql_permission(info, "organization", "delete")
        service = get_container(info).organization.organization_service()
        await service.delete(organization_id, actor)
        return True
