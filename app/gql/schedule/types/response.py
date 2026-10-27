"""
GraphQL object (output) type for the Schedule resource.

One canonical, genuinely FHIR R4-shaped Schedule — the same shape
regardless of which connector (internal, medplum, ...) is actually active;
mirrors app.gql.organization.types.response/app.gql.location.types.response/
app.gql.healthcare_service.types.response/app.gql.practitioner.types.response/
app.gql.practitioner_role.types.response exactly — see those modules and
app.gql.organization's package docstring for the overall idea, and
app.connectors.base.ScheduleWireTranslator for how each connector's own
wire conventions get bridged to this one canonical shape.

Schedule has no resource-specific BackboneElement of its own (unlike
PractitionerRole's availableTime/notAvailable), so there's nothing to
declare before the parent type below — just the shared leaf types already
registered by app.gql.organization.types.response (`FhirCodeableConceptType`,
`FhirIdentifierType`, `FhirReferenceType`, `FhirMetaType`, `FhirPeriodType`).
"""

import strawberry
from strawberry.scalars import JSON

from app.fhir.schemas.schedule import FhirScheduleResponse

# Importing this ensures FhirCodeableConceptType/FhirIdentifierType/
# FhirReferenceType/FhirMetaType/FhirPeriodType are registered before
# FhirScheduleType below — see this module's docstring.
import app.gql.organization.types.response  # noqa: F401


@strawberry.experimental.pydantic.type(
    model=FhirScheduleResponse,
    all_fields=True,
    description=(
        "A full FHIR R4 Schedule resource — the one canonical shape "
        "returned regardless of which connector (internal, medplum, ...) is "
        "active."
    ),
)
class FhirScheduleType:
    """A full FHIR R4 Schedule resource."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar, same as Organization's own extension/assigner fields.
    extension: JSON | None
