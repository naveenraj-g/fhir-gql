"""
GraphQL input types for the Encounter resource.

Mirrors app.gql.organization.types.input/.../app.gql.appointment_response.types.input
exactly — see those modules and app.gql.organization's package docstring
for the overall idea. Declaration order matters for
strawberry.experimental.pydantic: leaf types before the parent model that
references them. `FhirCodeableConceptInput`, `FhirIdentifierInput`,
`FhirReferenceInput`, `FhirPeriodInput`, `FhirCodingInput` are reused from
app.gql.organization.types.input rather than redeclared — Encounter uses
the exact same underlying Pydantic models, so a second
strawberry.experimental.pydantic.input registration for the same model
would conflict rather than add anything. `FhirDurationInput` and the six
`FhirEncounter*Input` BackboneElement input types ARE new — same reasoning
as the *Type leaf classes in response.py.
"""

import strawberry
from strawberry.scalars import JSON

from app.fhir.schemas.encounter import (
    FhirDuration,
    FhirEncounterClassHistory,
    FhirEncounterDiagnosis,
    FhirEncounterHospitalization,
    FhirEncounterInput as FhirEncounterInputSchema,
    FhirEncounterLocation,
    FhirEncounterParticipant,
    FhirEncounterStatusHistory,
)

# Importing this ensures FhirCodeableConceptInput/FhirIdentifierInput/
# FhirReferenceInput/FhirPeriodInput/FhirCodingInput are registered before
# FhirEncounterInput below — see this module's docstring.
import app.gql.organization.types.input  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.input(
    model=FhirDuration,
    all_fields=True,
    description="Input for Encounter.length.",
)
class FhirDurationInput:
    """Input for Encounter.length."""


@strawberry.experimental.pydantic.input(
    model=FhirEncounterStatusHistory,
    all_fields=True,
    description="Input for one Encounter.statusHistory entry.",
)
class FhirEncounterStatusHistoryInput:
    """Input for one Encounter.statusHistory entry."""


@strawberry.experimental.pydantic.input(
    model=FhirEncounterClassHistory,
    all_fields=True,
    description="Input for one Encounter.classHistory entry.",
)
class FhirEncounterClassHistoryInput:
    """Input for one Encounter.classHistory entry."""


@strawberry.experimental.pydantic.input(
    model=FhirEncounterParticipant,
    all_fields=True,
    description="Input for one Encounter.participant entry.",
)
class FhirEncounterParticipantInput:
    """Input for one Encounter.participant entry."""


@strawberry.experimental.pydantic.input(
    model=FhirEncounterDiagnosis,
    all_fields=True,
    description="Input for one Encounter.diagnosis entry.",
)
class FhirEncounterDiagnosisInput:
    """Input for one Encounter.diagnosis entry."""


@strawberry.experimental.pydantic.input(
    model=FhirEncounterHospitalization,
    all_fields=True,
    description="Input for Encounter.hospitalization.",
)
class FhirEncounterHospitalizationInput:
    """Input for Encounter.hospitalization."""


@strawberry.experimental.pydantic.input(
    model=FhirEncounterLocation,
    all_fields=True,
    description="Input for one Encounter.location entry.",
)
class FhirEncounterLocationInput:
    """Input for one Encounter.location entry."""


@strawberry.experimental.pydantic.input(
    model=FhirEncounterInputSchema,
    all_fields=True,
    description=(
        "Input for createFhirEncounter/updateFhirEncounter — a genuine "
        "FHIR R4 Encounter shape, translated per-connector on write. See "
        "app.connectors.base.EncounterWireTranslator."
    ),
)
class FhirEncounterInput:
    """Input for createFhirEncounter/updateFhirEncounter."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar, same as Organization's own extension/assigner fields.
    extension: JSON | None = None
