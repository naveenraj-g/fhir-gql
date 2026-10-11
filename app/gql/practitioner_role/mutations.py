from typing import Annotated

import strawberry

from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.practitioner_role.types.input import (
    PractitionerRoleCreateInput,
    PractitionerRolePatchInput,
)
from app.gql.practitioner_role.types.response import PractitionerRoleType
from app.schemas.practitioner_role.response import PractitionerRoleResponse


def _to_practitioner_role_type(data: dict) -> PractitionerRoleType:
    """Shared conversion: raw fhir-server dict -> validated PractitionerRoleResponse -> PractitionerRoleType."""
    return PractitionerRoleType.from_pydantic(
        PractitionerRoleResponse.model_validate(data)
    )


@strawberry.type(description="Mutation fields for the PractitionerRole resource.")
class PractitionerRoleMutation:
    """Mutation fields for the PractitionerRole resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description=(
            "Create a new PractitionerRole and any combination of its sub-resources "
            "(identifier, code, specialty, location, healthcareService, telecom, "
            "availableTime, notAvailable, endpoint) atomically in one request. If "
            "`practitioner`/`organization` are set, fhir-server validates each exists and "
            "belongs to the caller's own tenant — a GraphQL error with "
            "`extensions.code == 404` otherwise; each `location`/`healthcareService` entry "
            "is validated the same way. `createdBy` is stamped automatically from the "
            "caller's JWT. Requires the `practitioner_role:create` permission."
        )
    )
    @translate_errors
    async def create_practitioner_role(
        self,
        info: strawberry.types.Info,
        input: Annotated[
            PractitionerRoleCreateInput,
            strawberry.argument(
                description="The PractitionerRole (and any sub-resources) to create."
            ),
        ],
    ) -> PractitionerRoleType:
        """Create a new PractitionerRole — mirrors POST /practitioner-roles/."""
        actor = require_gql_permission(info, "practitioner_role", "create")
        service = get_container(info).practitioner_role.practitioner_role_service()
        dto = input.to_pydantic()
        data = await service.create(dto, actor)
        return _to_practitioner_role_type(data)

    @strawberry.mutation(
        description=(
            "Partially update a PractitionerRole. Only supplied fields are written; every "
            "supplied sub-resource list (identifier, code, specialty, location, "
            "healthcareService, telecom, availableTime, notAvailable, endpoint — even "
            "`[]`) replaces the corresponding rows wholesale. `practitioner`/"
            "`organization` may be set to null to clear the reference; fhir-server "
            "re-validates them (and every `location`/`healthcareService` entry) "
            "server-side whenever supplied. `updatedBy` is stamped automatically from the "
            "caller's JWT. Requires the `practitioner_role:update` permission."
        )
    )
    @translate_errors
    async def update_practitioner_role(
        self,
        info: strawberry.types.Info,
        resource_id: Annotated[
            int,
            strawberry.argument(description="Public practitioner_role identifier."),
        ],
        input: Annotated[
            PractitionerRolePatchInput,
            strawberry.argument(
                description="Fields to update — only these are written."
            ),
        ],
    ) -> PractitionerRoleType:
        """Partially update a PractitionerRole — mirrors PATCH /practitioner-roles/{id}."""
        actor = require_gql_permission(info, "practitioner_role", "update")
        service = get_container(info).practitioner_role.practitioner_role_service()
        dto = input.to_pydantic()
        data = await service.update(resource_id, dto, actor)
        return _to_practitioner_role_type(data)

    @strawberry.mutation(
        description=(
            "Permanently delete a PractitionerRole and all its associated child records. "
            "Scoped to the caller's organization — raises a 404 GraphQL error if the "
            "PractitionerRole belongs to a different org. Irreversible. Requires the "
            "`practitioner_role:delete` permission. Returns true on success."
        )
    )
    @translate_errors
    async def delete_practitioner_role(
        self,
        info: strawberry.types.Info,
        resource_id: Annotated[
            int,
            strawberry.argument(description="Public practitioner_role identifier."),
        ],
    ) -> bool:
        """Delete a PractitionerRole and its child records — mirrors DELETE /practitioner-roles/{id}. Returns true on success."""
        actor = require_gql_permission(info, "practitioner_role", "delete")
        service = get_container(info).practitioner_role.practitioner_role_service()
        await service.delete(resource_id, actor)
        return True
