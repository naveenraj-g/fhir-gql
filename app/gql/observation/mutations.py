"""
Mutation fields for the Observation resource. Mirrors
app.gql.medication_request.mutations exactly — see that module's
docstring for why `to_wire_create`/`to_wire_patch` take extra
keyword-only arguments here (Observation is a default/gateway-trusted
resource on fhir-server).
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_observation_translator
from app.fhir.schemas.observation import FhirObservationResponse
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.observation.types.input import FhirObservationInput
from app.gql.observation.types.response import FhirObservationType
from app.gql.permissions import require_gql_permission


@strawberry.type(description="Mutation fields for the Observation resource.")
class FhirObservationMutation:
    """Mutation fields for the Observation resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description="Create a new Observation from a genuine FHIR R4 payload. Requires the `observation:create` permission."
    )
    @translate_errors
    async def create_fhir_observation(
        self,
        info: strawberry.types.Info,
        input: Annotated[
            FhirObservationInput,
            strawberry.argument(description="The Observation to create, in FHIR R4 shape."),
        ],
    ) -> FhirObservationType:
        """Create a new Observation — mirrors POST /Observation."""
        actor = require_gql_permission(info, "observation", "create")
        connector = get_container(info).core.fhir_client()
        translator = active_observation_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.post(
            translator.list_path(),
            translator.to_wire_create(data, tenant_id=actor.org_id, user_id=actor.sub, created_by=actor.sub),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirObservationType.from_pydantic(FhirObservationResponse.model_validate(translator.from_wire(raw)))

    @strawberry.mutation(
        description="Partially update an Observation from a genuine FHIR R4 payload — only supplied fields are written. Requires the `observation:update` permission."
    )
    @translate_errors
    async def update_fhir_observation(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
        input: Annotated[
            FhirObservationInput,
            strawberry.argument(description="Fields to update, in FHIR R4 shape."),
        ],
    ) -> FhirObservationType:
        """Update an Observation by FHIR id — mirrors PATCH /Observation/{id}."""
        actor = require_gql_permission(info, "observation", "update")
        connector = get_container(info).core.fhir_client()
        translator = active_observation_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.patch(
            translator.item_path(id),
            translator.to_wire_patch(data, updated_by=actor.sub),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirObservationType.from_pydantic(FhirObservationResponse.model_validate(translator.from_wire(raw)))

    @strawberry.mutation(
        description="Permanently delete an Observation by its FHIR resource id. Irreversible. Requires the `observation:delete` permission. Returns true on success."
    )
    @translate_errors
    async def delete_fhir_observation(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> bool:
        """Delete an Observation by FHIR id — mirrors DELETE /Observation/{id}."""
        actor = require_gql_permission(info, "observation", "delete")
        connector = get_container(info).core.fhir_client()
        translator = active_observation_translator()
        await connector.delete(translator.item_path(id), actor=actor)
        return True
