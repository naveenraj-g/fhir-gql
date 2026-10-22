"""
Medplum wire translation for the canonical FHIR R4 Location shape used by
app.gql.location (see app.connectors.base.LocationWireTranslator for the
shared contract and app.connectors.medplum.translators.organization's
module docstring for the overall idea — this mirrors it exactly for
Location).

Medplum is genuinely FHIR-native, so canonical path/params/body ARE its
real path/params/body — a pure pass-through in every direction, same as
the Organization translator.
"""


class MedplumLocationTranslator:
    """medplum. See module docstring — near pure pass-through."""

    accept = None  # MedplumConnector's Content-Type is already fixed to FHIR.

    def item_path(self, location_id: str) -> str:
        return f"/Location/{location_id}"

    def list_path(self) -> str:
        return "/Location"

    def list_params(
        self,
        name: str | None,
        identifier: str | None,
        status: str | None,
        operational_status: str | None,
        location_type: str | None,
        address: str | None,
        address_city: str | None,
        address_state: str | None,
        address_postal_code: str | None,
        address_country: str | None,
        address_use: str | None,
        organization: str | None,
        partof: str | None,
        endpoint: str | None,
        near: str | None,
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
        if identifier is not None:
            params["identifier"] = identifier
        if status is not None:
            params["status"] = status
        if operational_status is not None:
            params["operational-status"] = operational_status
        if location_type is not None:
            params["type"] = location_type
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
        if organization is not None:
            params["organization"] = organization
        if partof is not None:
            params["partof"] = partof
        if endpoint is not None:
            params["endpoint"] = endpoint
        if near is not None:
            params["near"] = near
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return {"resourceType": "Location", **data}

    def to_wire_patch(self, data: dict) -> dict:
        return {"resourceType": "Location", **data}
