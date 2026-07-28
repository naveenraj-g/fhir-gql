"""
GraphQL input types for the HealthcareService resource, derived from the
existing Pydantic schemas in app/schemas/healthcare_service/input.py via
`strawberry.experimental.pydantic`. Output types live in
app/gql/healthcare_service/types/types.py.

Naming convention:
  - `<X>Schema`/`<X>Input` (Pydantic) -> `<X>Input` (GraphQL input type)
  - Every one of the 16 sub-resource Pydantic input schemas already ends in
    "Input" and shares its name with the GraphQL wrapper class defined here,
    so all 16 are imported under a `...Schema` alias, same pattern used for
    Organization's/Location's colliding sub-resource input names.

All 16 leaf input types are needed even though none has its own dedicated
mutation (HealthcareServicePatchSchema doesn't expose any array field) —
they're referenced as nested list-item types inside
`HealthcareServiceCreateInput`, and strawberry.experimental.pydantic needs
every nested model wrapped before the parent that contains it.
"""

import strawberry

# Registers ContactPointSystem/IdentifierUse/DayOfWeek/etc. as GraphQL enums
# (side-effect import) — required before wrapping any input schema whose
# fields use them.
import app.gql.enums  # noqa: F401
from app.schemas.healthcare_service.input import (
    HealthcareServiceAvailableTimeInput as HealthcareServiceAvailableTimeInputSchema,
)
from app.schemas.healthcare_service.input import (
    HealthcareServiceCategoryInput as HealthcareServiceCategoryInputSchema,
)
from app.schemas.healthcare_service.input import (
    HealthcareServiceCharacteristicInput as HealthcareServiceCharacteristicInputSchema,
)
from app.schemas.healthcare_service.input import (
    HealthcareServiceCommunicationInput as HealthcareServiceCommunicationInputSchema,
)
from app.schemas.healthcare_service.input import (
    HealthcareServiceCoverageAreaInput as HealthcareServiceCoverageAreaInputSchema,
)
from app.schemas.healthcare_service.input import (
    HealthcareServiceCreateSchema,
    HealthcareServicePatchSchema,
)
from app.schemas.healthcare_service.input import (
    HealthcareServiceEligibilityInput as HealthcareServiceEligibilityInputSchema,
)
from app.schemas.healthcare_service.input import (
    HealthcareServiceEndpointInput as HealthcareServiceEndpointInputSchema,
)
from app.schemas.healthcare_service.input import (
    HealthcareServiceIdentifierInput as HealthcareServiceIdentifierInputSchema,
)
from app.schemas.healthcare_service.input import (
    HealthcareServiceLocationInput as HealthcareServiceLocationInputSchema,
)
from app.schemas.healthcare_service.input import (
    HealthcareServiceNotAvailableInput as HealthcareServiceNotAvailableInputSchema,
)
from app.schemas.healthcare_service.input import (
    HealthcareServiceProgramInput as HealthcareServiceProgramInputSchema,
)
from app.schemas.healthcare_service.input import (
    HealthcareServiceProvisionCodeInput as HealthcareServiceProvisionCodeInputSchema,
)
from app.schemas.healthcare_service.input import (
    HealthcareServiceReferralMethodInput as HealthcareServiceReferralMethodInputSchema,
)
from app.schemas.healthcare_service.input import (
    HealthcareServiceSpecialtyInput as HealthcareServiceSpecialtyInputSchema,
)
from app.schemas.healthcare_service.input import (
    HealthcareServiceTelecomInput as HealthcareServiceTelecomInputSchema,
)
from app.schemas.healthcare_service.input import (
    HealthcareServiceTypeInput as HealthcareServiceTypeInputSchema,
)

# ── Input types — leaf sub-resources first ───────────────────────────────────


@strawberry.experimental.pydantic.input(
    model=HealthcareServiceIdentifierInputSchema,
    all_fields=True,
    description="Input for one HealthcareService.identifier entry.",
)
class HealthcareServiceIdentifierInput:
    """Input for one HealthcareService.identifier entry."""


@strawberry.experimental.pydantic.input(
    model=HealthcareServiceCategoryInputSchema,
    all_fields=True,
    description="Input for one HealthcareService.category entry.",
)
class HealthcareServiceCategoryInput:
    """Input for one HealthcareService.category entry."""


@strawberry.experimental.pydantic.input(
    model=HealthcareServiceTypeInputSchema,
    all_fields=True,
    description="Input for one HealthcareService.type entry.",
)
class HealthcareServiceTypeInput:
    """Input for one HealthcareService.type entry."""


@strawberry.experimental.pydantic.input(
    model=HealthcareServiceSpecialtyInputSchema,
    all_fields=True,
    description="Input for one HealthcareService.specialty entry.",
)
class HealthcareServiceSpecialtyInput:
    """Input for one HealthcareService.specialty entry."""


@strawberry.experimental.pydantic.input(
    model=HealthcareServiceLocationInputSchema,
    all_fields=True,
    description="Input for one Location reference where this HealthcareService is provided. Validated on create.",
)
class HealthcareServiceLocationInput:
    """Input for one HealthcareService.location reference."""


@strawberry.experimental.pydantic.input(
    model=HealthcareServiceTelecomInputSchema,
    all_fields=True,
    description="Input for one HealthcareService.telecom entry. `system` and `value` are required.",
)
class HealthcareServiceTelecomInput:
    """Input for one HealthcareService.telecom entry."""


@strawberry.experimental.pydantic.input(
    model=HealthcareServiceCoverageAreaInputSchema,
    all_fields=True,
    description="Input for one Location reference defining the coverage area. Validated on create.",
)
class HealthcareServiceCoverageAreaInput:
    """Input for one HealthcareService.coverageArea reference."""


@strawberry.experimental.pydantic.input(
    model=HealthcareServiceProvisionCodeInputSchema,
    all_fields=True,
    description="Input for one HealthcareService.serviceProvisionCode entry.",
)
class HealthcareServiceProvisionCodeInput:
    """Input for one HealthcareService.serviceProvisionCode entry."""


@strawberry.experimental.pydantic.input(
    model=HealthcareServiceEligibilityInputSchema,
    all_fields=True,
    description="Input for one HealthcareService.eligibility entry.",
)
class HealthcareServiceEligibilityInput:
    """Input for one HealthcareService.eligibility entry."""


@strawberry.experimental.pydantic.input(
    model=HealthcareServiceProgramInputSchema,
    all_fields=True,
    description="Input for one HealthcareService.program entry.",
)
class HealthcareServiceProgramInput:
    """Input for one HealthcareService.program entry."""


@strawberry.experimental.pydantic.input(
    model=HealthcareServiceCharacteristicInputSchema,
    all_fields=True,
    description="Input for one HealthcareService.characteristic entry.",
)
class HealthcareServiceCharacteristicInput:
    """Input for one HealthcareService.characteristic entry."""


@strawberry.experimental.pydantic.input(
    model=HealthcareServiceCommunicationInputSchema,
    all_fields=True,
    description="Input for one HealthcareService.communication entry.",
)
class HealthcareServiceCommunicationInput:
    """Input for one HealthcareService.communication entry."""


@strawberry.experimental.pydantic.input(
    model=HealthcareServiceReferralMethodInputSchema,
    all_fields=True,
    description="Input for one HealthcareService.referralMethod entry.",
)
class HealthcareServiceReferralMethodInput:
    """Input for one HealthcareService.referralMethod entry."""


@strawberry.experimental.pydantic.input(
    model=HealthcareServiceAvailableTimeInputSchema,
    all_fields=True,
    description="Input for one HealthcareService.availableTime entry.",
)
class HealthcareServiceAvailableTimeInput:
    """Input for one HealthcareService.availableTime entry."""


@strawberry.experimental.pydantic.input(
    model=HealthcareServiceNotAvailableInputSchema,
    all_fields=True,
    description="Input for one HealthcareService.notAvailable entry. `description` is required.",
)
class HealthcareServiceNotAvailableInput:
    """Input for one HealthcareService.notAvailable entry."""


@strawberry.experimental.pydantic.input(
    model=HealthcareServiceEndpointInputSchema,
    all_fields=True,
    description="Input for one HealthcareService.endpoint reference. Not validated (no Endpoint resource in this project).",
)
class HealthcareServiceEndpointInput:
    """Input for one HealthcareService.endpoint reference."""


@strawberry.experimental.pydantic.input(
    model=HealthcareServiceCreateSchema,
    all_fields=True,
    description=(
        "Input for `createHealthcareService`. If `providedBy` is set, it must reference an "
        "existing organization in the caller's own tenant. If `location`/`coverageArea` entries "
        "are set, each must reference an existing Location in the caller's own tenant. "
        "`createdBy` is stamped automatically from the caller's JWT — do not supply it."
    ),
)
class HealthcareServiceCreateInput:
    """Input for `createHealthcareService` — mirrors HealthcareServiceCreateSchema."""


@strawberry.experimental.pydantic.input(
    model=HealthcareServicePatchSchema,
    all_fields=True,
    description=(
        "Input for `updateHealthcareService` — every field optional, at least one must be set. "
        "Only scalar and photo fields are patchable; `providedBy`, `location`, `coverageArea`, "
        "and every array sub-resource are create-only — delete and re-create to correct those."
    ),
)
class HealthcareServicePatchInput:
    """Input for `updateHealthcareService` — every field optional, at least one must be set (enforced in HealthcareServiceService)."""


# `ListHealthcareServicesSchema` is a query-parameter schema, not a mutation
# payload — exposed as plain field arguments on the `healthcareServices`
# query instead, matching every other resource's `List*Schema` treatment.
__all__ = [
    "HealthcareServiceIdentifierInput",
    "HealthcareServiceCategoryInput",
    "HealthcareServiceTypeInput",
    "HealthcareServiceSpecialtyInput",
    "HealthcareServiceLocationInput",
    "HealthcareServiceTelecomInput",
    "HealthcareServiceCoverageAreaInput",
    "HealthcareServiceProvisionCodeInput",
    "HealthcareServiceEligibilityInput",
    "HealthcareServiceProgramInput",
    "HealthcareServiceCharacteristicInput",
    "HealthcareServiceCommunicationInput",
    "HealthcareServiceReferralMethodInput",
    "HealthcareServiceAvailableTimeInput",
    "HealthcareServiceNotAvailableInput",
    "HealthcareServiceEndpointInput",
    "HealthcareServiceCreateInput",
    "HealthcareServicePatchInput",
]
