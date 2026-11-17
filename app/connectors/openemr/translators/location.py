"""
OpenEMR wire translation for the canonical FHIR R4 Location shape.

Pass-through, same as the Organization translator. OpenEMR exposes Location
as read/search only, so create/update/delete are rejected by OpenEMR itself
(its 4xx is passed back to the GraphQL caller).
"""

from app.connectors.fhir_search import build_search_params


class OpenEmrLocationTranslator:
    """openemr. See module docstring."""

    accept = None  # OpenEmrConnector fixes the FHIR media type itself.

    def item_path(self, location_id: str) -> str:
        return f"/Location/{location_id}"

    def list_path(self) -> str:
        return "/Location"

    def search_params(self, **search) -> dict[str, list[str]]:
        return build_search_params(**search)

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return {"resourceType": "Location", **data}

    def to_wire_patch(self, data: dict) -> dict:
        return data
