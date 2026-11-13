"""
internal (fhir-server) wire translation for the canonical FHIR R4 Location
shape used by app.gql.location (see app.connectors.base.LocationWireTranslator
for the shared contract) — the same arrangement as
app.connectors.internal.translators.organization.

fhir-server's Location create/patch body is genuine FHIR R4 JSON (the
resource is stored whole, Medplum-style, and served back the same way), so
the canonical shape passes through unchanged in both directions — no body
translation at all. Its Location search is genuine FHIR R4 search too
(every R4 Location search parameter including `near`, modifiers, chaining,
`_count`/`_offset`, `_sort`, `_include`, ...), so the only thing that still
differs from FHIR R4 conventions is fhir-server's own path (`/locations`,
not `/Location`).

PATCH stays a plain partial-object body (merge-patch on top-level
elements: a supplied list or object replaces the stored value wholesale)
— unlike Medplum, which needs an RFC 6902 JSON Patch array.
"""

# Shared with the medplum translator: both backends speak FHIR R4 search.
from app.connectors.fhir_search import build_search_params


class InternalLocationTranslator:
    """internal (fhir-server). See module docstring for what differs from
    genuine FHIR R4 conventions."""

    # fhir-server serves Location as FHIR JSON regardless; sent anyway so
    # the request states what it wants.
    accept = "application/fhir+json"

    def item_path(self, location_id: str) -> str:
        """GET-by-id / PATCH / DELETE path."""
        return f"/locations/{location_id}"

    def list_path(self) -> str:
        """Search (GET) and create (POST) path."""
        return "/locations"

    def search_params(self, **search) -> dict[str, list[str]]:
        """FHIR R4 search arguments -> query parameters. fhir-server
        implements genuine FHIR R4 search for Location (its app/fhir/search
        engine), so this is app.connectors.fhir_search.build_search_params()
        unchanged — see that function for the keyword arguments."""
        return build_search_params(**search)

    def from_wire(self, raw: dict) -> dict:
        """fhir-server's response already is canonical FHIR R4 — identity."""
        return raw

    def to_wire_create(self, data: dict) -> dict:
        """The canonical FHIR Location, stamped with its resourceType."""
        return {"resourceType": "Location", **data}

    def to_wire_patch(self, data: dict) -> dict:
        """The supplied top-level elements, as a merge-patch body."""
        return data
