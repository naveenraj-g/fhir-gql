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
        self,
        name: str | None,
        active: bool | None,
        identifier: str | None,
        org_type: str | None,
        address: str | None,
        address_city: str | None,
        address_state: str | None,
        address_postal_code: str | None,
        address_country: str | None,
        address_use: str | None,
        partof: str | None,
        endpoint: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Medplum speaks genuine FHIR R4 search params natively, so these
        are passed straight through under their real spec names — no
        renaming needed, unlike the internal connector's own flattened
        pagination (`_count`/`_offset` here vs `limit`/`offset` there)."""
        params: dict = {"_count": limit, "_offset": offset}
        if name is not None:
            params["name"] = name
        if active is not None:
            params["active"] = active
        if identifier is not None:
            params["identifier"] = identifier
        if org_type is not None:
            params["type"] = org_type
        if address is not None:
            params["address"] = address
        if address_city is not None:
            params["address-city"] = address_city
        if address_state is not None:
            params["address-state"] = address_state
        if address_postal_code is not None:
            params["address-postalcode"] = address_postal_code
        if address_country is not None:
            params["address-country"] = address_country
        if address_use is not None:
            params["address-use"] = address_use
        if partof is not None:
            params["partof"] = partof
        if endpoint is not None:
            params["endpoint"] = endpoint
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return {"resourceType": "Organization", **data}

    def to_wire_patch(self, data: dict) -> dict:
        return {"resourceType": "Organization", **data}
