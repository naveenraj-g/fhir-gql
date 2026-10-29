"""
Query fields for the DiagnosticReport resource — one canonical,
genuinely FHIR R4-shaped DiagnosticReport regardless of which connector
(internal, medplum, ...) is actually active. Mirrors
app.gql.observation.queries exactly.
"""

from typing import Annotated

import strawberry

from app.connectors.translator_registry import active_diagnostic_report_translator
from app.fhir.schemas.diagnostic_report import FhirDiagnosticReportResponse
from app.gql.context import get_container
from app.gql.diagnostic_report.types.response import FhirDiagnosticReportType
from app.gql.errors import translate_errors
from app.gql.permissions import require_gql_permission


def _entries_from_bundle(bundle: dict) -> list[dict]:
    if bundle.get("resourceType") == "Bundle":
        return [entry["resource"] for entry in bundle.get("entry") or []]
    return [bundle]


@strawberry.type(description="Query fields for the DiagnosticReport resource.")
class FhirDiagnosticReportQuery:
    """Query fields for the DiagnosticReport resource. Mixed into the root `Query` type in app/gql/schema.py."""

    @strawberry.field(
        description="Fetch a single DiagnosticReport by its FHIR resource id, in genuine FHIR R4 shape. Requires the `diagnostic_report:read` permission."
    )
    @translate_errors
    async def get_fhir_diagnostic_report(
        self,
        info: strawberry.types.Info,
        id: Annotated[str, strawberry.argument(description="FHIR resource id.")],
    ) -> FhirDiagnosticReportType:
        """Fetch a single DiagnosticReport by FHIR id — mirrors GET /DiagnosticReport/{id}."""
        actor = require_gql_permission(info, "diagnostic_report", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_diagnostic_report_translator()
        raw = await connector.get(translator.item_path(id), accept=translator.accept, actor=actor)
        data = translator.from_wire(raw)
        return FhirDiagnosticReportType.from_pydantic(FhirDiagnosticReportResponse.model_validate(data))

    @strawberry.field(
        description=(
            "Search DiagnosticReports, in genuine FHIR R4 shape, with a "
            "subset of the FHIR R4 DiagnosticReport search parameters "
            "(https://hl7.org/fhir/R4/diagnosticreport.html#search) — "
            "status, subject, identifier — plus limit/offset pagination. "
            "Always scoped to the caller's own org, derived from the "
            "forwarded JWT — not a client-suppliable filter. Requires "
            "the `diagnostic_report:read` permission."
        )
    )
    @translate_errors
    async def get_fhir_diagnostic_reports(
        self,
        info: strawberry.types.Info,
        status: Annotated[
            str | None,
            strawberry.argument(description="registered | partial | preliminary | final | amended | corrected | appended | cancelled | entered-in-error | unknown."),
        ] = None,
        subject: Annotated[
            str | None, strawberry.argument(description="Exact match on the subject reference string.")
        ] = None,
        identifier: Annotated[
            str | None, strawberry.argument(description="Exact match on a business identifier value.")
        ] = None,
        limit: Annotated[int, strawberry.argument(description="Max results (default 50).")] = 50,
        offset: Annotated[int, strawberry.argument(description="Pagination offset (default 0).")] = 0,
    ) -> list[FhirDiagnosticReportType]:
        """Search DiagnosticReports — mirrors GET /DiagnosticReport?status=...&subject=..."""
        actor = require_gql_permission(info, "diagnostic_report", "read")
        connector = get_container(info).core.fhir_client()
        translator = active_diagnostic_report_translator()
        params = translator.list_params(status, subject, identifier, limit, offset)
        raw = await connector.get(translator.list_path(), params=params, accept=translator.accept, actor=actor)
        resources = _entries_from_bundle(translator.from_wire(raw))
        return [FhirDiagnosticReportType.from_pydantic(FhirDiagnosticReportResponse.model_validate(r)) for r in resources]
