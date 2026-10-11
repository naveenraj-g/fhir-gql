"""
GraphQL response (output) types for the PractitionerRole resource, derived
from the Pydantic schemas in the app/schemas/practitioner_role/response/
package via `strawberry.experimental.pydantic`. Input types live in
app/gql/practitioner_role/types/input.py — this split mirrors the
app/schemas/practitioner_role/{response,input}/ package split one layer
down.

Booking-specific output types (PractitionerDetailType,
PractitionerRoleBookingType, PaginatedPractitionerRoleBookingType) have no
corresponding inputs — booking is read-only, and (per
app/schemas/practitioner_role/response/booking.py's docstring) has no
fhir-server counterpart at all; kept as-is, out of scope for this port.

NOTE: `PractitionerRoleCharacteristicType`, `PractitionerRoleCommunicationType`,
`PractitionerRoleContactType` (+ nested name/telecom types), and
`PractitionerRoleAvailabilityType` are GONE — the sub-resources they wrapped
don't exist on FHIR R4 PractitionerRole (see
app/schemas/practitioner_role/input/core.py's docstring). New
`PractitionerRoleTelecomType` (top-level) replaces the old nested contact
telecom, and `PractitionerRoleAvailableTimeType`/
`PractitionerRoleNotAvailableType` are now flat top-level arrays rather
than nested inside an availability group.

Naming convention: `<X>Response` (Pydantic) -> `<X>Type` (GraphQL object type).

Declaration order matters: `strawberry.experimental.pydantic` resolves a
wrapped model's nested-model fields by looking up the nested Pydantic class
in its own registry, which only has entries for classes wrapped *before*
the parent is declared. Leaf sub-resource types are therefore declared
first, the top-level `PractitionerRoleType` / `PaginatedPractitionerRoleType`
next, and the booking types last (since they subclass the core types).
"""

import strawberry

from app.schemas.practitioner_role.response import (
    PaginatedPractitionerRoleBookingResponse,
    PaginatedPractitionerRoleResponse,
    PractitionerDetailResponse,
    PractitionerRoleAvailableTimeResponse,
    PractitionerRoleBookingHealthcareServiceResponse,
    PractitionerRoleBookingLocationResponse,
    PractitionerRoleBookingResponse,
    PractitionerRoleCodeResponse,
    PractitionerRoleDetailLanguageResponse,
    PractitionerRoleDetailTelecomResponse,
    PractitionerRoleEndpointResponse,
    PractitionerRoleHealthcareServiceResponse,
    PractitionerRoleIdentifierResponse,
    PractitionerRoleLocationResponse,
    PractitionerRoleNameResponse,
    PractitionerRoleNotAvailableResponse,
    PractitionerRoleQualificationResponse,
    PractitionerRoleResponse,
    PractitionerRoleSpecialtyResponse,
    PractitionerRoleTelecomResponse,
)

# ── Response (output) types — leaf sub-resources first ───────────────────────


@strawberry.experimental.pydantic.type(
    model=PractitionerRoleIdentifierResponse,
    all_fields=True,
    description="A single PractitionerRole.identifier entry.",
)
class PractitionerRoleIdentifierType:
    """A single PractitionerRole.identifier entry."""


@strawberry.experimental.pydantic.type(
    model=PractitionerRoleCodeResponse,
    all_fields=True,
    description="A single PractitionerRole.code entry.",
)
class PractitionerRoleCodeType:
    """A single PractitionerRole.code entry."""


@strawberry.experimental.pydantic.type(
    model=PractitionerRoleSpecialtyResponse,
    all_fields=True,
    description="A single PractitionerRole.specialty entry.",
)
class PractitionerRoleSpecialtyType:
    """A single PractitionerRole.specialty entry."""


@strawberry.experimental.pydantic.type(
    model=PractitionerRoleLocationResponse,
    all_fields=True,
    description="A single PractitionerRole.location reference.",
)
class PractitionerRoleLocationType:
    """A single PractitionerRole.location reference."""


@strawberry.experimental.pydantic.type(
    model=PractitionerRoleHealthcareServiceResponse,
    all_fields=True,
    description="A single PractitionerRole.healthcareService reference.",
)
class PractitionerRoleHealthcareServiceType:
    """A single PractitionerRole.healthcareService reference."""


@strawberry.experimental.pydantic.type(
    model=PractitionerRoleTelecomResponse,
    all_fields=True,
    description="A single PractitionerRole.telecom (ContactPoint) entry.",
)
class PractitionerRoleTelecomType:
    """A single PractitionerRole.telecom entry."""


@strawberry.experimental.pydantic.type(
    model=PractitionerRoleAvailableTimeResponse,
    all_fields=True,
    description="A single PractitionerRole.availableTime entry.",
)
class PractitionerRoleAvailableTimeType:
    """A single PractitionerRole.availableTime entry."""


@strawberry.experimental.pydantic.type(
    model=PractitionerRoleNotAvailableResponse,
    all_fields=True,
    description="A single PractitionerRole.notAvailable entry.",
)
class PractitionerRoleNotAvailableType:
    """A single PractitionerRole.notAvailable entry."""


@strawberry.experimental.pydantic.type(
    model=PractitionerRoleEndpointResponse,
    all_fields=True,
    description="A single PractitionerRole.endpoint reference.",
)
class PractitionerRoleEndpointType:
    """A single PractitionerRole.endpoint reference."""


@strawberry.experimental.pydantic.type(
    model=PractitionerRoleResponse,
    all_fields=True,
    description="A full PractitionerRole resource, including all nested sub-resource arrays (identifiers, codes, specialties, locations, healthcareServices, telecoms, availableTimes, notAvailables, endpoints).",
)
class PractitionerRoleType:
    """A full PractitionerRole resource, including all nested sub-resource arrays."""


@strawberry.experimental.pydantic.type(
    model=PaginatedPractitionerRoleResponse,
    all_fields=True,
    description="Paginated envelope returned by the `practitionerRoles` query — `data` for the current page, plus `total`/`limit`/`offset` for pagination.",
)
class PaginatedPractitionerRoleType:
    """Paginated envelope returned by the `practitionerRoles` list query."""


# ── Booking-enriched types (no fhir-server counterpart — see module docstring) ──


@strawberry.experimental.pydantic.type(
    model=PractitionerRoleQualificationResponse,
    all_fields=True,
    description="A single qualification entry for a Practitioner in the booking response.",
)
class PractitionerRoleQualificationType:
    """A single qualification entry for a Practitioner in the booking response."""


@strawberry.experimental.pydantic.type(
    model=PractitionerRoleNameResponse,
    all_fields=True,
    description="Structured name for a Practitioner in the booking response.",
)
class PractitionerRoleNameType:
    """Structured name for a Practitioner in the booking response."""


@strawberry.experimental.pydantic.type(
    model=PractitionerRoleDetailTelecomResponse,
    all_fields=True,
    description="A single telecom entry within the booking response's practitioner_detail block.",
)
class PractitionerRoleDetailTelecomType:
    """A single telecom entry within the booking response's practitioner_detail block."""


@strawberry.experimental.pydantic.type(
    model=PractitionerRoleDetailLanguageResponse,
    all_fields=True,
    description="A single language entry within the booking response's practitioner_detail block.",
)
class PractitionerRoleDetailLanguageType:
    """A single language entry within the booking response's practitioner_detail block."""


@strawberry.experimental.pydantic.type(
    model=PractitionerDetailResponse,
    all_fields=True,
    description="Enriched Practitioner data embedded in each booking response item.",
)
class PractitionerDetailType:
    """Enriched Practitioner data embedded in each booking response item."""


@strawberry.experimental.pydantic.type(
    model=PractitionerRoleBookingLocationResponse,
    all_fields=True,
    description="Location reference enriched with Location model data for booking UIs.",
)
class PractitionerRoleBookingLocationType:
    """Location reference enriched with Location model data for booking UIs."""


@strawberry.experimental.pydantic.type(
    model=PractitionerRoleBookingHealthcareServiceResponse,
    all_fields=True,
    description="HealthcareService reference enriched with HealthcareService model data for booking UIs.",
)
class PractitionerRoleBookingHealthcareServiceType:
    """HealthcareService reference enriched with HealthcareService model data for booking UIs."""


@strawberry.experimental.pydantic.type(
    model=PractitionerRoleBookingResponse,
    all_fields=True,
    description="PractitionerRole enriched with the linked Practitioner's details and resolved Location/HealthcareService data.",
)
class PractitionerRoleBookingType:
    """PractitionerRole enriched with the linked Practitioner's details."""


@strawberry.experimental.pydantic.type(
    model=PaginatedPractitionerRoleBookingResponse,
    all_fields=True,
    description="Paginated envelope returned by the `practitionerRolesForBooking` query.",
)
class PaginatedPractitionerRoleBookingType:
    """Paginated envelope returned by the `practitionerRolesForBooking` query."""


__all__ = [
    "PaginatedPractitionerRoleBookingType",
    "PaginatedPractitionerRoleType",
    "PractitionerDetailType",
    "PractitionerRoleAvailableTimeType",
    "PractitionerRoleBookingHealthcareServiceType",
    "PractitionerRoleBookingLocationType",
    "PractitionerRoleBookingType",
    "PractitionerRoleCodeType",
    "PractitionerRoleDetailLanguageType",
    "PractitionerRoleDetailTelecomType",
    "PractitionerRoleEndpointType",
    "PractitionerRoleHealthcareServiceType",
    "PractitionerRoleIdentifierType",
    "PractitionerRoleLocationType",
    "PractitionerRoleNameType",
    "PractitionerRoleNotAvailableType",
    "PractitionerRoleQualificationType",
    "PractitionerRoleSpecialtyType",
    "PractitionerRoleTelecomType",
    "PractitionerRoleType",
]
