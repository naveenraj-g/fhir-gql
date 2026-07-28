"""
GraphQL response (output) types for the PractitionerRole resource, derived
from the existing Pydantic schemas in
app/schemas/practitioner_role/response.py via
`strawberry.experimental.pydantic`. Input types live in
app/gql/practitioner_role/types/input.py — this split mirrors the
app/schemas/practitioner_role/{response,input}.py split one layer down.

Booking-specific output types (PractitionerDetailType,
PractitionerRoleBookingType, PaginatedPractitionerRoleBookingType) have no
corresponding inputs — booking is read-only.

Naming convention: `<X>Response` (Pydantic) -> `<X>Type` (GraphQL object type).
"""

import strawberry

from app.schemas.practitioner_role.response import (
    PaginatedPractitionerRoleBookingResponse,
    PaginatedPractitionerRoleResponse,
    PractitionerDetailResponse,
    PractitionerRoleAvailabilityResponse,
    PractitionerRoleAvailableTimeResponse,
    PractitionerRoleBookingHealthcareServiceResponse,
    PractitionerRoleBookingLocationResponse,
    PractitionerRoleBookingResponse,
    PractitionerRoleCharacteristicResponse,
    PractitionerRoleCodeResponse,
    PractitionerRoleCommunicationResponse,
    PractitionerRoleContactNameResponse,
    PractitionerRoleContactResponse,
    PractitionerRoleContactTelecomResponse,
    PractitionerRoleDetailLanguageResponse,
    PractitionerRoleDetailTelecomResponse,
    PractitionerRoleEndpointResponse,
    PractitionerRoleHealthcareServiceResponse,
    PractitionerRoleIdentifierResponse,
    PractitionerRoleLocationResponse,
    PractitionerRoleNameResponse,
    PractitionerRoleNotAvailableTimeResponse,
    PractitionerRoleQualificationResponse,
    PractitionerRoleResponse,
    PractitionerRoleSpecialtyResponse,
)

# ── Response (output) types — leaf sub-resources first ───────────────────────


@strawberry.experimental.pydantic.type(model=PractitionerRoleIdentifierResponse, all_fields=True, description="A single PractitionerRole.identifier entry.")
class PractitionerRoleIdentifierType:
    """A single PractitionerRole.identifier entry."""


@strawberry.experimental.pydantic.type(model=PractitionerRoleCodeResponse, all_fields=True, description="A single PractitionerRole.code entry — a role this practitioner is authorised to perform.")
class PractitionerRoleCodeType:
    """A single PractitionerRole.code entry."""


@strawberry.experimental.pydantic.type(model=PractitionerRoleSpecialtyResponse, all_fields=True, description="A single PractitionerRole.specialty entry.")
class PractitionerRoleSpecialtyType:
    """A single PractitionerRole.specialty entry."""


@strawberry.experimental.pydantic.type(model=PractitionerRoleLocationResponse, all_fields=True, description="A single Location reference where this PractitionerRole is provided.")
class PractitionerRoleLocationType:
    """A single PractitionerRole.location reference."""


@strawberry.experimental.pydantic.type(model=PractitionerRoleHealthcareServiceResponse, all_fields=True, description="A single HealthcareService reference this PractitionerRole provides.")
class PractitionerRoleHealthcareServiceType:
    """A single PractitionerRole.healthcareService reference."""


@strawberry.experimental.pydantic.type(model=PractitionerRoleCharacteristicResponse, all_fields=True, description="A single PractitionerRole.characteristic entry.")
class PractitionerRoleCharacteristicType:
    """A single PractitionerRole.characteristic entry."""


@strawberry.experimental.pydantic.type(model=PractitionerRoleCommunicationResponse, all_fields=True, description="A single PractitionerRole.communication language entry.")
class PractitionerRoleCommunicationType:
    """A single PractitionerRole.communication entry."""


@strawberry.experimental.pydantic.type(model=PractitionerRoleContactNameResponse, all_fields=True, description="A single name entry within a PractitionerRole.contact.")
class PractitionerRoleContactNameType:
    """A single name entry within a PractitionerRole.contact."""


@strawberry.experimental.pydantic.type(model=PractitionerRoleContactTelecomResponse, all_fields=True, description="A single telecom entry within a PractitionerRole.contact.")
class PractitionerRoleContactTelecomType:
    """A single telecom entry within a PractitionerRole.contact."""


@strawberry.experimental.pydantic.type(model=PractitionerRoleContactResponse, all_fields=True, description="A single PractitionerRole.contact entry (references PractitionerRoleContactNameType/PractitionerRoleContactTelecomType).")
class PractitionerRoleContactType:
    """A single PractitionerRole.contact entry."""


@strawberry.experimental.pydantic.type(model=PractitionerRoleAvailableTimeResponse, all_fields=True, description="A single available-time slot within a PractitionerRole.availability entry.")
class PractitionerRoleAvailableTimeType:
    """A single available-time slot within a PractitionerRole.availability entry."""


@strawberry.experimental.pydantic.type(model=PractitionerRoleNotAvailableTimeResponse, all_fields=True, description="A single not-available period within a PractitionerRole.availability entry.")
class PractitionerRoleNotAvailableTimeType:
    """A single not-available period within a PractitionerRole.availability entry."""


@strawberry.experimental.pydantic.type(model=PractitionerRoleAvailabilityResponse, all_fields=True, description="A single PractitionerRole.availability group (references PractitionerRoleAvailableTimeType/PractitionerRoleNotAvailableTimeType).")
class PractitionerRoleAvailabilityType:
    """A single PractitionerRole.availability group."""


@strawberry.experimental.pydantic.type(model=PractitionerRoleEndpointResponse, all_fields=True, description="A single PractitionerRole.endpoint reference.")
class PractitionerRoleEndpointType:
    """A single PractitionerRole.endpoint reference."""


@strawberry.experimental.pydantic.type(
    model=PractitionerRoleResponse, all_fields=True,
    description="A full PractitionerRole resource, including all nested sub-resource arrays.",
)
class PractitionerRoleType:
    """A full PractitionerRole resource, including all nested sub-resource arrays."""


@strawberry.experimental.pydantic.type(model=PaginatedPractitionerRoleResponse, all_fields=True, description="Paginated envelope returned by the `practitionerRoles` query.")
class PaginatedPractitionerRoleType:
    """Paginated envelope returned by the `practitionerRoles` list query."""


# ── Booking-enriched output types ─────────────────────────────────────────────


@strawberry.experimental.pydantic.type(model=PractitionerRoleQualificationResponse, all_fields=True, description="A single qualification entry for the practitioner in a booking result.")
class PractitionerRoleQualificationType:
    """A single qualification entry for the practitioner in a booking result."""


@strawberry.experimental.pydantic.type(model=PractitionerRoleNameResponse, all_fields=True, description="The practitioner's name in a booking result.")
class PractitionerRoleNameType:
    """The practitioner's name in a booking result."""


@strawberry.experimental.pydantic.type(model=PractitionerRoleDetailTelecomResponse, all_fields=True, description="A single telecom entry for the practitioner in a booking result.")
class PractitionerRoleDetailTelecomType:
    """A single telecom entry for the practitioner in a booking result."""


@strawberry.experimental.pydantic.type(model=PractitionerRoleDetailLanguageResponse, all_fields=True, description="A single language entry for the practitioner in a booking result.")
class PractitionerRoleDetailLanguageType:
    """A single language entry for the practitioner in a booking result."""


@strawberry.experimental.pydantic.type(
    model=PractitionerDetailResponse, all_fields=True,
    description="Enriched Practitioner data (name, gender, photo, qualifications) embedded in each booking result.",
)
class PractitionerDetailType:
    """Enriched Practitioner data embedded in each booking result."""


@strawberry.experimental.pydantic.type(model=PractitionerRoleBookingLocationResponse, all_fields=True, description="A Location reference enriched with address/phone data for a booking result.")
class PractitionerRoleBookingLocationType:
    """A Location reference enriched with address/phone data for a booking result."""


@strawberry.experimental.pydantic.type(model=PractitionerRoleBookingHealthcareServiceResponse, all_fields=True, description="A HealthcareService reference enriched with descriptive data for a booking result.")
class PractitionerRoleBookingHealthcareServiceType:
    """A HealthcareService reference enriched with descriptive data for a booking result."""


@strawberry.experimental.pydantic.type(
    model=PractitionerRoleBookingResponse, all_fields=True,
    description="A PractitionerRole enriched with the linked Practitioner's details and resolved Location/HealthcareService data, for booking UIs.",
)
class PractitionerRoleBookingType:
    """A PractitionerRole enriched with Practitioner/Location/HealthcareService details for booking UIs."""


@strawberry.experimental.pydantic.type(model=PaginatedPractitionerRoleBookingResponse, all_fields=True, description="Paginated envelope returned by the `practitionerRolesForBooking` query.")
class PaginatedPractitionerRoleBookingType:
    """Paginated envelope returned by the `practitionerRolesForBooking` query."""


__all__ = [
    "PractitionerRoleIdentifierType",
    "PractitionerRoleCodeType",
    "PractitionerRoleSpecialtyType",
    "PractitionerRoleLocationType",
    "PractitionerRoleHealthcareServiceType",
    "PractitionerRoleCharacteristicType",
    "PractitionerRoleCommunicationType",
    "PractitionerRoleContactNameType",
    "PractitionerRoleContactTelecomType",
    "PractitionerRoleContactType",
    "PractitionerRoleAvailableTimeType",
    "PractitionerRoleNotAvailableTimeType",
    "PractitionerRoleAvailabilityType",
    "PractitionerRoleEndpointType",
    "PractitionerRoleType",
    "PaginatedPractitionerRoleType",
    "PractitionerRoleQualificationType",
    "PractitionerRoleNameType",
    "PractitionerRoleDetailTelecomType",
    "PractitionerRoleDetailLanguageType",
    "PractitionerDetailType",
    "PractitionerRoleBookingLocationType",
    "PractitionerRoleBookingHealthcareServiceType",
    "PractitionerRoleBookingType",
    "PaginatedPractitionerRoleBookingType",
]
