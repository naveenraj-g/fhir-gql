"""
GraphQL object (output) types for the DiagnosticReport resource. Mirrors
app.gql.observation.types.response's overall pattern — see that module
and app.gql.organization's package docstring for the overall idea.

No recursive types here — every nested type is declared in strict
leaf-first order, so no `strawberry.lazy()` override is needed anywhere.

`FhirCodeableConceptType`, `FhirIdentifierType`, `FhirReferenceType`,
`FhirMetaType`, `FhirPeriodType` are NOT redeclared — reused from
app.gql.organization.types.response. `FhirAttachmentType` is NOT
redeclared either — reused from app.gql.healthcare_service.types.response
(the same shared `FhirAttachment` Pydantic model from
app.fhir.schemas.datatypes).

DiagnosticReport has no Quantity/Range/Ratio/SampledData-shaped fields
at all, so none of the strawberry nested-pydantic-type bug mitigations
app.gql.observation/medication_request needed apply here — every field
is a genuinely typed nested model.
"""

from strawberry.scalars import JSON

import strawberry

from app.fhir.schemas.diagnostic_report import (
    FhirDiagnosticReportMedia,
    FhirDiagnosticReportResponse,
)

# Importing this ensures FhirCodeableConceptType/FhirIdentifierType/
# FhirReferenceType/FhirMetaType/FhirPeriodType are registered before
# FhirDiagnosticReportType below — see this module's docstring.
import app.gql.organization.types.response  # noqa: F401

# Importing this ensures FhirAttachmentType is registered before
# FhirDiagnosticReportType below.
import app.gql.healthcare_service.types.response  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.type(
    model=FhirDiagnosticReportMedia,
    all_fields=True,
    description="DiagnosticReport.media entry — a key image associated with the report.",
)
class FhirDiagnosticReportMediaType:
    """DiagnosticReport.media entry."""


@strawberry.experimental.pydantic.type(
    model=FhirDiagnosticReportResponse,
    all_fields=True,
    description=(
        "A full FHIR R4 DiagnosticReport resource — the one canonical shape "
        "returned regardless of which connector (internal, medplum, ...) is "
        "active."
    ),
)
class FhirDiagnosticReportType:
    """A full FHIR R4 DiagnosticReport resource."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar.
    extension: JSON | None
