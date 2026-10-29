"""
Mutation fields for the DiagnosticReport resource. fhir-server's own
DiagnosticReport is now one of its JWT-auth-rollout resources, so
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

from app.connectors.translator_registry import active_diagnostic_report_translator
from app.fhir.schemas.diagnostic_report import FhirDiagnosticReportResponse
from app.gql.context import get_container
from app.gql.diagnostic_report.types.input import FhirDiagnosticReportInput
from app.gql.diagnostic_report.types.response import FhirDiagnosticReportType
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission


@strawberry.type(description="Mutation fields for the DiagnosticReport resource.")
class FhirDiagnosticReportMutation:
    """Mutation fields for the DiagnosticReport resource. Mixed into the root `Mutation` type in app/gql/schema.py."""

    @strawberry.mutation(
        description="Create a new DiagnosticReport from a genuine FHIR R4 payload. Requires the `diagnostic_report:create` permission."
    )
    @translate_errors
    async def create_fhir_diagnostic_report(
        self,
        info: strawberry.types.Info,
        input: Annotated[
            FhirDiagnosticReportInput,
            strawberry.argument(description="The DiagnosticReport to create, in FHIR R4 shape."),
        ],
    ) -> FhirDiagnosticReportType:
        """Create a new DiagnosticReport — mirrors POST /DiagnosticReport."""
        actor = require_gql_permission(info, "diagnostic_report", "create")
        connector = get_container(info).core.fhir_client()
        translator = active_diagnostic_report_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.post(
            translator.list_path(),
            translator.to_wire_create(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirDiagnosticReportType.from_pydantic(FhirDiagnosticReportResponse.model_validate(translator.from_wire(raw)))

    @strawberry.mutation(
        description="Partially update a DiagnosticReport from a genuine FHIR R4 payload — only supplied fields are written. Requires the `diagnostic_report:update` permission."
    )
    @translate_errors
    async def update_fhir_diagnostic_report(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
        input: Annotated[
            FhirDiagnosticReportInput,
            strawberry.argument(description="Fields to update, in FHIR R4 shape."),
        ],
    ) -> FhirDiagnosticReportType:
        """Update a DiagnosticReport by FHIR id — mirrors PATCH /DiagnosticReport/{id}."""
        actor = require_gql_permission(info, "diagnostic_report", "update")
        connector = get_container(info).core.fhir_client()
        translator = active_diagnostic_report_translator()
        data = input.to_pydantic().model_dump(exclude_none=True, mode="json")
        raw = await connector.patch(
            translator.item_path(id),
            translator.to_wire_patch(data),
            actor=actor,
            accept=translator.accept,
            inject_audit=False,
        )
        return FhirDiagnosticReportType.from_pydantic(FhirDiagnosticReportResponse.model_validate(translator.from_wire(raw)))

    @strawberry.mutation(
        description="Permanently delete a DiagnosticReport by its FHIR resource id. Irreversible. Requires the `diagnostic_report:delete` permission. Returns true on success."
    )
    @translate_errors
    async def delete_fhir_diagnostic_report(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> bool:
        """Delete a DiagnosticReport by FHIR id — mirrors DELETE /DiagnosticReport/{id}."""
        actor = require_gql_permission(info, "diagnostic_report", "delete")
        connector = get_container(info).core.fhir_client()
        translator = active_diagnostic_report_translator()
        await connector.delete(translator.item_path(id), actor=actor)
        return True
