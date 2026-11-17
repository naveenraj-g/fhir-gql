"""
Oracle Health wire translation for the canonical FHIR R4 Organization shape.

Oracle is FHIR-native (`/Organization/{id}`), so path, search parameters and
body pass through. Oracle supports Organization create but not update/patch/
delete (the connector answers 405 for those), so `to_wire_patch` is never
reached.
"""

from app.connectors.fhir_search import build_search_params


class OracleHealthOrganizationTranslator:
    """oracle_health. See module docstring."""

    accept = None  # OracleHealthConnector fixes the FHIR media type itself.

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
