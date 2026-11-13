"""
internal (fhir-server) wire translation for the canonical FHIR R4
Organization shape used by app.gql.organization (see
app.connectors.base.OrganizationWireTranslator for the shared contract and
app.gql.organization's package docstring for the overall idea).

fhir-server's Organization create/patch body is genuine FHIR R4 JSON (the
same shape as its own `Accept: application/fhir+json` response), so the
canonical shape passes through unchanged in both directions — no body
translation at all. Its Organization search is genuine FHIR R4 search too
(every R4 search parameter and modifier, `_count`/`_offset`, `_sort`, ...),
so the only thing that still differs from FHIR R4 conventions is
fhir-server's own path (`/organizations`, not `/Organization`).

PATCH stays a plain partial-object body (merge-patch on top-level
elements: a supplied list or `partOf` replaces the stored value wholesale)
— unlike Medplum, which needs an RFC 6902 JSON Patch array.
"""

# Shared with the medplum translator: both backends speak FHIR R4 search.
from app.connectors.fhir_search import build_search_params


class InternalOrganizationTranslator:
    """internal (fhir-server). See module docstring for what differs from
    genuine FHIR R4 conventions."""

    accept = "application/fhir+json"

    def item_path(self, organization_id: str) -> str:
        return f"/organizations/{organization_id}"

    def list_path(self) -> str:
        return "/organizations"

    def search_params(self, **search) -> dict[str, list[str]]:
        """FHIR R4 search arguments -> query parameters. fhir-server
        implements genuine FHIR R4 search for Organization (its
        app/fhir/search engine), so this is
        app.connectors.fhir_search.build_search_params() unchanged — see
        that function for the accepted keyword arguments (`filters`,
        `params`, `count`, `offset`, `sort`, `total`, `include`,
        `revinclude`)."""
        return build_search_params(**search)

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return {"resourceType": "Organization", **data}

    def to_wire_patch(self, data: dict) -> dict:
        return data
