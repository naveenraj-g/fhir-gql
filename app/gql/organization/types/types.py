"""
GraphQL response (output) types for the Organization resource, derived from
the existing Pydantic schemas in app/schemas/organization/response.py via
`strawberry.experimental.pydantic`. Input types live in
app/gql/organization/types/input.py — this split mirrors the
app/schemas/organization/{response,input}.py split one layer down.

Every type below carries an explicit `description=` since Strawberry does
NOT promote a class's Python docstring into the GraphQL schema automatically
— `description=` is what shows up in GraphiQL's introspection-based "Docs"
panel.

Naming convention: `<X>Response` (Pydantic) -> `<X>Type` (GraphQL object type).

Declaration order matters: `strawberry.experimental.pydantic` resolves a
wrapped model's nested-model fields by looking up the nested Pydantic class
in its own registry, which only has entries for classes wrapped *before*
the parent is declared. Leaf sub-resource types are therefore declared
first, the top-level `OrgType` / `PaginatedOrgType` last.
"""

import strawberry

from app.schemas.organization.response import (
    OrgAddressResponse,
    OrgAliasResponse,
    OrgContactResponse,
    OrgContactTelecomResponse,
    OrgEndpointResponse,
    OrgIdentifierResponse,
    OrgResponse,
    OrgTelecomResponse,
    OrgTypeResponse,
    PaginatedOrgResponse,
)

# ── Response (output) types — leaf sub-resources first ───────────────────────


@strawberry.experimental.pydantic.type(
    model=OrgIdentifierResponse,
    all_fields=True,
    description="A single Organization.identifier entry.",
)
class OrgIdentifierType:
    """A single Organization.identifier entry."""


@strawberry.experimental.pydantic.type(
    model=OrgTypeResponse,
    all_fields=True,
    description="A single Organization.type CodeableConcept entry categorising the organization (e.g. prov = Healthcare Provider, dept = Hospital Department).",
)
class OrgTypeType:
    """A single Organization.type CodeableConcept entry (e.g. prov, dept)."""


@strawberry.experimental.pydantic.type(
    model=OrgAliasResponse,
    all_fields=True,
    description="A single Organization.alias entry — an alternative name the organization is or was known by.",
)
class OrgAliasType:
    """A single Organization.alias entry."""


@strawberry.experimental.pydantic.type(
    model=OrgTelecomResponse,
    all_fields=True,
    description="A single Organization.telecom (ContactPoint) entry — phone, email, fax, etc.",
)
class OrgTelecomType:
    """A single Organization.telecom (ContactPoint) entry."""


@strawberry.experimental.pydantic.type(
    model=OrgAddressResponse,
    all_fields=True,
    description="A single Organization.address entry.",
)
class OrgAddressType:
    """A single Organization.address entry."""


@strawberry.experimental.pydantic.type(
    model=OrgContactTelecomResponse,
    all_fields=True,
    description="A single telecom entry nested inside an Organization.contact person.",
)
class OrgContactTelecomType:
    """A single telecom entry nested inside an Organization.contact person."""


@strawberry.experimental.pydantic.type(
    model=OrgContactResponse,
    all_fields=True,
    description="A single Organization.contact person — someone contactable about the organization in a specific capacity (admin, billing, clinical, etc.), with nested telecom entries.",
)
class OrgContactType:
    """A single Organization.contact person (references OrgContactTelecomType)."""


@strawberry.experimental.pydantic.type(
    model=OrgEndpointResponse,
    all_fields=True,
    description="A single Organization.endpoint reference to a technical endpoint (e.g. SMART on FHIR, Direct Messaging) associated with the organization.",
)
class OrgEndpointType:
    """A single Organization.endpoint reference."""


@strawberry.experimental.pydantic.type(
    model=OrgResponse,
    all_fields=True,
    description="A full Organization resource, including all nested sub-resource arrays (identifiers, types, aliases, telecoms, addresses, contacts, endpoints).",
)
class OrgType:
    """A full Organization resource, including all nested sub-resource arrays."""


@strawberry.experimental.pydantic.type(
    model=PaginatedOrgResponse,
    all_fields=True,
    description="Paginated envelope returned by the `organizations` query — `data` for the current page, plus `total`/`limit`/`offset` for pagination.",
)
class PaginatedOrgType:
    """Paginated envelope returned by the `organizations` list query."""


__all__ = [
    "OrgIdentifierType",
    "OrgTypeType",
    "OrgAliasType",
    "OrgTelecomType",
    "OrgAddressType",
    "OrgContactTelecomType",
    "OrgContactType",
    "OrgEndpointType",
    "OrgType",
    "PaginatedOrgType",
]
