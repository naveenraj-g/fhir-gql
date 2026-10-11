"""
GraphQL input types for the PractitionerRole resource, derived from the
Pydantic schemas in the app/schemas/practitioner_role/input/ package via
`strawberry.experimental.pydantic`. Output types live in
app/gql/practitioner_role/types/response.py.

Naming convention:
  - Pydantic input schemas that already share a name with the GraphQL
    wrapper class defined here are imported under a `...Schema` alias so
    the plain name is free for this module's GraphQL class — same
    collision-handling pattern used for Organization/Location/
    HealthcareService.

NOTE: `PractitionerRoleCharacteristicInput`, `PractitionerRoleCommunicationInput`,
`PractitionerRoleContactInput` (+ its nested name/telecom types), and the
`PractitionerRoleAvailabilityInput` wrapper group are GONE — none of those
exist on the FHIR R4 PractitionerRole resource (see
app/schemas/practitioner_role/input/core.py's docstring for the full
explanation). `PractitionerRoleTelecomInput` (top-level, not nested) and
flat `PractitionerRoleAvailableTimeInput`/`PractitionerRoleNotAvailableInput`
lists are the correct R4 shape and replace them.

Declaration order matters — leaf sub-resource input types are declared
first, `PractitionerRoleCreateInput`/`PractitionerRolePatchInput` last.
"""

import strawberry

# Registers ContactPointSystem/IdentifierUse/DayOfWeek/etc. as GraphQL
# enums (side-effect import) — required before wrapping any input schema
# whose fields use them.
import app.gql.enums  # noqa: F401
from app.schemas.practitioner_role.input import (
    PractitionerRoleAvailableTimeInput as PractitionerRoleAvailableTimeInputSchema,
)
from app.schemas.practitioner_role.input import (
    PractitionerRoleCodeInput as PractitionerRoleCodeInputSchema,
)
from app.schemas.practitioner_role.input import (
    PractitionerRoleCreateSchema,
    PractitionerRolePatchSchema,
)
from app.schemas.practitioner_role.input import (
    PractitionerRoleEndpointInput as PractitionerRoleEndpointInputSchema,
)
from app.schemas.practitioner_role.input import (
    PractitionerRoleHealthcareServiceInput as PractitionerRoleHealthcareServiceInputSchema,
)
from app.schemas.practitioner_role.input import (
    PractitionerRoleIdentifierInput as PractitionerRoleIdentifierInputSchema,
)
from app.schemas.practitioner_role.input import (
    PractitionerRoleLocationInput as PractitionerRoleLocationInputSchema,
)
from app.schemas.practitioner_role.input import (
    PractitionerRoleNotAvailableInput as PractitionerRoleNotAvailableInputSchema,
)
from app.schemas.practitioner_role.input import (
    PractitionerRoleSpecialtyInput as PractitionerRoleSpecialtyInputSchema,
)
from app.schemas.practitioner_role.input import (
    PractitionerRoleTelecomInput as PractitionerRoleTelecomInputSchema,
)

# ── Input types — leaf sub-resources first ───────────────────────────────────


@strawberry.experimental.pydantic.input(
    model=PractitionerRoleIdentifierInputSchema,
    all_fields=True,
    description="Input for one PractitionerRole.identifier entry.",
)
class PractitionerRoleIdentifierInput:
    """Input for one PractitionerRole.identifier entry."""


@strawberry.experimental.pydantic.input(
    model=PractitionerRoleCodeInputSchema,
    all_fields=True,
    description="Input for one PractitionerRole.code entry.",
)
class PractitionerRoleCodeInput:
    """Input for one PractitionerRole.code entry."""


@strawberry.experimental.pydantic.input(
    model=PractitionerRoleSpecialtyInputSchema,
    all_fields=True,
    description="Input for one PractitionerRole.specialty entry.",
)
class PractitionerRoleSpecialtyInput:
    """Input for one PractitionerRole.specialty entry."""


@strawberry.experimental.pydantic.input(
    model=PractitionerRoleLocationInputSchema,
    all_fields=True,
    description="Input for one PractitionerRole.location reference. Validated server-side on create/update.",
)
class PractitionerRoleLocationInput:
    """Input for one PractitionerRole.location reference."""


@strawberry.experimental.pydantic.input(
    model=PractitionerRoleHealthcareServiceInputSchema,
    all_fields=True,
    description="Input for one PractitionerRole.healthcareService reference. Validated server-side on create/update.",
)
class PractitionerRoleHealthcareServiceInput:
    """Input for one PractitionerRole.healthcareService reference."""


@strawberry.experimental.pydantic.input(
    model=PractitionerRoleTelecomInputSchema,
    all_fields=True,
    description="Input for one PractitionerRole.telecom entry. `system` and `value` are required.",
)
class PractitionerRoleTelecomInput:
    """Input for one PractitionerRole.telecom entry."""


@strawberry.experimental.pydantic.input(
    model=PractitionerRoleAvailableTimeInputSchema,
    all_fields=True,
    description="Input for one PractitionerRole.availableTime entry.",
)
class PractitionerRoleAvailableTimeInput:
    """Input for one PractitionerRole.availableTime entry."""


@strawberry.experimental.pydantic.input(
    model=PractitionerRoleNotAvailableInputSchema,
    all_fields=True,
    description="Input for one PractitionerRole.notAvailable entry. `description` is required.",
)
class PractitionerRoleNotAvailableInput:
    """Input for one PractitionerRole.notAvailable entry."""


@strawberry.experimental.pydantic.input(
    model=PractitionerRoleEndpointInputSchema,
    all_fields=True,
    description="Input for one PractitionerRole.endpoint reference. Not validated (no Endpoint resource in this system).",
)
class PractitionerRoleEndpointInput:
    """Input for one PractitionerRole.endpoint reference."""


@strawberry.experimental.pydantic.input(
    model=PractitionerRoleCreateSchema,
    all_fields=True,
    description=(
        "Input for `createPractitionerRole`. Creates a PractitionerRole and any combination "
        "of its sub-resources (identifier, code, specialty, location, healthcareService, "
        "telecom, availableTime, notAvailable, endpoint) atomically in one request. If "
        "`practitioner`/`organization` are set, fhir-server validates each exists and "
        "belongs to the caller's own tenant; each `location`/`healthcareService` entry is "
        "validated the same way. `orgId`/`createdBy` are derived from the caller's JWT — "
        "do not supply them (not declared on this input type at all)."
    ),
)
class PractitionerRoleCreateInput:
    """Input for `createPractitionerRole` — mirrors PractitionerRoleCreateSchema exactly."""


@strawberry.experimental.pydantic.input(
    model=PractitionerRolePatchSchema,
    all_fields=True,
    description=(
        "Input for `updatePractitionerRole`. Only supplied fields are written; every "
        "supplied sub-resource list (even `[]`) replaces the corresponding rows wholesale. "
        "`practitioner`/`organization` may be set to null to clear the reference; "
        "fhir-server re-validates them (and every `location`/`healthcareService` entry) "
        "server-side whenever supplied. `updatedBy` is derived from the caller's JWT — do "
        "not supply it."
    ),
)
class PractitionerRolePatchInput:
    """Input for `updatePractitionerRole` — every field optional, at least one must be set."""


# `ListPractitionerRolesSchema` is a query-parameter schema, not a mutation
# payload — GraphQL convention is to expose filters via
# PractitionerRoleFilterInput (app/gql/practitioner_role/types/filter.py)
# rather than a wrapped input type here. See
# app/gql/practitioner_role/queries.py, which imports ListPractitionerRolesSchema
# directly from app.schemas.practitioner_role.input.
__all__ = [
    "PractitionerRoleAvailableTimeInput",
    "PractitionerRoleCodeInput",
    "PractitionerRoleCreateInput",
    "PractitionerRoleEndpointInput",
    "PractitionerRoleHealthcareServiceInput",
    "PractitionerRoleIdentifierInput",
    "PractitionerRoleLocationInput",
    "PractitionerRoleNotAvailableInput",
    "PractitionerRolePatchInput",
    "PractitionerRoleSpecialtyInput",
    "PractitionerRoleTelecomInput",
]
