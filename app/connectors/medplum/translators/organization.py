"""
Medplum wire translation for the canonical FHIR R4 Organization shape used
by app.gql.organization (see app.connectors.base.OrganizationWireTranslator
for the shared contract and app.gql.organization's package docstring for
the overall idea).

Medplum is genuinely FHIR-native, so canonical path/params/body ARE its
real path/params/body — this is closer to a pure pass-through than
app.connectors.internal.translators.organization's translator is in every
direction, not just reads.
"""


class MedplumOrganizationTranslator:
    """medplum. See module docstring — near pure pass-through."""

    accept = None  # MedplumConnector's Content-Type is already fixed to FHIR.

    def item_path(self, organization_id: str) -> str:
        return f"/Organization/{organization_id}"

    def list_path(self) -> str:
        return "/Organization"

    def list_params(
        self, name: str | None, active: bool | None, limit: int, offset: int
    ) -> dict:
        params: dict = {"_count": limit, "_offset": offset}
        if name is not None:
            params["name"] = name
        if active is not None:
            params["active"] = active
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return {"resourceType": "Organization", **data}

    def to_wire_patch(self, data: dict) -> dict:
        return {"resourceType": "Organization", **data}
