"""
Epic wire translation for the canonical FHIR R4 Organization shape.

Epic is FHIR-native (`/Organization/{id}`), so path, search parameters and
body pass through. Epic's own rules apply to searches (it requires certain
parameters, e.g. a name, for directory searches) and its OperationOutcome is
passed back as the error. The connector is read-only, so the write helpers
exist only to satisfy the translator contract and are never reached (the
connector answers 405 first).
"""

from app.connectors.fhir_search import build_search_params


class EpicOrganizationTranslator:
    """epic. See module docstring."""

    accept = None  # EpicConnector fixes the FHIR media type itself.

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
