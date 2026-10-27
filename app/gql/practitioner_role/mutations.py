"""
Mutation fields for the PractitionerRole resource — same genuinely FHIR
R4-shaped input/output regardless of which connector (internal, medplum,
...) is actually active; each connector's translator maps this shape onto
its own write conventions. Mirrors app.gql.organization.mutations/
app.gql.location.mutations/app.gql.healthcare_service.mutations/
app.gql.practitioner.mutations exactly — see those modules and
app.gql.organization's package docstring, and
app.connectors.base.PractitionerRoleWireTranslator's docstring for why
write translation is NOT a pass-through for `internal` the way reads are.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_practitioner_role_translator
from app.fhir.schemas.practitioner_role import FhirPractitionerRoleResponse
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.practitioner_role.types.input import FhirPractitionerRoleInput
from app.gql.practitioner_role.types.response import FhirPractitionerRoleType


@strawberry.type(description="Mutation fields for the PractitionerRole resource.")
class FhirPractitionerRoleMutation:
    """Mutation fields for the PractitionerRole resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description=(
            "Create a new PractitionerRole from a genuine FHIR R4 payload. "
            "Requires the `practitioner_role:create` permission."
        )
    )
    @translate_errors
    async def create_fhir_practitioner_role(
        self,
        info: strawberry.types.Info,
        input: Annotated[
            FhirPractitionerRoleInput,
            strawberry.argument(
                description="The PractitionerRole to create, in FHIR R4 shape."
            ),
        ],
    ) -> FhirPractitionerRoleType:
        """Create a new PractitionerRole — mirrors POST /PractitionerRole."""
        actor = require_gql_permission(info, "practitioner_role", "create")
        connector = get_container(info).core.fhir_client()
        translator = active_practitioner_role_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.post(
            translator.list_path(),
            translator.to_wire_create(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirPractitionerRoleType.from_pydantic(
            FhirPractitionerRoleResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Partially update a PractitionerRole from a genuine FHIR R4 "
            "payload — only supplied fields are written. Requires the "
            "`practitioner_role:update` permission."
        )
    )
    @translate_errors
    async def update_fhir_practitioner_role(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
        input: Annotated[
            FhirPractitionerRoleInput,
            strawberry.argument(description="Fields to update, in FHIR R4 shape."),
        ],
    ) -> FhirPractitionerRoleType:
        """Update a PractitionerRole by FHIR id — mirrors PATCH /PractitionerRole/{id}."""
        actor = require_gql_permission(info, "practitioner_role", "update")
        connector = get_container(info).core.fhir_client()
        translator = active_practitioner_role_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.patch(
            translator.item_path(id),
            translator.to_wire_patch(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirPractitionerRoleType.from_pydantic(
            FhirPractitionerRoleResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Permanently delete a PractitionerRole by its FHIR resource id. "
            "Irreversible. Requires the `practitioner_role:delete` "
            "permission. Returns true on success."
        )
    )
    @translate_errors
    async def delete_fhir_practitioner_role(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> bool:
        """Delete a PractitionerRole by FHIR id — mirrors DELETE /PractitionerRole/{id}."""
        actor = require_gql_permission(info, "practitioner_role", "delete")
        connector = get_container(info).core.fhir_client()
        translator = active_practitioner_role_translator()
        await connector.delete(translator.item_path(id), actor=actor)
        return True
