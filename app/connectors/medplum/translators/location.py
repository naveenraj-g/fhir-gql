"""
Medplum wire translation for the canonical FHIR R4 Location shape used by
app.gql.location (see app.connectors.base.LocationWireTranslator for the
shared contract and app.connectors.medplum.translators.organization's
module docstring for the overall idea — this mirrors it exactly for
Location).

Medplum is genuinely FHIR-native, so canonical path/params/body ARE its
real path/params/body — a pure pass-through in every direction, same as
the Organization translator. The one exception is `to_wire_patch` — see
app.connectors.medplum.json_patch's docstring for why PATCH can't be a
pass-through here either.
"""

# Shared with the internal translator: both backends speak FHIR R4 search.
from app.connectors.fhir_search import build_search_params
from app.connectors.medplum.json_patch import to_json_patch


class MedplumLocationTranslator:
    """medplum. See module docstring — near pure pass-through."""

    accept = None  # MedplumConnector's Content-Type is already fixed to FHIR.

    def item_path(self, location_id: str) -> str:
        return f"/Location/{location_id}"

    def list_path(self) -> str:
        return "/Location"

    def search_params(self, **search) -> dict[str, list[str]]:
        """FHIR R4 search arguments -> query parameters. Medplum speaks
        genuine FHIR R4 search natively, so this is
        app.connectors.fhir_search.build_search_params() unchanged — see
        that function for the keyword arguments."""
        return build_search_params(**search)

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return {"resourceType": "Location", **data}

    def to_wire_patch(self, data: dict) -> list[dict]:
        return to_json_patch(data)
