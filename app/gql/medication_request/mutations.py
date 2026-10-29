"""
Mutation fields for the MedicationRequest resource. fhir-server's own
MedicationRequest is now one of its JWT-auth-rollout resources, so
`org_id`/`created_by`/`updated_by` are derived by fhir-server itself
from the forwarded JWT (via `actor`, passed straight to the connector),
never built into the wire body here. `inject_audit=False` is still
passed, same as every other rolled-out resource's mutations —
InternalConnector's generic actor.sub-only mechanism would otherwise
try to merge `created_by` into a body whose schema no longer accepts
it.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_medication_request_translator
from app.fhir.schemas.medication_request import FhirMedicationRequestResponse
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.medication_request.types.input import FhirMedicationRequestInput
from app.gql.medication_request.types.response import FhirMedicationRequestType
from app.gql.permissions import require_gql_permission


@strawberry.type(description="Mutation fields for the MedicationRequest resource.")
class FhirMedicationRequestMutation:
    """Mutation fields for the MedicationRequest resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description="Create a new MedicationRequest from a genuine FHIR R4 payload. Requires the `medication_request:create` permission."
    )
    @translate_errors
    async def create_fhir_medication_request(
        self,
        info: strawberry.types.Info,
        input: Annotated[
            FhirMedicationRequestInput,
            strawberry.argument(description="The MedicationRequest to create, in FHIR R4 shape."),
        ],
    ) -> FhirMedicationRequestType:
        """Create a new MedicationRequest — mirrors POST /MedicationRequest."""
        actor = require_gql_permission(info, "medication_request", "create")
        connector = get_container(info).core.fhir_client()
        translator = active_medication_request_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.post(
            translator.list_path(),
            translator.to_wire_create(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirMedicationRequestType.from_pydantic(FhirMedicationRequestResponse.model_validate(translator.from_wire(raw)))

    @strawberry.mutation(
        description="Partially update a MedicationRequest from a genuine FHIR R4 payload — only supplied fields are written. Requires the `medication_request:update` permission."
    )
    @translate_errors
    async def update_fhir_medication_request(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
        input: Annotated[
            FhirMedicationRequestInput,
            strawberry.argument(description="Fields to update, in FHIR R4 shape."),
        ],
    ) -> FhirMedicationRequestType:
        """Update a MedicationRequest by FHIR id — mirrors PATCH /MedicationRequest/{id}."""
        actor = require_gql_permission(info, "medication_request", "update")
        connector = get_container(info).core.fhir_client()
        translator = active_medication_request_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.patch(
            translator.item_path(id),
            translator.to_wire_patch(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirMedicationRequestType.from_pydantic(FhirMedicationRequestResponse.model_validate(translator.from_wire(raw)))

    @strawberry.mutation(
        description="Permanently delete a MedicationRequest by its FHIR resource id. Irreversible. Requires the `medication_request:delete` permission. Returns true on success."
    )
    @translate_errors
    async def delete_fhir_medication_request(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> bool:
        """Delete a MedicationRequest by FHIR id — mirrors DELETE /MedicationRequest/{id}."""
        actor = require_gql_permission(info, "medication_request", "delete")
        connector = get_container(info).core.fhir_client()
        translator = active_medication_request_translator()
        await connector.delete(translator.item_path(id), actor=actor)
        return True
