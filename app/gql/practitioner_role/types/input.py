"""
GraphQL input types for the PractitionerRole resource, derived from the
existing Pydantic schemas in app/schemas/practitioner_role/input.py via
`strawberry.experimental.pydantic`. Output types live in
app/gql/practitioner_role/types/types.py.

Naming convention:
  - `<X>Input` (Pydantic, all of PractitionerRole's sub-resource input
    schemas already end in "Input" — unlike Practitioner's "CreateSchema"/
    "PatchSchema" convention) are imported under a `...Schema` alias so the
    plain name is free for this module's GraphQL wrapper class, same
    collision-handling pattern used for Organization/Location/HealthcareService.
"""

import strawberry

# Registers ContactPointSystem/IdentifierUse/AddressUse/HumanNameUse/
# DayOfWeek/etc. as GraphQL enums (side-effect import) — required before
# wrapping any input schema whose fields use them.
import app.gql.enums  # noqa: F401
from app.schemas.practitioner_role.input import (
    PractitionerRoleCreateSchema,
    PractitionerRolePatchSchema,
)
from app.schemas.practitioner_role.input import (
    PractitionerRoleAvailabilityInput as PractitionerRoleAvailabilityInputSchema,
)
from app.schemas.practitioner_role.input import (
    PractitionerRoleAvailableTimeInput as PractitionerRoleAvailableTimeInputSchema,
)
from app.schemas.practitioner_role.input import (
    PractitionerRoleCharacteristicInput as PractitionerRoleCharacteristicInputSchema,
)
from app.schemas.practitioner_role.input import (
    PractitionerRoleCodeInput as PractitionerRoleCodeInputSchema,
)
from app.schemas.practitioner_role.input import (
    PractitionerRoleCommunicationInput as PractitionerRoleCommunicationInputSchema,
)
from app.schemas.practitioner_role.input import (
    PractitionerRoleContactInput as PractitionerRoleContactInputSchema,
)
from app.schemas.practitioner_role.input import (
    PractitionerRoleContactNameInput as PractitionerRoleContactNameInputSchema,
)
from app.schemas.practitioner_role.input import (
    PractitionerRoleContactTelecomInput as PractitionerRoleContactTelecomInputSchema,
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
    PractitionerRoleNotAvailableTimeInput as PractitionerRoleNotAvailableTimeInputSchema,
)
from app.schemas.practitioner_role.input import (
    PractitionerRoleSpecialtyInput as PractitionerRoleSpecialtyInputSchema,
)

# ── Input types — leaf sub-resources first ───────────────────────────────────


@strawberry.experimental.pydantic.input(model=PractitionerRoleIdentifierInputSchema, all_fields=True, description="Input for one PractitionerRole.identifier entry.")
class PractitionerRoleIdentifierInput:
    """Input for one PractitionerRole.identifier entry."""


@strawberry.experimental.pydantic.input(model=PractitionerRoleCodeInputSchema, all_fields=True, description="Input for one PractitionerRole.code entry.")
class PractitionerRoleCodeInput:
    """Input for one PractitionerRole.code entry."""


@strawberry.experimental.pydantic.input(model=PractitionerRoleSpecialtyInputSchema, all_fields=True, description="Input for one PractitionerRole.specialty entry.")
class PractitionerRoleSpecialtyInput:
    """Input for one PractitionerRole.specialty entry."""


@strawberry.experimental.pydantic.input(model=PractitionerRoleLocationInputSchema, all_fields=True, description="Input for one Location reference. Validated on create.")
class PractitionerRoleLocationInput:
    """Input for one PractitionerRole.location reference."""


@strawberry.experimental.pydantic.input(model=PractitionerRoleHealthcareServiceInputSchema, all_fields=True, description="Input for one HealthcareService reference. Validated on create.")
class PractitionerRoleHealthcareServiceInput:
    """Input for one PractitionerRole.healthcareService reference."""


@strawberry.experimental.pydantic.input(model=PractitionerRoleCharacteristicInputSchema, all_fields=True, description="Input for one PractitionerRole.characteristic entry.")
class PractitionerRoleCharacteristicInput:
    """Input for one PractitionerRole.characteristic entry."""


@strawberry.experimental.pydantic.input(model=PractitionerRoleCommunicationInputSchema, all_fields=True, description="Input for one PractitionerRole.communication entry.")
class PractitionerRoleCommunicationInput:
    """Input for one PractitionerRole.communication entry."""


@strawberry.experimental.pydantic.input(model=PractitionerRoleContactNameInputSchema, all_fields=True, description="Input for one name entry within a PractitionerRole.contact.")
class PractitionerRoleContactNameInput:
    """Input for one name entry within a PractitionerRole.contact."""


@strawberry.experimental.pydantic.input(model=PractitionerRoleContactTelecomInputSchema, all_fields=True, description="Input for one telecom entry within a PractitionerRole.contact.")
class PractitionerRoleContactTelecomInput:
    """Input for one telecom entry within a PractitionerRole.contact."""


@strawberry.experimental.pydantic.input(model=PractitionerRoleContactInputSchema, all_fields=True, description="Input for one PractitionerRole.contact entry (references PractitionerRoleContactNameInput/PractitionerRoleContactTelecomInput).")
class PractitionerRoleContactInput:
    """Input for one PractitionerRole.contact entry."""


@strawberry.experimental.pydantic.input(model=PractitionerRoleAvailableTimeInputSchema, all_fields=True, description="Input for one available-time slot within a PractitionerRole.availability entry.")
class PractitionerRoleAvailableTimeInput:
    """Input for one available-time slot."""


@strawberry.experimental.pydantic.input(model=PractitionerRoleNotAvailableTimeInputSchema, all_fields=True, description="Input for one not-available period within a PractitionerRole.availability entry.")
class PractitionerRoleNotAvailableTimeInput:
    """Input for one not-available period."""


@strawberry.experimental.pydantic.input(model=PractitionerRoleAvailabilityInputSchema, all_fields=True, description="Input for one PractitionerRole.availability group (references PractitionerRoleAvailableTimeInput/PractitionerRoleNotAvailableTimeInput).")
class PractitionerRoleAvailabilityInput:
    """Input for one PractitionerRole.availability group."""


@strawberry.experimental.pydantic.input(model=PractitionerRoleEndpointInputSchema, all_fields=True, description="Input for one PractitionerRole.endpoint reference. Not validated (no Endpoint resource in this project).")
class PractitionerRoleEndpointInput:
    """Input for one PractitionerRole.endpoint reference."""


@strawberry.experimental.pydantic.input(
    model=PractitionerRoleCreateSchema, all_fields=True,
    description=(
        "Input for `createPractitionerRole`. If `practitioner`/`organization` are set, each must "
        "reference an existing resource in the caller's own tenant; each `location`/"
        "`healthcareService` entry is validated the same way. `createdBy` is stamped "
        "automatically from the caller's JWT — do not supply it."
    ),
)
class PractitionerRoleCreateInput:
    """Input for `createPractitionerRole` — mirrors PractitionerRoleCreateSchema."""


@strawberry.experimental.pydantic.input(
    model=PractitionerRolePatchSchema, all_fields=True,
    description=(
        "Input for `updatePractitionerRole` — every field optional, at least one must be set. "
        "Only `active`/`periodStart`/`periodEnd`/`availabilityExceptions` are patchable; child "
        "arrays are create-only — delete and re-create to correct those."
    ),
)
class PractitionerRolePatchInput:
    """Input for `updatePractitionerRole` — every field optional, at least one must be set (enforced in PractitionerRoleService)."""


# `ListPractitionerRolesSchema` is a query-parameter schema, not a mutation
# payload — exposed as plain field arguments on the `practitionerRoles`
# query instead, matching every other resource's `List*Schema` treatment.
__all__ = [
    "PractitionerRoleIdentifierInput",
    "PractitionerRoleCodeInput",
    "PractitionerRoleSpecialtyInput",
    "PractitionerRoleLocationInput",
    "PractitionerRoleHealthcareServiceInput",
    "PractitionerRoleCharacteristicInput",
    "PractitionerRoleCommunicationInput",
    "PractitionerRoleContactNameInput",
    "PractitionerRoleContactTelecomInput",
    "PractitionerRoleContactInput",
    "PractitionerRoleAvailableTimeInput",
    "PractitionerRoleNotAvailableTimeInput",
    "PractitionerRoleAvailabilityInput",
    "PractitionerRoleEndpointInput",
    "PractitionerRoleCreateInput",
    "PractitionerRolePatchInput",
]
