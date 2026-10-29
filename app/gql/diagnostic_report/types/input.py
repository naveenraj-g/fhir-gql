"""
GraphQL input types for the DiagnosticReport resource. Mirrors
app.gql.diagnostic_report.types.response's overall pattern.
"""

from strawberry.scalars import JSON

import strawberry

from app.fhir.schemas.diagnostic_report import (
    FhirDiagnosticReportInput as FhirDiagnosticReportInputSchema,
    FhirDiagnosticReportMedia,
)

# Importing this ensures FhirCodeableConceptInput/FhirIdentifierInput/
# FhirReferenceInput/FhirPeriodInput are registered before
# FhirDiagnosticReportInput below.
import app.gql.organization.types.input  # noqa: F401

# Importing this ensures FhirAttachmentInput is registered before
# FhirDiagnosticReportInput below.
import app.gql.healthcare_service.types.input  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.input(
    model=FhirDiagnosticReportMedia,
    all_fields=True,
    description="Input for one DiagnosticReport.media entry.",
)
class FhirDiagnosticReportMediaInput:
    """Input for one DiagnosticReport.media entry."""


@strawberry.experimental.pydantic.input(
    model=FhirDiagnosticReportInputSchema,
    all_fields=True,
    description=(
        "Input for createFhirDiagnosticReport/updateFhirDiagnosticReport — "
        "a genuine FHIR R4 DiagnosticReport shape, translated per-connector "
        "on write."
    ),
)
class FhirDiagnosticReportInput:
    """Input for createFhirDiagnosticReport/updateFhirDiagnosticReport."""

    extension: JSON | None = None
