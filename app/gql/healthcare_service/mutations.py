"""
Mutation fields for the HealthcareService resource — same genuinely FHIR
R4-shaped input/output regardless of which connector (internal, medplum,
...) is actually active; each connector's translator maps this shape onto
its own write conventions. Mirrors app.gql.organization.mutations/
app.gql.location.mutations exactly — see those modules and
app.gql.organization's package docstring, and
app.connectors.base.HealthcareServiceWireTranslator's docstring for why
write translation is NOT a pass-through for `internal` the way reads are.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_healthcare_service_translator
from app.fhir.schemas.healthcare_service import FhirHealthcareServiceResponse
from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.healthcare_service.types.input import FhirHealthcareServiceInput
from app.gql.healthcare_service.types.response import FhirHealthcareServiceType
from app.gql.permissions import require_gql_permission


@strawberry.type(description="Mutation fields for the HealthcareService resource.")
class FhirHealthcareServiceMutation:
    """Mutation fields for the HealthcareService resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description=(
            "Create a new HealthcareService from a genuine FHIR R4 payload. "
            "Requires the `healthcare_service:create` permission."
        )
    )
    @translate_errors
    async def create_fhir_healthcare_service(
        self,
        info: strawberry.types.Info,
        input: Annotated[
            FhirHealthcareServiceInput,
            strawberry.argument(
                description="The HealthcareService to create, in FHIR R4 shape."
            ),
        ],
    ) -> FhirHealthcareServiceType:
        """Create a new HealthcareService — mirrors POST /HealthcareService."""
        actor = require_gql_permission(info, "healthcare_service", "create")
        connector = get_container(info).core.fhir_client()
        translator = active_healthcare_service_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.post(
            translator.list_path(),
            translator.to_wire_create(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirHealthcareServiceType.from_pydantic(
            FhirHealthcareServiceResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Partially update a HealthcareService from a genuine FHIR R4 "
            "payload — only supplied fields are written. Requires the "
            "`healthcare_service:update` permission."
        )
    )
    @translate_errors
    async def update_fhir_healthcare_service(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
        input: Annotated[
            FhirHealthcareServiceInput,
            strawberry.argument(description="Fields to update, in FHIR R4 shape."),
        ],
    ) -> FhirHealthcareServiceType:
        """Update a HealthcareService by FHIR id — mirrors PATCH /HealthcareService/{id}."""
        actor = require_gql_permission(info, "healthcare_service", "update")
        connector = get_container(info).core.fhir_client()
        translator = active_healthcare_service_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.patch(
            translator.item_path(id),
            translator.to_wire_patch(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirHealthcareServiceType.from_pydantic(
            FhirHealthcareServiceResponse.model_validate(translator.from_wire(raw))
        )

    @strawberry.mutation(
        description=(
            "Permanently delete a HealthcareService by its FHIR resource "
            "id. Irreversible. Requires the `healthcare_service:delete` "
            "permission. Returns true on success."
        )
    )
    @translate_errors
    async def delete_fhir_healthcare_service(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> bool:
        """Delete a HealthcareService by FHIR id — mirrors DELETE /HealthcareService/{id}."""
        actor = require_gql_permission(info, "healthcare_service", "delete")
        connector = get_container(info).core.fhir_client()
        translator = active_healthcare_service_translator()
        await connector.delete(translator.item_path(id), actor=actor)
        return True
