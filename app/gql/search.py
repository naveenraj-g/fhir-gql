"""
GraphQL types shared by every resource's FHIR R4 search query
(https://www.hl7.org/fhir/R4/search.html) — not resource-specific, so a
future resource's `searchFhirX` query reuses them rather than redeclaring
them.

- FhirSearchParamInput: the generic "any FHIR search parameter" argument —
  how a GraphQL caller reaches modifiers (`name:exact`), chains
  (`partof.name`) and common parameters (`_lastUpdated`) that would
  otherwise each need their own GraphQL argument.
- FhirSearchTotal: `_total`.
- FhirBundleLinkType: one Bundle.link (self / first / previous / next / last).
- The common/result-parameter argument declarations (IdArg, ParamsArg,
  CountArg, ...) and run_fhir_search(), the resolver plumbing every
  resource's search query shares.
"""

from enum import Enum
from typing import Annotated

import strawberry


@strawberry.input(
    description=(
        "One FHIR R4 search parameter occurrence, exactly as it would appear in a FHIR "
        "query string. `name` may carry a modifier or a chain — e.g. `name:exact`, "
        "`name:contains`, `identifier:of-type`, `type:in`, `partof:below`, `partof.name`, "
        "`address-city:missing`, `_lastUpdated`, `_id`, `_summary`, `_elements`. `value` uses "
        "FHIR value syntax: comma = OR (`a,b`), `system|code` for tokens, date prefixes "
        "(`ge2024-01-01`). Repeating the same `name` ANDs the occurrences. See "
        "https://www.hl7.org/fhir/R4/search.html."
    )
)
class FhirSearchParamInput:
    """A single (name, value) search parameter, passed to the backend verbatim."""

    # The FHIR search parameter name, optionally with `:modifier` or a
    # `.chain` — sent as the query-string key unchanged.
    name: str = strawberry.field(
        description="FHIR search parameter name, optionally with `:modifier` or `.chained` parameter."
    )
    # The value in FHIR search syntax — sent as the query-string value unchanged.
    value: str = strawberry.field(description="Value in FHIR search syntax.")


@strawberry.enum(description="FHIR `_total`: how hard the server should try to count all matches.")
class FhirSearchTotal(Enum):
    """Maps 1:1 onto FHIR's `_total` values (the enum value is what goes on the wire)."""

    # Count every match (the default on fhir-server).
    ACCURATE = "accurate"
    # An estimate is acceptable (fhir-server treats this as accurate).
    ESTIMATE = "estimate"
    # Skip counting entirely — `total` comes back null; cheaper on large data.
    NONE = "none"


@strawberry.type(description="One FHIR Bundle.link — a URL for a page of the same search.")
class FhirBundleLinkType:
    """Bundle.link: `relation` is self (the search as the server applied it), first,
    previous, next or last."""

    # self / first / previous / next / last.
    relation: str = strawberry.field(description="self, first, previous, next or last.")
    # The backend's own URL for that page — informational for GraphQL
    # callers, who page with `offset`/`nextOffset` instead.
    url: str = strawberry.field(description="The backend's URL for that page of results.")


def search_param_pairs(params: list[FhirSearchParamInput] | None) -> list[tuple[str, str]]:
    """GraphQL FhirSearchParamInput list -> the (name, value) pairs
    app.connectors.fhir_search.build_search_params() takes."""
    return [(p.name, p.value) for p in params or []]


# ── Argument declarations shared by every resource's search query ────────────
# The FHIR common/result parameters mean the same on every resource, so they
# are declared once here (descriptions included — GraphQL clients and AI
# tools read them) and reused by each resource's search resolvers.

IdArg = Annotated[
    str | None,
    strawberry.argument(description="FHIR `_id`: the resource id(s), comma-separated for OR."),
]
LastUpdatedArg = Annotated[
    str | None,
    strawberry.argument(
        description=(
            "FHIR `_lastUpdated`: a date with an optional prefix (eq, ne, gt, lt, ge, le, sa, eb, ap), "
            "e.g. `ge2024-01-01`. For a range, add a second occurrence via `params`."
        )
    ),
]
ParamsArg = Annotated[
    list[FhirSearchParamInput] | None,
    strawberry.argument(
        description=(
            "Any other FHIR search parameters, as (name, value) pairs sent verbatim — modifiers "
            "(`name:exact`, `name:contains`, `identifier:of-type`, `type:text`, `type:in`, "
            "`partof:below`, `address-city:missing`), chains (`partof.name`), `_summary`, "
            "`_elements`, `_include:iterate`, or a second occurrence of a parameter (repeat = AND)."
        )
    ),
]
CountArg = Annotated[int, strawberry.argument(description="Page size — FHIR `_count` (default 50).")]
OffsetArg = Annotated[int, strawberry.argument(description="Matches to skip — `_offset` (default 0).")]
SortArg = Annotated[
    str | None,
    strawberry.argument(
        description=(
            "FHIR `_sort`: comma-separated parameter names, `-` for descending — e.g. `name`, "
            "`-_lastUpdated`. Default: newest first."
        )
    ),
]
TotalArg = Annotated[
    FhirSearchTotal | None,
    strawberry.argument(description="FHIR `_total`. NONE skips the count (`total` comes back null)."),
]

# Shared description tails, one per FHIR search parameter type.
STRING_DOC = (
    " FHIR string search: matches when the field equals or starts with the value, "
    "ignoring case and accents. Comma-separated values are OR'd."
)
TOKEN_DOC = " FHIR token: `code`, `system|code`, `|code` (no system) or `system|`. Comma = OR."
REFERENCE_DOC = " FHIR reference: an id, `Type/id` or an absolute URL. Comma = OR."


async def run_fhir_search(
    info,
    *,
    resource: str,
    translator,
    filters: dict[str, str | None],
    params: list[FhirSearchParamInput] | None,
    count: int,
    offset: int,
    sort: str | None = None,
    total: FhirSearchTotal | None = None,
    include: list[str] | None = None,
    revinclude: list[str] | None = None,
):
    """
    Run one FHIR search against the active connector and unpack the
    searchset Bundle (app.connectors.fhir_search.Searchset).

    RBAC check (`<resource>:read`) first; then the connector's translator
    turns the arguments into its query parameters (identical for both of
    today's backends); then the Bundle is split into matches / included /
    warnings. A search the backend rejects (bad value, unsupported
    modifier) comes back as a 400 HTTPException, which the resolver's
    @translate_errors turns into a GraphQL error carrying the backend's
    message.
    """
    # Imported here: app.gql.context / permissions import the DI container,
    # which would otherwise make this shared types module heavy to import.
    from app.connectors.fhir_search import parse_searchset
    from app.gql.context import get_container
    from app.gql.permissions import require_gql_permission

    actor = require_gql_permission(info, resource, "read")
    connector = get_container(info).core.fhir_client()
    query = translator.search_params(
        filters=filters,
        params=search_param_pairs(params),
        count=count,
        offset=offset,
        sort=sort,
        # The enum's value is the FHIR wire value (accurate/estimate/none).
        total=total.value if total else None,
        include=include,
        revinclude=revinclude,
    )
    raw = await connector.get(translator.list_path(), params=query, accept=translator.accept, actor=actor)
    return parse_searchset(translator.from_wire(raw))


def bundle_links(searchset) -> list[FhirBundleLinkType]:
    """Searchset.links -> GraphQL FhirBundleLinkType list."""
    return [FhirBundleLinkType(relation=rel, url=url) for rel, url in searchset.links]
