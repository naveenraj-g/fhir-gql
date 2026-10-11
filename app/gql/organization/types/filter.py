"""
GraphQL filter input for the `organizations` list query.

Bundles every Organization search parameter (matching fhir-server's
Medplum-mirrored Organization search parameter set — see
app/routers/organization/core.py's list_organizations()) into a single
input object, GraphQL's idiomatic convention for list-query filters (a
`filter`/`where` argument) rather than a long flat argument list.

Hand-written as a plain `@strawberry.input` (not derived from
ListOrganizationsSchema via `strawberry.experimental.pydantic.input`)
because ListOrganizationsSchema also carries `sort`/`total_mode`/`limit`/
`offset` — pagination/ordering concerns, not filters — which stay as
separate top-level arguments on the `organizations` query in queries.py
rather than living inside this input.

Every field carries its own `description=` — same documentation bar as
fhir-server's per-parameter `Query()` descriptions — since GraphQL only
surfaces per-field/per-argument descriptions when set explicitly, never a
class docstring.
"""

import strawberry

# Registers AddressUse as a GraphQL enum (side-effect import) — required
# before referencing AddressUseEnum below.
import app.gql.enums  # noqa: F401
from app.gql.enums import AddressUseEnum


@strawberry.input(description="Filter arguments for the `organizations` query.")
class OrganizationFilterInput:
    name: str | None = strawberry.field(
        default=None,
        description="Partial match against organization name or any alias.",
    )
    active: bool | None = strawberry.field(
        default=None, description="Filter by active status."
    )
    identifier: str | None = strawberry.field(
        default=None, description="Exact match on a business identifier value."
    )
    org_type: str | None = strawberry.field(
        default=None, description="Exact match on a coded organization type."
    )
    address: str | None = strawberry.field(
        default=None,
        description="Partial match against any Address sub-field (line, city, district, state, country, postalCode, text).",
    )
    address_city: str | None = strawberry.field(
        default=None, description="Filter by address city — partial match."
    )
    address_state: str | None = strawberry.field(
        default=None, description="Filter by address state — partial match."
    )
    address_postal_code: str | None = strawberry.field(
        default=None, description="Filter by address postal code — exact match."
    )
    address_country: str | None = strawberry.field(
        default=None, description="Filter by address country — partial match."
    )
    address_use: AddressUseEnum | None = strawberry.field(
        default=None, description="home|work|temp|old|billing."
    )
    partof: str | None = strawberry.field(
        default=None,
        description="FHIR reference string, e.g. 'Organization/190001'.",
    )
    endpoint: str | None = strawberry.field(
        default=None, description="FHIR reference string, e.g. 'Endpoint/1'."
    )


__all__ = ["OrganizationFilterInput"]
