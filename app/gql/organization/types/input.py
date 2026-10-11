"""
GraphQL input types for the Organization resource, derived from the
Pydantic schemas in the app/schemas/organization/input/ package via
`strawberry.experimental.pydantic`. Output types live in
app/gql/organization/types/response.py.

Naming convention:
  - `<X>Schema` (Pydantic) -> `<X>Input` (GraphQL input type)
  - Pydantic input schemas that already share a name with the GraphQL
    wrapper class defined here (OrganizationIdentifierInput,
    OrganizationTypeInput, OrganizationAliasInput, OrganizationTelecomInput,
    OrganizationAddressInput, OrganizationContactTelecomInput,
    OrganizationContactInput, OrganizationEndpointInput) are imported under
    a `...Schema` alias so the plain name is free for this module's GraphQL
    class.

Declaration order matters — leaf sub-resource input types are declared
first, `OrganizationCreateInput`/`OrganizationPatchInput` last.
"""

import strawberry

# Registers AddressUse/ContactPointSystem/etc. as GraphQL enums (side-effect
# import) — required before wrapping any input schema whose fields use them.
import app.gql.enums  # noqa: F401
from app.schemas.organization.input import (
    OrganizationAddressInput as OrganizationAddressInputSchema,
)
from app.schemas.organization.input import (
    OrganizationAliasInput as OrganizationAliasInputSchema,
)
from app.schemas.organization.input import (
    OrganizationContactInput as OrganizationContactInputSchema,
)
from app.schemas.organization.input import (
    OrganizationContactTelecomInput as OrganizationContactTelecomInputSchema,
)
from app.schemas.organization.input import (
    OrganizationCreateSchema,
    OrganizationPatchSchema,
)
from app.schemas.organization.input import (
    OrganizationEndpointInput as OrganizationEndpointInputSchema,
)
from app.schemas.organization.input import (
    OrganizationIdentifierInput as OrganizationIdentifierInputSchema,
)
from app.schemas.organization.input import (
    OrganizationTelecomInput as OrganizationTelecomInputSchema,
)
from app.schemas.organization.input import (
    OrganizationTypeInput as OrganizationTypeInputSchema,
)

# ── Input types — leaf sub-resources first ───────────────────────────────────


@strawberry.experimental.pydantic.input(
    model=OrganizationIdentifierInputSchema,
    all_fields=True,
    description="Input for one Organization.identifier entry.",
)
class OrganizationIdentifierInput:
    """Input for one Organization.identifier entry."""


@strawberry.experimental.pydantic.input(
    model=OrganizationTypeInputSchema,
    all_fields=True,
    description="Input for one Organization.type CodeableConcept entry — common codes: prov, dept, team, govt, ins, pay, edu, reli, crs, cg, bus, other.",
)
class OrganizationTypeInput:
    """Input for one Organization.type CodeableConcept entry."""


@strawberry.experimental.pydantic.input(
    model=OrganizationAliasInputSchema,
    all_fields=True,
    description="Input for one Organization.alias entry.",
)
class OrganizationAliasInput:
    """Input for one Organization.alias entry."""


@strawberry.experimental.pydantic.input(
    model=OrganizationTelecomInputSchema,
    all_fields=True,
    description="Input for one Organization.telecom entry. `system` and `value` are required.",
)
class OrganizationTelecomInput:
    """Input for one Organization.telecom entry."""


@strawberry.experimental.pydantic.input(
    model=OrganizationAddressInputSchema,
    all_fields=True,
    description="Input for one Organization.address entry.",
)
class OrganizationAddressInput:
    """Input for one Organization.address entry."""


@strawberry.experimental.pydantic.input(
    model=OrganizationContactTelecomInputSchema,
    all_fields=True,
    description="Input for one telecom entry nested inside an Organization.contact person.",
)
class OrganizationContactTelecomInput:
    """Input for one telecom entry nested inside an Organization.contact person."""


@strawberry.experimental.pydantic.input(
    model=OrganizationContactInputSchema,
    all_fields=True,
    description="Input for one Organization.contact person, with a nested telecom array.",
)
class OrganizationContactInput:
    """Input for one Organization.contact person (references OrganizationContactTelecomInput)."""


@strawberry.experimental.pydantic.input(
    model=OrganizationEndpointInputSchema,
    all_fields=True,
    description="Input for one Organization.endpoint reference.",
)
class OrganizationEndpointInput:
    """Input for one Organization.endpoint reference."""


@strawberry.experimental.pydantic.input(
    model=OrganizationCreateSchema,
    all_fields=True,
    description=(
        "Input for `createOrganization`. Creates an Organization and any combination of "
        "its sub-resources (identifier, type, alias, telecom, address, contact, endpoint) "
        "atomically in one request. `orgId`/`createdBy` are derived from the caller's JWT — "
        "do not supply them (not declared on this input type at all)."
    ),
)
class OrganizationCreateInput:
    """Input for `createOrganization` — mirrors OrganizationCreateSchema exactly."""


@strawberry.experimental.pydantic.input(
    model=OrganizationPatchSchema,
    all_fields=True,
    description=(
        "Input for `updateOrganization`. Only supplied fields are written; every supplied "
        "sub-resource list (even `[]`) replaces the corresponding rows wholesale. `updatedBy` "
        "is derived from the caller's JWT — do not supply it."
    ),
)
class OrganizationPatchInput:
    """Input for `updateOrganization` — every field optional, at least one must be set."""


# `ListOrganizationsSchema` is a query-parameter schema, not a mutation
# payload — GraphQL convention is to expose filters as plain field arguments
# rather than a wrapped input type, so it's intentionally NOT wrapped here.
# See app/gql/organization/queries.py, which imports it directly from
# app.schemas.organization.input.
__all__ = [
    "OrganizationAddressInput",
    "OrganizationAliasInput",
    "OrganizationContactInput",
    "OrganizationContactTelecomInput",
    "OrganizationCreateInput",
    "OrganizationEndpointInput",
    "OrganizationIdentifierInput",
    "OrganizationPatchInput",
    "OrganizationTelecomInput",
    "OrganizationTypeInput",
]
