"""
GraphQL response (output) types for the HealthcareService resource, derived
from the Pydantic schemas in the app/schemas/healthcare_service/response/
package via `strawberry.experimental.pydantic`. Input types live in
app/gql/healthcare_service/types/input.py — this split mirrors the
app/schemas/healthcare_service/{response,input}/ package split one layer
down.

Naming convention: `<X>Response` (Pydantic) -> `<X>Type` (GraphQL object type).

Declaration order matters — leaf sub-resource types are declared first, the
top-level `HealthcareServiceType` / `PaginatedHealthcareServiceType` last.
"""

import strawberry

from app.schemas.healthcare_service.response import (
    HealthcareServiceAvailableTimeResponse,
    HealthcareServiceCategoryResponse,
    HealthcareServiceCharacteristicResponse,
    HealthcareServiceCommunicationResponse,
    HealthcareServiceCoverageAreaResponse,
    HealthcareServiceEligibilityResponse,
    HealthcareServiceEndpointResponse,
    HealthcareServiceIdentifierResponse,
    HealthcareServiceLocationResponse,
    HealthcareServiceNotAvailableResponse,
    HealthcareServiceProgramResponse,
    HealthcareServiceReferralMethodResponse,
    HealthcareServiceResponse,
    HealthcareServiceServiceProvisionCodeResponse,
    HealthcareServiceSpecialtyResponse,
    HealthcareServiceTelecomResponse,
    HealthcareServiceTypeResponse,
    PaginatedHealthcareServiceResponse,
)

# ── Response (output) types — leaf sub-resources first ───────────────────────


@strawberry.experimental.pydantic.type(
    model=HealthcareServiceIdentifierResponse,
    all_fields=True,
    description="A single HealthcareService.identifier entry.",
)
class HealthcareServiceIdentifierType:
    """A single HealthcareService.identifier entry."""


@strawberry.experimental.pydantic.type(
    model=HealthcareServiceCategoryResponse,
    all_fields=True,
    description="A single HealthcareService.category entry — a broad category grouping the service.",
)
class HealthcareServiceCategoryType:
    """A single HealthcareService.category entry."""


@strawberry.experimental.pydantic.type(
    model=HealthcareServiceTypeResponse,
    all_fields=True,
    description="A single HealthcareService.type entry — a specific type of service delivered.",
)
class HealthcareServiceTypeType:
    """A single HealthcareService.type entry."""


@strawberry.experimental.pydantic.type(
    model=HealthcareServiceSpecialtyResponse,
    all_fields=True,
    description="A single HealthcareService.specialty entry — a clinical specialty (e.g. Cardiology).",
)
class HealthcareServiceSpecialtyType:
    """A single HealthcareService.specialty entry."""


@strawberry.experimental.pydantic.type(
    model=HealthcareServiceLocationResponse,
    all_fields=True,
    description="A single Location reference where this HealthcareService is provided.",
)
class HealthcareServiceLocationType:
    """A single HealthcareService.location reference."""


@strawberry.experimental.pydantic.type(
    model=HealthcareServiceTelecomResponse,
    all_fields=True,
    description="A single HealthcareService.telecom (ContactPoint) entry.",
)
class HealthcareServiceTelecomType:
    """A single HealthcareService.telecom entry."""


@strawberry.experimental.pydantic.type(
    model=HealthcareServiceCoverageAreaResponse,
    all_fields=True,
    description="A single Location reference defining the coverage area for this HealthcareService.",
)
class HealthcareServiceCoverageAreaType:
    """A single HealthcareService.coverageArea reference."""


@strawberry.experimental.pydantic.type(
    model=HealthcareServiceServiceProvisionCodeResponse,
    all_fields=True,
    description="A single HealthcareService.serviceProvisionCode entry — conditions of availability (e.g. free, discounted).",
)
class HealthcareServiceServiceProvisionCodeType:
    """A single HealthcareService.serviceProvisionCode entry."""


@strawberry.experimental.pydantic.type(
    model=HealthcareServiceEligibilityResponse,
    all_fields=True,
    description="A single HealthcareService.eligibility entry — criteria required to receive the service.",
)
class HealthcareServiceEligibilityType:
    """A single HealthcareService.eligibility entry."""


@strawberry.experimental.pydantic.type(
    model=HealthcareServiceProgramResponse,
    all_fields=True,
    description="A single HealthcareService.program entry — a health program this service is part of.",
)
class HealthcareServiceProgramType:
    """A single HealthcareService.program entry."""


@strawberry.experimental.pydantic.type(
    model=HealthcareServiceCharacteristicResponse,
    all_fields=True,
    description="A single HealthcareService.characteristic entry.",
)
class HealthcareServiceCharacteristicType:
    """A single HealthcareService.characteristic entry."""


@strawberry.experimental.pydantic.type(
    model=HealthcareServiceCommunicationResponse,
    all_fields=True,
    description="A single HealthcareService.communication entry — a language the service communicates in.",
)
class HealthcareServiceCommunicationType:
    """A single HealthcareService.communication entry."""


@strawberry.experimental.pydantic.type(
    model=HealthcareServiceReferralMethodResponse,
    all_fields=True,
    description="A single HealthcareService.referralMethod entry.",
)
class HealthcareServiceReferralMethodType:
    """A single HealthcareService.referralMethod entry."""


@strawberry.experimental.pydantic.type(
    model=HealthcareServiceAvailableTimeResponse,
    all_fields=True,
    description="A single HealthcareService.availableTime entry.",
)
class HealthcareServiceAvailableTimeType:
    """A single HealthcareService.availableTime entry."""


@strawberry.experimental.pydantic.type(
    model=HealthcareServiceNotAvailableResponse,
    all_fields=True,
    description="A single HealthcareService.notAvailable entry — a period the service is unavailable.",
)
class HealthcareServiceNotAvailableType:
    """A single HealthcareService.notAvailable entry."""


@strawberry.experimental.pydantic.type(
    model=HealthcareServiceEndpointResponse,
    all_fields=True,
    description="A single HealthcareService.endpoint reference.",
)
class HealthcareServiceEndpointType:
    """A single HealthcareService.endpoint reference."""


@strawberry.experimental.pydantic.type(
    model=HealthcareServiceResponse,
    all_fields=True,
    description="A full HealthcareService resource, including all nested sub-resource arrays.",
)
class HealthcareServiceType:
    """A full HealthcareService resource, including all nested sub-resource arrays."""


@strawberry.experimental.pydantic.type(
    model=PaginatedHealthcareServiceResponse,
    all_fields=True,
    description="Paginated envelope returned by the `healthcareServices` query — `data` for the current page, plus `total`/`limit`/`offset` for pagination.",
)
class PaginatedHealthcareServiceType:
    """Paginated envelope returned by the `healthcareServices` list query."""


__all__ = [
    "HealthcareServiceAvailableTimeType",
    "HealthcareServiceCategoryType",
    "HealthcareServiceCharacteristicType",
    "HealthcareServiceCommunicationType",
    "HealthcareServiceCoverageAreaType",
    "HealthcareServiceEligibilityType",
    "HealthcareServiceEndpointType",
    "HealthcareServiceIdentifierType",
    "HealthcareServiceLocationType",
    "HealthcareServiceNotAvailableType",
    "HealthcareServiceProgramType",
    "HealthcareServiceReferralMethodType",
    "HealthcareServiceServiceProvisionCodeType",
    "HealthcareServiceSpecialtyType",
    "HealthcareServiceTelecomType",
    "HealthcareServiceType",
    "HealthcareServiceTypeType",
    "PaginatedHealthcareServiceType",
]
