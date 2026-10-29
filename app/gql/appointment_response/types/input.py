"""
GraphQL input type for the AppointmentResponse resource.

Mirrors app.gql.organization.types.input/.../app.gql.slot.types.input
exactly — see those modules and app.gql.organization's package docstring
for the overall idea. `FhirCodeableConceptInput`, `FhirIdentifierInput`,
`FhirReferenceInput` are reused from app.gql.organization.types.input
rather than redeclared — AppointmentResponse uses the exact same
underlying Pydantic models, so a second
strawberry.experimental.pydantic.input registration for the same model
would conflict rather than add anything.
"""

import strawberry
from strawberry.scalars import JSON

from app.fhir.schemas.appointment_response import (
    FhirAppointmentResponseInput as FhirAppointmentResponseInputSchema,
)

# Importing this ensures FhirCodeableConceptInput/FhirIdentifierInput/
# FhirReferenceInput are registered before FhirAppointmentResponseInput
# below — see this module's docstring.
import app.gql.organization.types.input  # noqa: F401


@strawberry.experimental.pydantic.input(
    model=FhirAppointmentResponseInputSchema,
    all_fields=True,
    description=(
        "Input for createFhirAppointmentResponse/updateFhirAppointmentResponse "
        "— a genuine FHIR R4 AppointmentResponse shape, translated "
        "per-connector on write. See "
        "app.connectors.base.AppointmentResponseWireTranslator."
    ),
)
class FhirAppointmentResponseInput:
    """Input for createFhirAppointmentResponse/updateFhirAppointmentResponse."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar, same as Organization's own extension/assigner fields.
    extension: JSON | None = None
