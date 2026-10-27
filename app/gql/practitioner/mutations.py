"""
Mutation fields for the Practitioner resource — same genuinely FHIR
R4-shaped input/output regardless of which connector (internal, medplum,
...) is actually active; each connector's translator maps this shape onto
its own write conventions. Mirrors app.gql.organization.mutations/
app.gql.location.mutations/app.gql.healthcare_service.mutations exactly —
see those modules and app.gql.organization's package docstring, and
app.connectors.base.PractitionerWireTranslator's docstring for why write
translation is NOT a pass-through for `internal` the way reads are.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_practitioner_translator
from app.fhir.schemas.practitioner import FhirPractitionerResponse
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.practitioner.types.input import FhirPractitionerInput
from app.gql.practitioner.types.response import FhirPractitionerType


@strawberry.type(description="Mutation fields for the Practitioner resource.")
class FhirPractitionerMutation:
    """Mutation fields for the Practitioner resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description=(
            "Create a new Practitioner from a genuine FHIR R4 payload. "
            "Requires the `practitioner:create` permission."
        )
    )
    @translate_errors
    async def create_fhir_practitioner(
        self,
        info: strawberry.types.Info,
        input: Annotated[
            FhirPractitionerInput,
            strawberry.argument(
                description="The Practitioner to create, in FHIR R4 shape."
            ),
        ],
    ) -> FhirPractitionerType:
        """Create a new Practitioner — mirrors POST /Practitioner."""
        actor = require_gql_permission(info, "practitioner", "create")
        connector = get_container(info).core.fhir_client()
        translator = active_practitioner_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.post(
            translator.list_path(),
            translator.to_wire_create(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirPractitionerType.from_pydantic(
            FhirPractitionerResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Partially update a Practitioner from a genuine FHIR R4 "
            "payload — only supplied fields are written. Requires the "
            "`practitioner:update` permission."
        )
    )
    @translate_errors
    async def update_fhir_practitioner(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
        input: Annotated[
            FhirPractitionerInput,
            strawberry.argument(description="Fields to update, in FHIR R4 shape."),
        ],
    ) -> FhirPractitionerType:
        """Update a Practitioner by FHIR id — mirrors PATCH /Practitioner/{id}."""
        actor = require_gql_permission(info, "practitioner", "update")
        connector = get_container(info).core.fhir_client()
        translator = active_practitioner_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.patch(
            translator.item_path(id),
            translator.to_wire_patch(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirPractitionerType.from_pydantic(
            FhirPractitionerResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Permanently delete a Practitioner by its FHIR resource id. "
            "Irreversible. Requires the `practitioner:delete` permission. "
            "Returns true on success."
        )
    )
    @translate_errors
    async def delete_fhir_practitioner(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> bool:
        """Delete a Practitioner by FHIR id — mirrors DELETE /Practitioner/{id}."""
        actor = require_gql_permission(info, "practitioner", "delete")
        connector = get_container(info).core.fhir_client()
        translator = active_practitioner_translator()
        await connector.delete(translator.item_path(id), actor=actor)
        return True
