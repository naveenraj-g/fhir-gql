"""
Mutation fields for the Questionnaire resource — same genuinely FHIR
R4-shaped input/output regardless of which connector (internal, medplum,
...) is actually active; each connector's translator maps this shape onto
its own write conventions. Mirrors app.gql.practitioner.mutations exactly
— fhir-server's own Questionnaire is now one of its JWT-auth-rollout
resources, so `org_id`/`created_by`/`updated_by` are derived by
fhir-server itself from the forwarded JWT (via `actor`, passed straight
to the connector), never built into the wire body here. `inject_audit=False`
is still passed, same as every other rolled-out resource's mutations —
InternalConnector's generic actor.sub-only mechanism would otherwise try
to merge `created_by` into a body whose schema no longer accepts it.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_questionnaire_translator
from app.fhir.schemas.questionnaire import FhirQuestionnaireResponse
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.questionnaire.types.input import FhirQuestionnaireInput
from app.gql.questionnaire.types.response import FhirQuestionnaireType


@strawberry.type(description="Mutation fields for the Questionnaire resource.")
class FhirQuestionnaireMutation:
    """Mutation fields for the Questionnaire resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description=(
            "Create a new Questionnaire from a genuine FHIR R4 payload. "
            "Requires the `questionnaire:create` permission."
        )
    )
    @translate_errors
    async def create_fhir_questionnaire(
        self,
        info: strawberry.types.Info,
        input: Annotated[
            FhirQuestionnaireInput,
            strawberry.argument(
                description="The Questionnaire to create, in FHIR R4 shape."
            ),
        ],
    ) -> FhirQuestionnaireType:
        """Create a new Questionnaire — mirrors POST /Questionnaire."""
        actor = require_gql_permission(info, "questionnaire", "create")
        connector = get_container(info).core.fhir_client()
        translator = active_questionnaire_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.post(
            translator.list_path(),
            translator.to_wire_create(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirQuestionnaireType.from_pydantic(
            FhirQuestionnaireResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Partially update a Questionnaire from a genuine FHIR R4 "
            "payload — only supplied fields are written. Requires the "
            "`questionnaire:update` permission."
        )
    )
    @translate_errors
    async def update_fhir_questionnaire(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
        input: Annotated[
            FhirQuestionnaireInput,
            strawberry.argument(description="Fields to update, in FHIR R4 shape."),
        ],
    ) -> FhirQuestionnaireType:
        """Update a Questionnaire by FHIR id — mirrors PATCH /Questionnaire/{id}."""
        actor = require_gql_permission(info, "questionnaire", "update")
        connector = get_container(info).core.fhir_client()
        translator = active_questionnaire_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.patch(
            translator.item_path(id),
            translator.to_wire_patch(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirQuestionnaireType.from_pydantic(
            FhirQuestionnaireResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Permanently delete a Questionnaire by its FHIR resource id. "
            "Irreversible. Requires the `questionnaire:delete` permission. "
            "Returns true on success."
        )
    )
    @translate_errors
    async def delete_fhir_questionnaire(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> bool:
        """Delete a Questionnaire by FHIR id — mirrors DELETE /Questionnaire/{id}."""
        actor = require_gql_permission(info, "questionnaire", "delete")
        connector = get_container(info).core.fhir_client()
        translator = active_questionnaire_translator()
        await connector.delete(translator.item_path(id), actor=actor)
        return True
