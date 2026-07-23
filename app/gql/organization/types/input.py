"""
GraphQL input types for the Organization resource, derived from the
existing Pydantic schemas in app/schemas/organization/input.py via
`strawberry.experimental.pydantic`. Output types live in
app/gql/organization/types/types.py.

Naming convention:
  - `<X>Schema` (Pydantic) -> `<X>Input` (GraphQL input type)
  - Pydantic input schemas that already share a name with the GraphQL
    wrapper class defined here (OrgIdentifierInput, OrgTypeInput,
    OrgAliasInput, OrgTelecomInput, OrgAddressInput, OrgContactTelecomInput,
    OrgContactInput, OrgEndpointInput) are imported under a `...Schema`
    alias so the plain name is free for this module's GraphQL class.

Declaration order matters — leaf sub-resource input types are declared
first, `RegisterOrgInput`/`PatchOrgInput` last.
"""

import strawberry

# Registers AddressUse/ContactPointSystem/etc. as GraphQL enums (side-effect
# import) — required before wrapping any input schema whose fields use them.
import app.gql.enums  # noqa: F401
from app.schemas.organization.input import PatchOrgSchema, RegisterOrgSchema
from app.schemas.organization.input import OrgAddressInput as OrgAddressInputSchema
from app.schemas.organization.input import OrgAliasInput as OrgAliasInputSchema
from app.schemas.organization.input import OrgContactInput as OrgContactInputSchema
from app.schemas.organization.input import (
    OrgContactTelecomInput as OrgContactTelecomInputSchema,
)
from app.schemas.organization.input import OrgEndpointInput as OrgEndpointInputSchema
from app.schemas.organization.input import (
    OrgIdentifierInput as OrgIdentifierInputSchema,
)
from app.schemas.organization.input import OrgTelecomInput as OrgTelecomInputSchema
from app.schemas.organization.input import OrgTypeInput as OrgTypeInputSchema

# ── Input types — leaf sub-resources first ───────────────────────────────────


@strawberry.experimental.pydantic.input(
    model=OrgIdentifierInputSchema,
    all_fields=True,
    description="Input for one Organization.identifier entry.",
)
class OrgIdentifierInput:
    """Input for one Organization.identifier entry."""


@strawberry.experimental.pydantic.input(
    model=OrgTypeInputSchema,
    all_fields=True,
    description="Input for one Organization.type CodeableConcept entry — common codes: prov, dept, team, govt, ins, pay, edu, reli, crs, cg, bus, other.",
)
class OrgTypeInput:
    """Input for one Organization.type CodeableConcept entry."""


@strawberry.experimental.pydantic.input(
    model=OrgAliasInputSchema,
    all_fields=True,
    description="Input for one Organization.alias entry.",
)
class OrgAliasInput:
    """Input for one Organization.alias entry."""


@strawberry.experimental.pydantic.input(
    model=OrgTelecomInputSchema,
    all_fields=True,
    description="Input for one Organization.telecom entry. `system` and `value` are required.",
)
class OrgTelecomInput:
    """Input for one Organization.telecom entry."""


@strawberry.experimental.pydantic.input(
    model=OrgAddressInputSchema,
    all_fields=True,
    description="Input for one Organization.address entry.",
)
class OrgAddressInput:
    """Input for one Organization.address entry."""


@strawberry.experimental.pydantic.input(
    model=OrgContactTelecomInputSchema,
    all_fields=True,
    description="Input for one telecom entry nested inside an Organization.contact person.",
)
class OrgContactTelecomInput:
    """Input for one telecom entry nested inside an Organization.contact person."""


@strawberry.experimental.pydantic.input(
    model=OrgContactInputSchema,
    all_fields=True,
    description="Input for one Organization.contact person, with a nested telecom array.",
)
class OrgContactInput:
    """Input for one Organization.contact person (references OrgContactTelecomInput)."""


@strawberry.experimental.pydantic.input(
    model=OrgEndpointInputSchema,
    all_fields=True,
    description="Input for one Organization.endpoint reference.",
)
class OrgEndpointInput:
    """Input for one Organization.endpoint reference."""


@strawberry.experimental.pydantic.input(
    model=RegisterOrgSchema,
    all_fields=True,
    description=(
        "Input for `registerOrganization`. Enforces `name` and `type` even though FHIR itself "
        "leaves them optional. Deduplicates by name — a case-insensitive match against an "
        "existing organization raises a GraphQL error with `extensions.code == 409`. "
        "`createdBy` is stamped automatically from the caller's JWT — do not supply it."
    ),
)
class RegisterOrgInput:
    """Input for `registerOrganization` — mirrors RegisterOrgSchema exactly, including its `name`/`type` requirement."""


@strawberry.experimental.pydantic.input(
    model=PatchOrgSchema,
    all_fields=True,
    description=(
        "Input for `updateOrganization`. Only `active`, `name`, and `partofDisplay` are "
        "patchable — child arrays (identifier, type, alias, telecom, address, contact, "
        "endpoint) are not; delete and re-create them instead. At least one field must be set."
    ),
)
class PatchOrgInput:
    """Input for `updateOrganization` — every field optional, at least one must be set (enforced in OrganizationsService)."""


# `ListOrgsSchema` / `MeOrgsSchema` are query-parameter schemas, not mutation
# payloads — GraphQL convention is to expose filters as plain field arguments
# rather than a wrapped input type, so these two are intentionally NOT wrapped
# here. See app/gql/organization/queries.py, which imports them directly from
# app.schemas.organization.input.
__all__ = [
    "OrgIdentifierInput",
    "OrgTypeInput",
    "OrgAliasInput",
    "OrgTelecomInput",
    "OrgAddressInput",
    "OrgContactTelecomInput",
    "OrgContactInput",
    "OrgEndpointInput",
    "RegisterOrgInput",
    "PatchOrgInput",
]
