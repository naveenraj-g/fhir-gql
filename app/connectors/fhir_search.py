"""
Shared FHIR R4 search plumbing for every connector whose backend speaks
genuine FHIR R4 search (https://www.hl7.org/fhir/R4/search.html).

Both of today's backends do: Medplum natively, and fhir-server since
Organization moved onto its resource-agnostic search engine
(fhir-server's app/fhir/search/). So the GraphQL layer's search arguments
map onto the wire *identically* for both — the only per-connector
difference left is the URL path, which each translator still owns
(`list_path()`). Rather than copy the same mapping into every translator,
both translators delegate to `build_search_params()` here.

The second half of this module, `parse_searchset()`, turns the searchset
Bundle a FHIR search returns back into the pieces a GraphQL result type
exposes: the matches, the `_include`/`_revinclude`d resources, the total,
the paging links, and any OperationOutcome warnings (e.g. a search
parameter the backend ignored).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse


def build_search_params(
    *,
    filters: dict[str, str | None],
    params: list[tuple[str, str]] | None = None,
    count: int | None = None,
    offset: int | None = None,
    sort: str | None = None,
    total: str | None = None,
    include: list[str] | None = None,
    revinclude: list[str] | None = None,
) -> dict[str, list[str]]:
    """
    Assemble one FHIR search's query parameters.

    Returns `{name: [value, ...]}` — a list per name because FHIR search
    *repeats* a parameter to AND it (`name=a&name=b`), and httpx renders a
    list value as exactly that repeated key. Both connectors' `get()` pass
    the dict straight to httpx.

    Args:
        filters:    the typed GraphQL arguments, already keyed by their real
                    FHIR search parameter name (`address-city`, not
                    `address_city`). None means "not supplied" and is
                    dropped; a supplied value is sent verbatim, so FHIR's
                    own value syntax (comma = OR, `system|code`, date
                    prefixes like `ge2024-01-01`) works unchanged.
        params:     the generic escape hatch — any FHIR parameter,
                    including a modifier or chain in its name
                    (`name:exact`, `partof.name`, `_lastUpdated`), as
                    (name, value) pairs. Order is kept; a repeated name ANDs.
        count:      page size, sent as `_count`.
        offset:     matches to skip, sent as `_offset` (fhir-server and
                    Medplum both page this way).
        sort:       `_sort` value, e.g. `-_lastUpdated,name`.
        total:      `_total` (`accurate` | `estimate` | `none`).
        include:    `_include` values, e.g. `Organization:partof`.
        revinclude: `_revinclude` values.
    """
    # dict preserves insertion order, so the wire order follows the
    # caller's order: typed filters, then the generic params, then the
    # result parameters.
    out: dict[str, list[str]] = {}

    def add(name: str, value: str) -> None:
        """Append one occurrence of `name` (repeat = AND in FHIR)."""
        out.setdefault(name, []).append(value)

    # Typed filters: skip the unsupplied ones (None). An empty string is
    # also skipped — FHIR says an empty parameter value is ignored anyway,
    # so not sending it keeps the backend's self link clean.
    for name, value in filters.items():
        if value is not None and value != "":
            add(name, value)

    # Generic (name, value) pairs pass through untouched — this is how a
    # caller reaches every modifier and chain without the GraphQL schema
    # having to declare each one as its own argument.
    for name, value in params or []:
        add(name, value)

    # Result parameters. Integers go out as strings — query strings carry
    # only text, and a list value must be homogeneous for httpx.
    if count is not None:
        add("_count", str(count))
    if offset is not None:
        add("_offset", str(offset))
    if sort:
        add("_sort", sort)
    if total:
        add("_total", total)
    for value in include or []:
        add("_include", value)
    for value in revinclude or []:
        add("_revinclude", value)
    return out


@dataclass
class Searchset:
    """A searchset Bundle, unpacked for a GraphQL result type."""

    # Bundle.entry where search.mode == "match" — the resources that
    # matched the search, for the current page.
    matches: list[dict] = field(default_factory=list)
    # Bundle.entry.search.extension of each match, parallel to `matches`
    # (e.g. Location `near`'s location-distance); [] when it has none.
    match_extensions: list[list[dict]] = field(default_factory=list)
    # search.mode == "include" — added by _include/_revinclude. Any
    # resource type (an _include can pull in e.g. an Endpoint).
    included: list[dict] = field(default_factory=list)
    # Bundle.total — every match across all pages; None when the backend
    # omitted it (`_total=none`).
    total: int | None = None
    # Bundle.link as (relation, url) — self / first / previous / next / last.
    links: list[tuple[str, str]] = field(default_factory=list)
    # The `_offset` of the next page, parsed from the `next` link, or None
    # on the last page — so a GraphQL client can page without parsing URLs.
    next_offset: int | None = None
    # diagnostics of every OperationOutcome issue in a search.mode=outcome
    # entry (e.g. "unknown search parameter 'x' was ignored").
    warnings: list[str] = field(default_factory=list)


def _offset_of(url: str) -> int | None:
    """The `_offset` query parameter of a paging link, if it has one."""
    values = parse_qs(urlparse(url).query).get("_offset")
    if not values:
        return None
    try:
        return int(values[0])
    except ValueError:
        # A backend using an opaque paging token instead of _offset — no
        # numeric offset to report; the raw link is still exposed.
        return None


def parse_searchset(bundle: dict) -> Searchset:
    """
    Split a searchset Bundle into matches / included / outcome warnings.

    An entry with no `search.mode` is treated as a match — R4 makes the
    field mandatory only for servers that also return non-match entries,
    and a backend that never does may leave it out. A response that isn't a
    Bundle at all is treated as a single match (defensive; neither backend
    does this for a collection GET).
    """
    if bundle.get("resourceType") != "Bundle":
        return Searchset(matches=[bundle], match_extensions=[[]], total=1)

    result = Searchset(total=bundle.get("total"))
    for entry in bundle.get("entry") or []:
        resource = entry.get("resource") or {}
        mode = (entry.get("search") or {}).get("mode", "match")
        if mode == "include":
            result.included.append(resource)
        elif mode == "outcome" or resource.get("resourceType") == "OperationOutcome":
            # Surface each issue's human-readable text as one warning line.
            for issue in resource.get("issue") or []:
                text = issue.get("diagnostics") or (issue.get("details") or {}).get("text")
                if text:
                    result.warnings.append(text)
        else:
            result.matches.append(resource)
            result.match_extensions.append((entry.get("search") or {}).get("extension") or [])

    for link in bundle.get("link") or []:
        relation, url = link.get("relation"), link.get("url")
        if relation and url:
            result.links.append((relation, url))
            if relation == "next":
                result.next_offset = _offset_of(url)
    return result
