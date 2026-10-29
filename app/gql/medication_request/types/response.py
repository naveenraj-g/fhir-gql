"""
GraphQL object (output) types for the MedicationRequest resource. Mirrors
app.gql.service_request.types.response's overall pattern — see that
module and app.gql.organization's package docstring for the overall
idea.

No recursive types here — every nested type is declared in strict
leaf-first order, so no `strawberry.lazy()` override is needed anywhere.

`FhirCodeableConceptType`, `FhirIdentifierType`, `FhirReferenceType`,
`FhirMetaType`, `FhirPeriodType` are NOT redeclared — reused from
app.gql.organization.types.response. `FhirAnnotationType` IS new (local,
duplicate definition — same situation as app.gql.service_request's own
copy).

`dosageInstruction.timing`/`.doseAndRate`/`.maxDosePerPeriod`/
`.maxDosePerAdministration`/`.maxDosePerLifetime`, and every Quantity/
Duration-shaped field on `dispenseRequest`/`dispenseRequest.initialFill`,
are ALL rendered as raw `JSON` — see
app.fhir.schemas.medication_request's module docstring for the confirmed
strawberry nested-pydantic-type bug this sidesteps (two or more sibling
fields of the same wrapped Quantity type within one parent wrapped type
— confirmed live via an actual `createFhirMedicationRequest` call, same
failure mode as ServiceRequest.quantityRatio's numerator/denominator).
There is therefore no local `FhirQuantityType` here at all — every
Quantity-shaped field on this resource has a same-typed sibling
somewhere in its own parent.
"""

from strawberry.scalars import JSON

import strawberry

from app.fhir.schemas.medication_request import (
    FhirAnnotation,
    FhirMedicationRequestDispenseRequest,
    FhirMedicationRequestDosage,
    FhirMedicationRequestInitialFill,
    FhirMedicationRequestResponse,
    FhirMedicationRequestSubstitution,
)

# Importing this ensures FhirCodeableConceptType/FhirIdentifierType/
# FhirReferenceType/FhirMetaType/FhirPeriodType are registered before
# FhirMedicationRequestType below — see this module's docstring.
import app.gql.organization.types.response  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.type(
    model=FhirAnnotation,
    all_fields=True,
    description="FHIR R4 Annotation — MedicationRequest.note entry.",
)
class FhirAnnotationType:
    """FHIR R4 Annotation."""


@strawberry.experimental.pydantic.type(
    model=FhirMedicationRequestDosage,
    all_fields=True,
    description="FHIR R4 Dosage — MedicationRequest.dosageInstruction entry.",
)
class FhirMedicationRequestDosageType:
    """FHIR R4 Dosage."""

    timing: JSON | None
    doseAndRate: JSON | None
    maxDosePerPeriod: JSON | None
    maxDosePerAdministration: JSON | None
    maxDosePerLifetime: JSON | None


@strawberry.experimental.pydantic.type(
    model=FhirMedicationRequestInitialFill,
    all_fields=True,
    description="MedicationRequest.dispenseRequest.initialFill.",
)
class FhirMedicationRequestInitialFillType:
    """MedicationRequest.dispenseRequest.initialFill."""

    quantity: JSON | None
    duration: JSON | None


@strawberry.experimental.pydantic.type(
    model=FhirMedicationRequestDispenseRequest,
    all_fields=True,
    description="MedicationRequest.dispenseRequest.",
)
class FhirMedicationRequestDispenseRequestType:
    """MedicationRequest.dispenseRequest."""

    dispenseInterval: JSON | None
    quantity: JSON | None
    expectedSupplyDuration: JSON | None


@strawberry.experimental.pydantic.type(
    model=FhirMedicationRequestSubstitution,
    all_fields=True,
    description="MedicationRequest.substitution.",
)
class FhirMedicationRequestSubstitutionType:
    """MedicationRequest.substitution."""


@strawberry.experimental.pydantic.type(
    model=FhirMedicationRequestResponse,
    all_fields=True,
    description=(
        "A full FHIR R4 MedicationRequest resource — the one canonical "
        "shape returned regardless of which connector (internal, medplum, "
        "...) is active."
    ),
)
class FhirMedicationRequestType:
    """A full FHIR R4 MedicationRequest resource."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar.
    extension: JSON | None
