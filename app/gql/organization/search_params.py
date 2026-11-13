"""
The FHIR R4 Organization search parameters
(https://www.hl7.org/fhir/R4/organization.html#search) as GraphQL
arguments, and `fhir_filters()`, which maps those arguments back to FHIR
parameter names. Used by both search resolvers in
app.gql.organization.queries, so their argument lists (and descriptions,
which GraphQL clients and AI tools read) can't drift apart.

The parameters shared by every resource (IdArg, ParamsArg, CountArg, ...)
live in app.gql.search.
"""

from typing import Annotated

import strawberry

from app.gql.search import REFERENCE_DOC, STRING_DOC, TOKEN_DOC

# ── Argument declarations ────────────────────────────────────────────────────
# Organization's own search parameters, declared once and reused by both
# search resolvers so their argument lists (and descriptions, which GraphQL
# clients and AI tools read) can't drift apart. The common/result parameters
# (IdArg, ParamsArg, CountArg, ...) are shared by every resource — see
# app.gql.search. Each typed filter is `str | None`: the FHIR value is
# passed to the backend exactly as written.

# The 13 FHIR R4 Organization search parameters.
NameArg = Annotated[
    str | None, strawberry.argument(description="Organization.name or any alias." + STRING_DOC)
]
PhoneticArg = Annotated[
    str | None,
    strawberry.argument(
        description="Organization.name, sounds-like (phonetic) match, e.g. `Generel Hospitel`."
    ),
]
ActiveArg = Annotated[bool | None, strawberry.argument(description="Organization.active.")]
IdentifierArg = Annotated[
    str | None, strawberry.argument(description="Organization.identifier." + TOKEN_DOC)
]
TypeArg = Annotated[
    str | None,
    strawberry.argument(name="type", description="Organization.type (any coding)." + TOKEN_DOC),
]
AddressArg = Annotated[
    str | None,
    strawberry.argument(
        description="Any Address part (line, city, district, state, country, postalCode, text)."
        + STRING_DOC
    ),
]
AddressCityArg = Annotated[
    str | None, strawberry.argument(description="Organization.address.city." + STRING_DOC)
]
AddressStateArg = Annotated[
    str | None, strawberry.argument(description="Organization.address.state." + STRING_DOC)
]
AddressPostalCodeArg = Annotated[
    str | None, strawberry.argument(description="Organization.address.postalCode." + STRING_DOC)
]
AddressCountryArg = Annotated[
    str | None, strawberry.argument(description="Organization.address.country." + STRING_DOC)
]
AddressUseArg = Annotated[
    str | None,
    strawberry.argument(
        description="Organization.address.use: home | work | temp | old | billing." + TOKEN_DOC
    ),
]
PartofArg = Annotated[
    str | None,
    strawberry.argument(description="Organization.partOf (the parent organization)." + REFERENCE_DOC),
]
EndpointArg = Annotated[
    str | None, strawberry.argument(description="Organization.endpoint." + REFERENCE_DOC)
]

IncludeArg = Annotated[
    list[str] | None,
    strawberry.argument(
        description=(
            "FHIR `_include`: also return resources the matches point to — `Organization:partof` "
            "(the parent) or `*`. For every ancestor, send `_include:iterate` via `params`."
        )
    ),
]
RevincludeArg = Annotated[
    list[str] | None,
    strawberry.argument(
        description=(
            "FHIR `_revinclude`: also return resources that point at the matches — "
            "`Organization:partof` (the children)."
        )
    ),
]


def fhir_filters(
    *,
    id: str | None,
    last_updated: str | None,
    name: str | None,
    phonetic: str | None,
    active: bool | None,
    identifier: str | None,
    type: str | None,
    address: str | None,
    address_city: str | None,
    address_state: str | None,
    address_postal_code: str | None,
    address_country: str | None,
    address_use: str | None,
    partof: str | None,
    endpoint: str | None,
) -> dict[str, str | None]:
    """Typed GraphQL arguments -> {FHIR search parameter name: value}.
    The only translation is the name, plus `active`'s bool -> the FHIR
    token text `true`/`false` (lower-case, as FHIR requires)."""
    return {
        "_id": id,
        "_lastUpdated": last_updated,
        "name": name,
        "phonetic": phonetic,
        "active": None if active is None else ("true" if active else "false"),
        "identifier": identifier,
        "type": type,
        "address": address,
        "address-city": address_city,
        "address-state": address_state,
        "address-postalcode": address_postal_code,
        "address-country": address_country,
        "address-use": address_use,
        "partof": partof,
        "endpoint": endpoint,
    }
