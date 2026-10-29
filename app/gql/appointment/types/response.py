"""
GraphQL object (output) types for the Appointment resource.

One canonical, genuinely FHIR R4-shaped Appointment — the same shape
regardless of which connector (internal, medplum, ...) is actually active;
mirrors app.gql.organization.types.response/.../app.gql.practitioner_role.types.response
exactly — see those modules and app.gql.organization's package docstring
for the overall idea, and app.connectors.base.AppointmentWireTranslator
for how each connector's own wire conventions get bridged to this one
canonical shape.

Declaration order matters for strawberry.experimental.pydantic: leaf types
before the parent model that references them. `FhirCodeableConceptType`,
`FhirIdentifierType`, `FhirReferenceType`, `FhirMetaType`, `FhirPeriodType`
are NOT redeclared here — they're the exact same leaf types
app.gql.organization.types.response already declares from the exact same
app.fhir.schemas.datatypes models. `FhirAppointmentParticipantType` IS new
— `participant` is Appointment's own resource-specific BackboneElement
(the first one in this repo not built from shared datatypes alone), same
situation as PractitionerRole's availableTime/notAvailable.
"""

import strawberry
from strawberry.scalars import JSON

from app.fhir.schemas.appointment import (
    FhirAppointmentParticipant,
    FhirAppointmentResponse,
)

# Importing this ensures FhirCodeableConceptType/FhirIdentifierType/
# FhirReferenceType/FhirMetaType/FhirPeriodType are registered before
# FhirAppointmentType below — see this module's docstring.
import app.gql.organization.types.response  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.type(
    model=FhirAppointmentParticipant,
    all_fields=True,
    description="One Appointment.participant entry.",
)
class FhirAppointmentParticipantType:
    """One Appointment.participant entry."""


@strawberry.experimental.pydantic.type(
    model=FhirAppointmentResponse,
    all_fields=True,
    description=(
        "A full FHIR R4 Appointment resource — the one canonical shape "
        "returned regardless of which connector (internal, medplum, ...) is "
        "active."
    ),
)
class FhirAppointmentType:
    """A full FHIR R4 Appointment resource."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar, same as Organization's own extension/assigner fields.
    extension: JSON | None
