"""
GraphQL response (output) types for the Organization resource, derived from
the Pydantic schemas in the app/schemas/organization/response/ package via
`strawberry.experimental.pydantic`. Input types live in
app/gql/organization/types/input.py — this split mirrors the
app/schemas/organization/{response,input}/ package split one layer down.

Every type below carries an explicit `description=` since Strawberry does
NOT promote a class's Python docstring into the GraphQL schema automatically
— `description=` is what shows up in GraphiQL's introspection-based "Docs"
panel.

Naming convention: `<X>Response` (Pydantic) -> `<X>Type` (GraphQL object type).

Declaration order matters: `strawberry.experimental.pydantic` resolves a
wrapped model's nested-model fields by looking up the nested Pydantic class
in its own registry, which only has entries for classes wrapped *before*
the parent is declared. Leaf sub-resource types are therefore declared
first, the top-level `OrganizationType` / `PaginatedOrganizationType` last.
"""

import strawberry
from strawberry.scalars import JSON

from app.connectors.internal.schemas.organization.response import (
    OrganizationAddressResponse,
    OrganizationAliasResponse,
    OrganizationCodingResponse,
    OrganizationContactResponse,
    OrganizationContactTelecomResponse,
    OrganizationEndpointResponse,
    OrganizationIdentifierResponse,
    OrganizationResponse,
    OrganizationTelecomResponse,
    OrganizationTypeResponse,
    PaginatedOrganizationResponse,
)

# ── Response (output) types — leaf sub-resources first ───────────────────────


@strawberry.experimental.pydantic.type(
    model=OrganizationCodingResponse,
    all_fields=True,
    description="A single Coding entry — reused by Organization.type, Organization.identifier.type, and Organization.contact.purpose.",
)
class OrganizationCodingType:
    """A single Coding entry (system/version/code/display/userSelected)."""


@strawberry.experimental.pydantic.type(
    model=OrganizationIdentifierResponse,
    all_fields=True,
    description="A single Organization.identifier entry.",
)
class OrganizationIdentifierType:
    """A single Organization.identifier entry."""


@strawberry.experimental.pydantic.type(
    model=OrganizationTypeResponse,
    all_fields=True,
    description="A single Organization.type CodeableConcept entry categorising the organization (e.g. prov = Healthcare Provider, dept = Hospital Department).",
)
class OrganizationTypeType:
    """A single Organization.type CodeableConcept entry (e.g. prov, dept)."""


@strawberry.experimental.pydantic.type(
    model=OrganizationAliasResponse,
    all_fields=True,
    description="A single Organization.alias entry — an alternative name the organization is or was known by.",
)
class OrganizationAliasType:
    """A single Organization.alias entry."""


@strawberry.experimental.pydantic.type(
    model=OrganizationTelecomResponse,
    all_fields=True,
    description="A single Organization.telecom (ContactPoint) entry — phone, email, fax, etc.",
)
class OrganizationTelecomType:
    """A single Organization.telecom (ContactPoint) entry."""


@strawberry.experimental.pydantic.type(
    model=OrganizationAddressResponse,
    all_fields=True,
    description="A single Organization.address entry.",
)
class OrganizationAddressType:
    """A single Organization.address entry."""


@strawberry.experimental.pydantic.type(
    model=OrganizationContactTelecomResponse,
    all_fields=True,
    description="A single telecom entry nested inside an Organization.contact person.",
)
class OrganizationContactTelecomType:
    """A single telecom entry nested inside an Organization.contact person."""


@strawberry.experimental.pydantic.type(
    model=OrganizationContactResponse,
    all_fields=True,
    description="A single Organization.contact person — someone contactable about the organization in a specific capacity (admin, billing, clinical, etc.), with nested telecom entries.",
)
class OrganizationContactType:
    """A single Organization.contact person (references OrganizationContactTelecomType)."""


@strawberry.experimental.pydantic.type(
    model=OrganizationEndpointResponse,
    all_fields=True,
    description="A single Organization.endpoint reference to a technical endpoint (e.g. SMART on FHIR, Direct Messaging) associated with the organization.",
)
class OrganizationEndpointType:
    """A single Organization.endpoint reference."""


@strawberry.experimental.pydantic.type(
    model=OrganizationResponse,
    all_fields=True,
    description="A full Organization resource, including all nested sub-resource arrays (identifiers, types, aliases, telecoms, addresses, contacts, endpoints).",
)
class OrganizationType:
    """A full Organization resource, including all nested sub-resource arrays."""

    # Pydantic types this as list[dict] — strawberry's pydantic integration
    # can't auto-map a bare `dict` to a GraphQL type, so it's overridden
    # explicitly with the JSON scalar here (all_fields=True still respects
    # an explicit annotation over auto-deriving one).
    extension: JSON | None


@strawberry.experimental.pydantic.type(
    model=PaginatedOrganizationResponse,
    all_fields=True,
    description="Paginated envelope returned by the `organizations` query — `data` for the current page, plus `total`/`limit`/`offset` for pagination.",
)
class PaginatedOrganizationType:
    """Paginated envelope returned by the `organizations` list query."""


__all__ = [
    "OrganizationAddressType",
    "OrganizationAliasType",
    "OrganizationCodingType",
    "OrganizationContactTelecomType",
    "OrganizationContactType",
    "OrganizationEndpointType",
    "OrganizationIdentifierType",
    "OrganizationTelecomType",
    "OrganizationType",
    "OrganizationTypeType",
    "PaginatedOrganizationType",
]
