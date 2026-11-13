"""
GraphQL result type for `searchFhirOrganizations` — one FHIR R4 searchset
Bundle, reshaped for GraphQL: the matches as typed Organizations, the
`_include`/`_revinclude`d resources, the total, paging, and any warnings
the backend reported about the search.

`getFhirOrganizations` (the older, list-only query) returns just the
matches; this type is what exposes everything else a FHIR search returns.
"""

import strawberry
from strawberry.scalars import JSON

from app.gql.organization.types.response import FhirOrganizationType
from app.gql.search import FhirBundleLinkType


@strawberry.type(
    description=(
        "One page of a FHIR R4 Organization search (a searchset Bundle): the matching "
        "Organizations, the resources added by `include`/`revinclude`, the total match "
        "count, paging, and any warnings about the search."
    )
)
class FhirOrganizationSearchResult:
    """See module docstring."""

    # Bundle.total — every match across all pages, not counting included
    # resources. Null when `total: NONE` was requested.
    total: int | None = strawberry.field(
        description="Number of matches across all pages (included resources not counted). Null with `total: NONE`."
    )
    # Bundle.entry[search.mode=match], typed. With `_summary`/`_elements`
    # in `params`, each is a subset (tagged SUBSETTED in meta.tag).
    organizations: list[FhirOrganizationType] = strawberry.field(
        description="The Organizations that matched, for this page."
    )
    # The included resources that are Organizations (e.g. from
    # `Organization:partof`), typed like the matches.
    included_organizations: list[FhirOrganizationType] = strawberry.field(
        description="Organizations added by `include`/`revinclude` (e.g. parents via `Organization:partof`)."
    )
    # Every included resource as raw FHIR JSON, whatever its type — an
    # include can pull in resource types this schema has no GraphQL type for.
    included: list[JSON] = strawberry.field(
        description="Every resource added by `include`/`revinclude`, as raw FHIR R4 JSON (any resource type)."
    )
    # Pass back as `offset` to fetch the next page; null on the last page.
    next_offset: int | None = strawberry.field(
        description="`offset` of the next page, or null when this is the last page."
    )
    # Bundle.link — the backend's own paging URLs (self shows the search as applied).
    links: list[FhirBundleLinkType] = strawberry.field(
        description="Bundle.link: self (the search as the server applied it), first, previous, next, last."
    )
    # OperationOutcome diagnostics from search.mode=outcome entries — e.g.
    # an unknown search parameter the backend ignored.
    warnings: list[str] = strawberry.field(
        description="Warnings from the server about this search, e.g. an unknown parameter that was ignored."
    )
