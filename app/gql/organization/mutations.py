"""
Mutation fields for the Organization resource — same genuinely FHIR
R4-shaped input/output regardless of which connector (internal, medplum,
...) is actually active; each connector's translator maps this shape onto
its own write conventions. See app.gql.organization's package docstring and
app.connectors.base.OrganizationWireTranslator's docstring for why write
translation is NOT a pass-through for `internal` the way reads are.
"""

from typing import Annotated

import strawberry

from app.connectors.internal.schemas.organization.fhir_schemas import FhirOrgResponse
from app.connectors.translator_registry import active_organization_translator
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.organization.types.input import FhirOrganizationInput
from app.gql.organization.types.response import FhirOrganizationType
from app.gql.permissions import require_gql_permission


@strawberry.type(description="Mutation fields for the Organization resource.")
class FhirOrganizationMutation:
    """Mutation fields for the Organization resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description=(
            "Create a new Organization from a genuine FHIR R4 payload. "
            "Requires the `organization:create` permission."
        )
    )
    @translate_errors
    async def create_fhir_organization(
        self,
        info: strawberry.types.Info,
        input: Annotated[
            FhirOrganizationInput,
            strawberry.argument(
                description="The Organization to create, in FHIR R4 shape."
            ),
        ],
    ) -> FhirOrganizationType:
        """Create a new Organization — mirrors POST /Organization."""
        actor = require_gql_permission(info, "organization", "create")
        connector = get_container(info).core.fhir_client()
        translator = active_organization_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.post(
            translator.list_path(),
            translator.to_wire_create(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirOrganizationType.from_pydantic(
            FhirOrgResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Partially update an Organization from a genuine FHIR R4 "
            "payload — only supplied fields are written. Requires the "
            "`organization:update` permission."
        )
    )
    @translate_errors
    async def update_fhir_organization(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
        input: Annotated[
            FhirOrganizationInput,
            strawberry.argument(description="Fields to update, in FHIR R4 shape."),
        ],
    ) -> FhirOrganizationType:
        """Update an Organization by FHIR id — mirrors PATCH /Organization/{id}."""
        actor = require_gql_permission(info, "organization", "update")
        connector = get_container(info).core.fhir_client()
        translator = active_organization_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.patch(
            translator.item_path(id),
            translator.to_wire_patch(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirOrganizationType.from_pydantic(
            FhirOrgResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Permanently delete an Organization by its FHIR resource id. "
            "Irreversible. Requires the `organization:delete` permission. "
            "Returns true on success."
        )
    )
    @translate_errors
    async def delete_fhir_organization(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> bool:
        """Delete an Organization by FHIR id — mirrors DELETE /Organization/{id}."""
        actor = require_gql_permission(info, "organization", "delete")
        connector = get_container(info).core.fhir_client()
        translator = active_organization_translator()
        await connector.delete(translator.item_path(id), actor=actor)
        return True
