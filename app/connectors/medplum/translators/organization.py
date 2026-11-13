"""
Medplum wire translation for the canonical FHIR R4 Organization shape used
by app.gql.organization (see app.connectors.base.OrganizationWireTranslator
for the shared contract and app.gql.organization's package docstring for
the overall idea).

Medplum is genuinely FHIR-native, so canonical path/params/body ARE its
real path/params/body — this is closer to a pure pass-through than
app.connectors.internal.translators.organization's translator is in every
direction, not just reads. The one exception is `to_wire_patch` — see
app.connectors.medplum.json_patch's docstring for why PATCH can't be a
pass-through here either.
"""

# Shared with the internal translator: both backends speak FHIR R4 search.
from app.connectors.fhir_search import build_search_params
from app.connectors.medplum.json_patch import to_json_patch


class MedplumOrganizationTranslator:
    """medplum. See module docstring — near pure pass-through."""

    accept = None  # MedplumConnector's Content-Type is already fixed to FHIR.

    def item_path(self, organization_id: str) -> str:
        return f"/Organization/{organization_id}"

    def list_path(self) -> str:
        return "/Organization"

    def search_params(self, **search) -> dict[str, list[str]]:
        """FHIR R4 search arguments -> query parameters. Medplum speaks
        genuine FHIR R4 search natively, so this is
        app.connectors.fhir_search.build_search_params() unchanged — see
        that function for the accepted keyword arguments (`filters`,
        `params`, `count`, `offset`, `sort`, `total`, `include`,
        `revinclude`)."""
        return build_search_params(**search)

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return {"resourceType": "Organization", **data}

    def to_wire_patch(self, data: dict) -> list[dict]:
        return to_json_patch(data)
