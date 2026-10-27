"""
Medplum wire translation for the canonical FHIR R4 Practitioner shape used
by app.gql.practitioner (see app.connectors.base.PractitionerWireTranslator
for the shared contract and app.connectors.medplum.translators.organization's
module docstring for the overall idea — this mirrors it exactly for
Practitioner).

Medplum is genuinely FHIR-native, so canonical path/params/body ARE its
real path/params/body — a pure pass-through in every direction, same as
the Organization/Location/HealthcareService translators. The one
exception is `to_wire_patch` — see app.connectors.medplum.json_patch's
docstring for why PATCH can't be a pass-through here either.
"""

from app.connectors.medplum.json_patch import to_json_patch


class MedplumPractitionerTranslator:
    """medplum. See module docstring — near pure pass-through."""

    accept = None  # MedplumConnector's Content-Type is already fixed to FHIR.

    def item_path(self, practitioner_id: str) -> str:
        return f"/Practitioner/{practitioner_id}"

    def list_path(self) -> str:
        return "/Practitioner"

    def list_params(
        self,
        name: str | None,
        family: str | None,
        given: str | None,
        identifier: str | None,
        active: bool | None,
        gender: str | None,
        communication: str | None,
        telecom: str | None,
        phone: str | None,
        email: str | None,
        address: str | None,
        address_city: str | None,
        address_state: str | None,
        address_postal_code: str | None,
        address_country: str | None,
        address_use: str | None,
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
        if family is not None:
            params["family"] = family
        if given is not None:
            params["given"] = given
        if identifier is not None:
            params["identifier"] = identifier
        if active is not None:
            params["active"] = active
        if gender is not None:
            params["gender"] = gender
        if communication is not None:
            params["communication"] = communication
        if telecom is not None:
            params["telecom"] = telecom
        if phone is not None:
            params["phone"] = phone
        if email is not None:
            params["email"] = email
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
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return {"resourceType": "Practitioner", **data}

    def to_wire_patch(self, data: dict) -> list[dict]:
        return to_json_patch(data)
