"""
GraphQL input types for the Appointment resource.

Mirrors app.gql.organization.types.input/.../app.gql.practitioner_role.types.input
exactly — see those modules and app.gql.organization's package docstring
for the overall idea. Declaration order matters for
strawberry.experimental.pydantic: leaf types before the parent model that
references them. `FhirCodeableConceptInput`, `FhirIdentifierInput`,
`FhirReferenceInput`, `FhirPeriodInput` are reused from
app.gql.organization.types.input rather than redeclared — Appointment uses
the exact same underlying Pydantic models, so a second
strawberry.experimental.pydantic.input registration for the same model
would conflict rather than add anything. `FhirAppointmentParticipantInput`
IS new — same reasoning as FhirAppointmentParticipantType in response.py.
"""

import strawberry
from strawberry.scalars import JSON

from app.fhir.schemas.appointment import (
    FhirAppointmentInput as FhirAppointmentInputSchema,
    FhirAppointmentParticipant,
)

# Importing this ensures FhirCodeableConceptInput/FhirIdentifierInput/
# FhirReferenceInput/FhirPeriodInput are registered before
# FhirAppointmentInput below — see this module's docstring.
import app.gql.organization.types.input  # noqa: F401

# ── Leaf sub-resources first ─────────────────────────────────────────────────


@strawberry.experimental.pydantic.input(
    model=FhirAppointmentParticipant,
    all_fields=True,
    description="Input for one Appointment.participant entry.",
)
class FhirAppointmentParticipantInput:
    """Input for one Appointment.participant entry."""


@strawberry.experimental.pydantic.input(
    model=FhirAppointmentInputSchema,
    all_fields=True,
    description=(
        "Input for createFhirAppointment/updateFhirAppointment — a genuine "
        "FHIR R4 Appointment shape, translated per-connector on write. See "
        "app.connectors.base.AppointmentWireTranslator."
    ),
)
class FhirAppointmentInput:
    """Input for createFhirAppointment/updateFhirAppointment."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar, same as Organization's own extension/assigner fields.
    extension: JSON | None = None
