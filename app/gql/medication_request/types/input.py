"""
GraphQL input types for the MedicationRequest resource. Mirrors
app.gql.medication_request.types.response's overall pattern — including
exposing every Quantity/Duration-shaped sub-field as raw JSON (see that
module's docstring for the confirmed strawberry nested-pydantic-type
bug this sidesteps). No local `FhirQuantityInput` exists for the same
reason there's no `FhirQuantityType`.
"""

from strawberry.scalars import JSON

import strawberry

from app.fhir.schemas.medication_request import (
    FhirAnnotation,
    FhirMedicationRequestDispenseRequest,
    FhirMedicationRequestDosage,
    FhirMedicationRequestInitialFill,
    FhirMedicationRequestInput as FhirMedicationRequestInputSchema,
    FhirMedicationRequestSubstitution,
)

# Importing this ensures FhirCodeableConceptInput/FhirIdentifierInput/
# FhirReferenceInput/FhirPeriodInput are registered before
# FhirMedicationRequestInput below.
import app.gql.organization.types.input  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.input(
    model=FhirAnnotation,
    all_fields=True,
    description="Input for one FHIR R4 Annotation — MedicationRequest.note entry.",
)
class FhirAnnotationInput:
    """Input for one FHIR R4 Annotation."""


@strawberry.experimental.pydantic.input(
    model=FhirMedicationRequestDosage,
    all_fields=True,
    description="Input for one FHIR R4 Dosage — MedicationRequest.dosageInstruction entry.",
)
class FhirMedicationRequestDosageInput:
    """Input for one FHIR R4 Dosage."""

    timing: JSON | None = None
    doseAndRate: JSON | None = None
    maxDosePerPeriod: JSON | None = None
    maxDosePerAdministration: JSON | None = None
    maxDosePerLifetime: JSON | None = None


@strawberry.experimental.pydantic.input(
    model=FhirMedicationRequestInitialFill,
    all_fields=True,
    description="Input for MedicationRequest.dispenseRequest.initialFill.",
)
class FhirMedicationRequestInitialFillInput:
    """Input for MedicationRequest.dispenseRequest.initialFill."""

    quantity: JSON | None = None
    duration: JSON | None = None


@strawberry.experimental.pydantic.input(
    model=FhirMedicationRequestDispenseRequest,
    all_fields=True,
    description="Input for MedicationRequest.dispenseRequest.",
)
class FhirMedicationRequestDispenseRequestInput:
    """Input for MedicationRequest.dispenseRequest."""

    dispenseInterval: JSON | None = None
    quantity: JSON | None = None
    expectedSupplyDuration: JSON | None = None


@strawberry.experimental.pydantic.input(
    model=FhirMedicationRequestSubstitution,
    all_fields=True,
    description="Input for MedicationRequest.substitution.",
)
class FhirMedicationRequestSubstitutionInput:
    """Input for MedicationRequest.substitution."""


@strawberry.experimental.pydantic.input(
    model=FhirMedicationRequestInputSchema,
    all_fields=True,
    description=(
        "Input for createFhirMedicationRequest/updateFhirMedicationRequest "
        "— a genuine FHIR R4 MedicationRequest shape, translated per-"
        "connector on write."
    ),
)
class FhirMedicationRequestInput:
    """Input for createFhirMedicationRequest/updateFhirMedicationRequest."""

    extension: JSON | None = None
