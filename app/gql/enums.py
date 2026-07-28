"""
GraphQL enum registrations shared across all resource types.

`strawberry.experimental.pydantic.type` / `.input` need every plain Python
`Enum` referenced by a wrapped Pydantic model's fields to already be
registered as a GraphQL enum via `strawberry.enum(...)` before that model is
wrapped. `strawberry.enum()` annotates the existing Enum class in place (it
does not create a new class), so each FHIR code-set enum must be wrapped
exactly once — doing it here, in one shared module, means resource type
modules (patient.py, organization.py, ...) that need the same enum (e.g.
AddressUse is used by both Patient and Organization) import the same
already-wrapped class instead of risking a double-registration.

Only enums referenced by *input* schemas need wrapping: response schemas
(app/schemas/*/response.py) represent FHIR code values as plain `str`, not
these Enum classes, so they need no special GraphQL handling.
"""

import strawberry

from app.schemas.enums import (
    AddressType,
    AddressUse,
    AdministrativeGender,
    ContactPointSystem,
    ContactPointUse,
    DayOfWeek,
    HumanNameUse,
    IdentifierUse,
    TotalMode,
)
from app.schemas.location.enums import LocationMode, LocationStatus
from app.schemas.patient.enums import (
    GeneralPractitionerReferenceType,
    PatientLinkOtherType,
    PatientLinkType,
)
from app.schemas.slot.enums import SlotStatus

# ── Shared FHIR code-set enums (app.schemas.enums) ────────────────────────────
AddressTypeEnum = strawberry.enum(AddressType)
AddressUseEnum = strawberry.enum(AddressUse)
AdministrativeGenderEnum = strawberry.enum(AdministrativeGender)
ContactPointSystemEnum = strawberry.enum(ContactPointSystem)
ContactPointUseEnum = strawberry.enum(ContactPointUse)
HumanNameUseEnum = strawberry.enum(HumanNameUse)
IdentifierUseEnum = strawberry.enum(IdentifierUse)
TotalModeEnum = strawberry.enum(TotalMode)
DayOfWeekEnum = strawberry.enum(DayOfWeek)

# ── Patient-specific enums (app.schemas.patient.enums) ────────────────────────
GeneralPractitionerReferenceTypeEnum = strawberry.enum(GeneralPractitionerReferenceType)
PatientLinkOtherTypeEnum = strawberry.enum(PatientLinkOtherType)
# Explicit `name=` — the Python class is named `PatientLinkType`, which would
# otherwise collide with the GraphQL *object* type of the same name in
# app/gql/types/patient.py (the wrapper for PatientLinkResponse).
PatientLinkTypeEnum = strawberry.enum(PatientLinkType, name="PatientLinkTypeCode")

# ── Location-specific enums (app.schemas.location.enums) ──────────────────────
LocationStatusEnum = strawberry.enum(LocationStatus)
LocationModeEnum = strawberry.enum(LocationMode)

# ── Slot-specific enums (app.schemas.slot.enums) ───────────────────────────────
SlotStatusEnum = strawberry.enum(SlotStatus)
