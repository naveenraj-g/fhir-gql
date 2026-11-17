"""
OpenEMR wire translation for the canonical FHIR R4 Organization shape.

OpenEMR is FHIR-native (`/Organization/{id}`), so path, search parameters
and body are passed through. `to_wire_patch` returns the plain partial
object: OpenEMR has no PATCH, so OpenEmrConnector.patch() turns it into
read -> merge -> PUT. Which operations OpenEMR allows on Organization is its
own rule (create/update yes, delete no - see client.py).
"""

from app.connectors.fhir_search import build_search_params


class OpenEmrOrganizationTranslator:
    """openemr. See module docstring."""

    accept = None  # OpenEmrConnector fixes the FHIR media type itself.

    def item_path(self, organization_id: str) -> str:
        return f"/Organization/{organization_id}"

    def list_path(self) -> str:
        return "/Organization"

    def search_params(self, **search) -> dict[str, list[str]]:
        return build_search_params(**search)

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return {"resourceType": "Organization", **data}

    def to_wire_patch(self, data: dict) -> dict:
        return data
