"""
Mutation fields for the ServiceRequest resource. Mirrors
app.gql.questionnaire_response.mutations exactly — see that module's
docstring for why `to_wire_create`/`to_wire_patch` take extra keyword-
only arguments here (ServiceRequest is a default/gateway-trusted resource
on fhir-server).
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_service_request_translator
from app.fhir.schemas.service_request import FhirServiceRequestResponse
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission
from app.gql.service_request.types.input import FhirServiceRequestInput
from app.gql.service_request.types.response import FhirServiceRequestType


@strawberry.type(description="Mutation fields for the ServiceRequest resource.")
class FhirServiceRequestMutation:
    """Mutation fields for the ServiceRequest resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description="Create a new ServiceRequest from a genuine FHIR R4 payload. Requires the `service_request:create` permission."
    )
    @translate_errors
    async def create_fhir_service_request(
        self,
        info: strawberry.types.Info,
        input: Annotated[
            FhirServiceRequestInput,
            strawberry.argument(description="The ServiceRequest to create, in FHIR R4 shape."),
        ],
    ) -> FhirServiceRequestType:
        """Create a new ServiceRequest — mirrors POST /ServiceRequest."""
        actor = require_gql_permission(info, "service_request", "create")
        connector = get_container(info).core.fhir_client()
        translator = active_service_request_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.post(
            translator.list_path(),
            translator.to_wire_create(data, tenant_id=actor.org_id, user_id=actor.sub, created_by=actor.sub),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirServiceRequestType.from_pydantic(FhirServiceRequestResponse.model_validate(translator.from_wire(raw)))

    @strawberry.mutation(
        description="Partially update a ServiceRequest from a genuine FHIR R4 payload — only supplied fields are written. Requires the `service_request:update` permission."
    )
    @translate_errors
    async def update_fhir_service_request(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
        input: Annotated[
            FhirServiceRequestInput,
            strawberry.argument(description="Fields to update, in FHIR R4 shape."),
        ],
    ) -> FhirServiceRequestType:
        """Update a ServiceRequest by FHIR id — mirrors PATCH /ServiceRequest/{id}."""
        actor = require_gql_permission(info, "service_request", "update")
        connector = get_container(info).core.fhir_client()
        translator = active_service_request_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.patch(
            translator.item_path(id),
            translator.to_wire_patch(data, updated_by=actor.sub),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirServiceRequestType.from_pydantic(FhirServiceRequestResponse.model_validate(translator.from_wire(raw)))

    @strawberry.mutation(
        description="Permanently delete a ServiceRequest by its FHIR resource id. Irreversible. Requires the `service_request:delete` permission. Returns true on success."
    )
    @translate_errors
    async def delete_fhir_service_request(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> bool:
        """Delete a ServiceRequest by FHIR id — mirrors DELETE /ServiceRequest/{id}."""
        actor = require_gql_permission(info, "service_request", "delete")
        connector = get_container(info).core.fhir_client()
        translator = active_service_request_translator()
        await connector.delete(translator.item_path(id), actor=actor)
        return True
