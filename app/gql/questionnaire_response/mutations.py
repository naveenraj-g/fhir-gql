"""
Mutation fields for the QuestionnaireResponse resource — same genuinely
FHIR R4-shaped input/output regardless of which connector (internal,
medplum, ...) is actually active; each connector's translator maps this
shape onto its own write conventions.

fhir-server's own QuestionnaireResponse is now one of its JWT-auth-rollout
resources, so `org_id`/`created_by`/`updated_by` are derived by
fhir-server itself from the forwarded JWT (via `actor`, passed straight
to the connector), never built into the wire body here. `inject_audit=False`
is still passed, same as every other rolled-out resource's mutations —
InternalConnector's generic actor.sub-only mechanism would otherwise try
to merge `created_by` into a body whose schema no longer accepts it.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_questionnaire_response_translator
from app.fhir.schemas.questionnaire_response import FhirQuestionnaireResponseResponse
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.questionnaire_response.types.input import FhirQuestionnaireResponseInput
from app.gql.questionnaire_response.types.response import FhirQuestionnaireResponseType


@strawberry.type(description="Mutation fields for the QuestionnaireResponse resource.")
class FhirQuestionnaireResponseMutation:
    """Mutation fields for the QuestionnaireResponse resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description=(
            "Create a new QuestionnaireResponse from a genuine FHIR R4 payload. "
            "Requires the `questionnaire_response:create` permission."
        )
    )
    @translate_errors
    async def create_fhir_questionnaire_response(
        self,
        info: strawberry.types.Info,
        input: Annotated[
            FhirQuestionnaireResponseInput,
            strawberry.argument(
                description="The QuestionnaireResponse to create, in FHIR R4 shape."
            ),
        ],
    ) -> FhirQuestionnaireResponseType:
        """Create a new QuestionnaireResponse — mirrors POST /QuestionnaireResponse."""
        actor = require_gql_permission(info, "questionnaire_response", "create")
        connector = get_container(info).core.fhir_client()
        translator = active_questionnaire_response_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.post(
            translator.list_path(),
            translator.to_wire_create(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirQuestionnaireResponseType.from_pydantic(
            FhirQuestionnaireResponseResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Partially update a QuestionnaireResponse from a genuine FHIR R4 "
            "payload — only supplied fields are written. Requires the "
            "`questionnaire_response:update` permission."
        )
    )
    @translate_errors
    async def update_fhir_questionnaire_response(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
        input: Annotated[
            FhirQuestionnaireResponseInput,
            strawberry.argument(description="Fields to update, in FHIR R4 shape."),
        ],
    ) -> FhirQuestionnaireResponseType:
        """Update a QuestionnaireResponse by FHIR id — mirrors PATCH /QuestionnaireResponse/{id}."""
        actor = require_gql_permission(info, "questionnaire_response", "update")
        connector = get_container(info).core.fhir_client()
        translator = active_questionnaire_response_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.patch(
            translator.item_path(id),
            translator.to_wire_patch(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirQuestionnaireResponseType.from_pydantic(
            FhirQuestionnaireResponseResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Permanently delete a QuestionnaireResponse by its FHIR resource id. "
            "Irreversible. Requires the `questionnaire_response:delete` permission. "
            "Returns true on success."
        )
    )
    @translate_errors
    async def delete_fhir_questionnaire_response(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> bool:
        """Delete a QuestionnaireResponse by FHIR id — mirrors DELETE /QuestionnaireResponse/{id}."""
        actor = require_gql_permission(info, "questionnaire_response", "delete")
        connector = get_container(info).core.fhir_client()
        translator = active_questionnaire_response_translator()
        await connector.delete(translator.item_path(id), actor=actor)
        return True
