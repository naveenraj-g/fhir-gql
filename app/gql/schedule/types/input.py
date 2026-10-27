"""
GraphQL input type for the Schedule resource.

Mirrors app.gql.organization.types.input/app.gql.location.types.input/
app.gql.healthcare_service.types.input/app.gql.practitioner.types.input/
app.gql.practitioner_role.types.input exactly — see those modules and
app.gql.organization's package docstring for the overall idea.
`FhirCodeableConceptInput`, `FhirIdentifierInput`, `FhirReferenceInput`,
`FhirPeriodInput` are reused from app.gql.organization.types.input rather
than redeclared — Schedule uses the exact same underlying Pydantic models,
so a second strawberry.experimental.pydantic.input registration for the
same model would conflict rather than add anything.
"""

import strawberry
from strawberry.scalars import JSON

from app.fhir.schemas.schedule import FhirScheduleInput as FhirScheduleInputSchema

# Importing this ensures FhirCodeableConceptInput/FhirIdentifierInput/
# FhirReferenceInput/FhirPeriodInput are registered before
# FhirScheduleInput below — see this module's docstring.
import app.gql.organization.types.input  # noqa: F401


@strawberry.experimental.pydantic.input(
    model=FhirScheduleInputSchema,
    all_fields=True,
    description=(
        "Input for createFhirSchedule/updateFhirSchedule — a genuine FHIR "
        "R4 Schedule shape, translated per-connector on write. See "
        "app.connectors.base.ScheduleWireTranslator."
    ),
)
class FhirScheduleInput:
    """Input for createFhirSchedule/updateFhirSchedule."""

    # dict isn't a native GraphQL scalar — must be overridden explicitly as
    # the JSON scalar, same as Organization's own extension/assigner fields.
    extension: JSON | None = None
