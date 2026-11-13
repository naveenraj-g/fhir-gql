"""
GraphQL result type for `searchFhirLocations` — one FHIR R4 searchset
Bundle, reshaped for GraphQL (same arrangement as
app.gql.organization.types.search): the matches as typed Locations, the
`_include`/`_revinclude`d resources (typed when they're Locations or
Organizations, raw FHIR JSON always), the total, paging, warnings — and,
for a `near` search, each match's distance.
"""

import strawberry
from strawberry.scalars import JSON

from app.gql.location.types.response import FhirLocationType
from app.gql.organization.types.response import FhirOrganizationType
from app.gql.search import FhirBundleLinkType


@strawberry.type(description="How far a `near` search match is from the search point.")
class FhirLocationDistanceType:
    """One match's http://hl7.org/fhir/StructureDefinition/location-distance."""

    # The matched Location's FHIR id.
    location_id: str = strawberry.field(description="The matched Location's id.")
    # Distance to the (closest) search point.
    value: float = strawberry.field(description="Distance to the search point (the closest one, if several).")
    # Unit as given in the search (km by default).
    unit: str = strawberry.field(description="Unit of `value` — the unit used in the `near` value (km by default).")


@strawberry.type(
    description=(
        "One page of a FHIR R4 Location search (a searchset Bundle): the matching Locations, the "
        "resources added by `include`/`revinclude`, the total match count, paging, warnings, and "
        "— for a `near` search — each match's distance."
    )
)
class FhirLocationSearchResult:
    """See module docstring."""

    # Bundle.total — every match across all pages (includes not counted);
    # null when `total: NONE` was requested.
    total: int | None = strawberry.field(
        description="Number of matches across all pages (included resources not counted). Null with `total: NONE`."
    )
    # Bundle.entry[search.mode=match], typed.
    locations: list[FhirLocationType] = strawberry.field(description="The Locations that matched, for this page.")
    # Included Locations (e.g. containers via `Location:partof`).
    included_locations: list[FhirLocationType] = strawberry.field(
        description="Locations added by `include`/`revinclude` (e.g. the containing location via `Location:partof`)."
    )
    # Included Organizations (`Location:organization`).
    included_organizations: list[FhirOrganizationType] = strawberry.field(
        description="Organizations added by `include` (the managing organization via `Location:organization`)."
    )
    # Every included resource as raw FHIR JSON, whatever its type.
    included: list[JSON] = strawberry.field(
        description="Every resource added by `include`/`revinclude`, as raw FHIR R4 JSON (any resource type)."
    )
    # Per-match distances for a `near` search; empty otherwise.
    distances: list[FhirLocationDistanceType] = strawberry.field(
        description="For a `near` search: each match's distance from the search point. Empty otherwise."
    )
    # Pass back as `offset` to fetch the next page; null on the last page.
    next_offset: int | None = strawberry.field(
        description="`offset` of the next page, or null when this is the last page."
    )
    # Bundle.link — the backend's own paging URLs.
    links: list[FhirBundleLinkType] = strawberry.field(
        description="Bundle.link: self (the search as the server applied it), first, previous, next, last."
    )
    # OperationOutcome diagnostics from search.mode=outcome entries.
    warnings: list[str] = strawberry.field(
        description="Warnings from the server about this search, e.g. an unknown parameter that was ignored."
    )
