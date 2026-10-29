"""
Mutation fields for the QuestionnaireResponse resource — same genuinely
FHIR R4-shaped input/output regardless of which connector (internal,
medplum, ...) is actually active; each connector's translator maps this
shape onto its own write conventions.

QuestionnaireResponse is a default (gateway-trusted) resource on
fhir-server — unlike every other resource this gateway talks to, it was
never asked to get the JWT-auth-rollout treatment (see
app.connectors.internal.translators.questionnaire_response's module
docstring), so fhir-server still expects `tenant_id`/`user_id`/
`created_by`/`updated_by` as plain request-body fields rather than
deriving them from a forwarded JWT itself. `inject_audit=False` is passed
(same as every other resource's mutations) because InternalConnector's own
generic actor.sub-only mechanism only ever injects `created_by`/
`updated_by`, never `tenant_id`/`user_id` — this module builds the wire
body with all four explicitly instead, via `to_wire_create`/
`to_wire_patch`'s extra keyword-only arguments (both connectors' own
translators accept the same extra arguments — Medplum's just discards
them, see its own module docstring — so this call site never needs to
branch on which connector is active).
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
            translator.to_wire_create(
                data, tenant_id=actor.org_id, user_id=actor.sub, created_by=actor.sub
            ),
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
            translator.to_wire_patch(data, updated_by=actor.sub),
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
