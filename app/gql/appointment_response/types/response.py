"""
GraphQL object (output) type for the AppointmentResponse resource.

One canonical, genuinely FHIR R4-shaped AppointmentResponse — the same
shape regardless of which connector (internal, medplum, ...) is actually
active; mirrors app.gql.organization.types.response/.../
app.gql.slot.types.response exactly — see those modules and
app.gql.organization's package docstring for the overall idea, and
app.connectors.base.AppointmentResponseWireTranslator for how each
connector's own wire conventions get bridged to this one canonical shape.

AppointmentResponse has no resource-specific BackboneElement of its own
(same as Schedule/Slot), so there's nothing to declare before the parent
type below — just the shared leaf types already registered by
app.gql.organization.types.response (`FhirCodeableConceptType`,
`FhirIdentifierType`, `FhirReferenceType`, `FhirMetaType`).
"""

import strawberry
from strawberry.scalars import JSON

from app.fhir.schemas.appointment_response import FhirAppointmentResponseResponse

# Importing this ensures FhirCodeableConceptType/FhirIdentifierType/
# FhirReferenceType/FhirMetaType are registered before
# FhirAppointmentResponseType below — see this module's docstring.
import app.gql.organization.types.response  # noqa: F401


@strawberry.experimental.pydantic.type(
    model=FhirAppointmentResponseResponse,
    all_fields=True,
    description=(
        "A full FHIR R4 AppointmentResponse resource — the one canonical "
        "shape returned regardless of which connector (internal, medplum, "
        "...) is active."
    ),
)
class FhirAppointmentResponseType:
    """A full FHIR R4 AppointmentResponse resource."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar, same as Organization's own extension/assigner fields.
    extension: JSON | None
