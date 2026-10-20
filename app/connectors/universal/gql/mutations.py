"""
Mutation fields for the universal-FHIR-GraphQL experiment's Organization
resource. See app.connectors.universal's package docstring for the overall
idea, and app.connectors.universal.translators's module docstring for why
write translation is NOT a pass-through for `internal` the way reads are.
"""

from typing import Annotated

import strawberry

from app.connectors.universal.gql.types import (
    FhirOrganizationInput,
    FhirOrganizationType,
)
from app.connectors.universal.schemas import FhirOrgResponse
from app.connectors.universal.translators import active_organization_translator
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission


@strawberry.type(
    description=(
        "EXPERIMENTAL — universal FHIR Organization mutations. Same "
        "genuinely FHIR R4-shaped input/output regardless of which "
        "connector (connectors.active) actually serves it; each connector's "
        "translator maps this shape onto its own write conventions. See "
        "dev-docs/18-universal-fhir-graphql-experiment.md."
    )
)
class FhirOrganizationMutation:
    """Root mutation mixin for the universal-FHIR-GraphQL experiment. Mixed
    into the root `Mutation` type in app/connectors/universal/schema.py."""

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
