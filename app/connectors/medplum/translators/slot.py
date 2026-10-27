"""
Medplum wire translation for the canonical FHIR R4 Slot shape used by
app.gql.slot (see app.connectors.base.SlotWireTranslator for the shared
contract and app.connectors.medplum.translators.organization's module
docstring for the overall idea — this mirrors it exactly for Slot).

Medplum is genuinely FHIR-native, so canonical path/params/body ARE its
real path/params/body — a pure pass-through in every direction, same as
the Organization/Location/HealthcareService/Practitioner/
PractitionerRole/Schedule translators. The one exception is
`to_wire_patch` — see app.connectors.medplum.json_patch's docstring for
why PATCH can't be a pass-through here either.
"""

from app.connectors.medplum.json_patch import to_json_patch


class MedplumSlotTranslator:
    """medplum. See module docstring — near pure pass-through."""

    accept = None  # MedplumConnector's Content-Type is already fixed to FHIR.

    def item_path(self, slot_id: str) -> str:
        return f"/Slot/{slot_id}"

    def list_path(self) -> str:
        return "/Slot"

    def list_params(
        self,
        status: str | None,
        identifier: str | None,
        service_category: str | None,
        service_type: str | None,
        specialty: str | None,
        schedule: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Medplum speaks genuine FHIR R4 search params natively —
        `service_category`/`service_type` map to the real spec names
        `service-category`/`service-type`
        (https://hl7.org/fhir/R4/slot.html#search), same renaming the
        internal connector's own router aliases apply."""
        params: dict = {"_count": limit, "_offset": offset}
        if status is not None:
            params["status"] = status
        if identifier is not None:
            params["identifier"] = identifier
        if service_category is not None:
            params["service-category"] = service_category
        if service_type is not None:
            params["service-type"] = service_type
        if specialty is not None:
            params["specialty"] = specialty
        if schedule is not None:
            params["schedule"] = schedule
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return {"resourceType": "Slot", **data}

    def to_wire_patch(self, data: dict) -> list[dict]:
        return to_json_patch(data)
