"""
The FHIR R4 Location search parameters
(https://www.hl7.org/fhir/R4/location.html#search), including `near`, as
GraphQL arguments, and `fhir_filters()`, which maps those arguments back to
FHIR parameter names. Used by both search resolvers in
app.gql.location.queries, so their argument lists can't drift apart.

The parameters shared by every resource (IdArg, ParamsArg, CountArg, ...)
live in app.gql.search.
"""

from typing import Annotated

import strawberry

from app.gql.search import REFERENCE_DOC, STRING_DOC, TOKEN_DOC

# ── Argument declarations ────────────────────────────────────────────────────
# Location's own search parameters, declared once and reused by both search
# resolvers. The common/result parameters are shared — see app.gql.search.

NameArg = Annotated[
    str | None,
    strawberry.argument(description="Location.name or any alias." + STRING_DOC),
]
IdentifierArg = Annotated[
    str | None, strawberry.argument(description="Location.identifier." + TOKEN_DOC)
]
StatusArg = Annotated[
    str | None,
    strawberry.argument(
        description="Location.status: active | suspended | inactive." + TOKEN_DOC
    ),
]
OperationalStatusArg = Annotated[
    str | None,
    strawberry.argument(
        name="operationalStatus",
        description="Location.operationalStatus (typically a bed/room's, e.g. `U` unoccupied, `K` contaminated)."
        + TOKEN_DOC,
    ),
]
TypeArg = Annotated[
    str | None,
    strawberry.argument(
        name="type", description="Location.type (any coding)." + TOKEN_DOC
    ),
]
AddressArg = Annotated[
    str | None,
    strawberry.argument(
        description="Any Address part (line, city, district, state, country, postalCode, text)."
        + STRING_DOC
    ),
]
AddressCityArg = Annotated[
    str | None, strawberry.argument(description="Location.address.city." + STRING_DOC)
]
AddressStateArg = Annotated[
    str | None, strawberry.argument(description="Location.address.state." + STRING_DOC)
]
AddressPostalCodeArg = Annotated[
    str | None,
    strawberry.argument(description="Location.address.postalCode." + STRING_DOC),
]
AddressCountryArg = Annotated[
    str | None,
    strawberry.argument(description="Location.address.country." + STRING_DOC),
]
AddressUseArg = Annotated[
    str | None,
    strawberry.argument(
        description="Location.address.use: home | work | temp | old | billing."
        + TOKEN_DOC
    ),
]
OrganizationArg = Annotated[
    str | None,
    strawberry.argument(
        description="Location.managingOrganization."
        + REFERENCE_DOC
        + " Chain into the Organization's own parameters via `params`, e.g. `organization.name`."
    ),
]
PartofArg = Annotated[
    str | None,
    strawberry.argument(
        description="Location.partOf (the containing location)."
        + REFERENCE_DOC
        + " `partof:below` / `partof:above` (via `params`) walk the whole hierarchy."
    ),
]
EndpointArg = Annotated[
    str | None, strawberry.argument(description="Location.endpoint." + REFERENCE_DOC)
]
NearArg = Annotated[
    str | None,
    strawberry.argument(
        description=(
            "FHIR `near`: `latitude|longitude|distance|units` (WGS84), e.g. `42.2565|-83.6948|11.2|km`. "
            "Units km (default), m, mi / [mi_i], ft / [ft_i]; without a distance the server uses 50 km. "
            "Each match's distance is returned in `distances`."
        )
    ),
]
IncludeArg = Annotated[
    list[str] | None,
    strawberry.argument(
        description=(
            "FHIR `_include`: also return resources the matches point to — `Location:organization` "
            "(managing organization), `Location:partof` (containing location), or `*`."
        )
    ),
]
RevincludeArg = Annotated[
    list[str] | None,
    strawberry.argument(
        description="FHIR `_revinclude`: also return resources that point at the matches — `Location:partof` (locations inside)."
    ),
]


def fhir_filters(
    *,
    id,
    last_updated,
    name,
    identifier,
    status,
    operational_status,
    type,
    address,
    address_city,
    address_state,
    address_postal_code,
    address_country,
    address_use,
    organization,
    partof,
    endpoint,
    near,
) -> dict[str, str | None]:
    """Typed GraphQL arguments -> {FHIR search parameter name: value}."""
    return {
        "_id": id,
        "_lastUpdated": last_updated,
        "name": name,
        "identifier": identifier,
        "status": status,
        "operational-status": operational_status,
        "type": type,
        "address": address,
        "address-city": address_city,
        "address-state": address_state,
        "address-postalcode": address_postal_code,
        "address-country": address_country,
        "address-use": address_use,
        "organization": organization,
        "partof": partof,
        "endpoint": endpoint,
        "near": near,
    }
