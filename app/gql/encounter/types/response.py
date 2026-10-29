"""
GraphQL object (output) types for the Encounter resource.

One canonical, genuinely FHIR R4-shaped Encounter — the same shape
regardless of which connector (internal, medplum, ...) is actually active;
mirrors app.gql.organization.types.response/.../app.gql.appointment_response.types.response
exactly — see those modules and app.gql.organization's package docstring
for the overall idea, and app.connectors.base.EncounterWireTranslator for
how each connector's own wire conventions get bridged to this one
canonical shape.

Declaration order matters for strawberry.experimental.pydantic: leaf types
before the parent model that references them. `FhirCodeableConceptType`,
`FhirIdentifierType`, `FhirReferenceType`, `FhirMetaType`, `FhirPeriodType`,
`FhirCodingType` are NOT redeclared here — they're the exact same leaf
types app.gql.organization.types.response already declares from the exact
same app.fhir.schemas.datatypes models (`FhirCodingType` is used for
Encounter.class/classHistory.class — Encounter is its first consumer, but
the type itself already exists). `FhirDurationType` and the six
`FhirEncounter*Type` BackboneElement types ARE new — Encounter's own
resource-specific shapes, same situation as PractitionerRole's
availableTime/notAvailable or Appointment's participant.

`Encounter.class` is aliased `class_` at the Pydantic layer (Python
reserves `class`) — strawberry's `use_pydantic_alias` (on by default)
exposes it over GraphQL under its real alias, `class`, automatically; no
explicit override needed here, same as fhir-server's own
FHIREncounterSchema's `class_: ... = Field(..., alias="class")` pattern.
"""

import strawberry
from strawberry.scalars import JSON

from app.fhir.schemas.encounter import (
    FhirDuration,
    FhirEncounterClassHistory,
    FhirEncounterDiagnosis,
    FhirEncounterHospitalization,
    FhirEncounterLocation,
    FhirEncounterParticipant,
    FhirEncounterResponse,
    FhirEncounterStatusHistory,
)

# Importing this ensures FhirCodeableConceptType/FhirIdentifierType/
# FhirReferenceType/FhirMetaType/FhirPeriodType/FhirCodingType are
# registered before FhirEncounterType below — see this module's docstring.
import app.gql.organization.types.response  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.type(
    model=FhirDuration,
    all_fields=True,
    description="Encounter.length — how long the encounter lasted.",
)
class FhirDurationType:
    """Encounter.length — how long the encounter lasted."""


@strawberry.experimental.pydantic.type(
    model=FhirEncounterStatusHistory,
    all_fields=True,
    description="One Encounter.statusHistory entry.",
)
class FhirEncounterStatusHistoryType:
    """One Encounter.statusHistory entry."""


@strawberry.experimental.pydantic.type(
    model=FhirEncounterClassHistory,
    all_fields=True,
    description="One Encounter.classHistory entry.",
)
class FhirEncounterClassHistoryType:
    """One Encounter.classHistory entry."""


@strawberry.experimental.pydantic.type(
    model=FhirEncounterParticipant,
    all_fields=True,
    description="One Encounter.participant entry.",
)
class FhirEncounterParticipantType:
    """One Encounter.participant entry."""


@strawberry.experimental.pydantic.type(
    model=FhirEncounterDiagnosis,
    all_fields=True,
    description="One Encounter.diagnosis entry.",
)
class FhirEncounterDiagnosisType:
    """One Encounter.diagnosis entry."""


@strawberry.experimental.pydantic.type(
    model=FhirEncounterHospitalization,
    all_fields=True,
    description="Encounter.hospitalization — details about the admission to a healthcare service.",
)
class FhirEncounterHospitalizationType:
    """Encounter.hospitalization — details about the admission to a healthcare service."""


@strawberry.experimental.pydantic.type(
    model=FhirEncounterLocation,
    all_fields=True,
    description="One Encounter.location entry.",
)
class FhirEncounterLocationType:
    """One Encounter.location entry."""


@strawberry.experimental.pydantic.type(
    model=FhirEncounterResponse,
    all_fields=True,
    description=(
        "A full FHIR R4 Encounter resource — the one canonical shape "
        "returned regardless of which connector (internal, medplum, ...) is "
        "active."
    ),
)
class FhirEncounterType:
    """A full FHIR R4 Encounter resource."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar, same as Organization's own extension/assigner fields.
    extension: JSON | None
