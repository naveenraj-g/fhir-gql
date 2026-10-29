"""
Medplum wire translation for the canonical FHIR R4 Encounter shape used
by app.gql.encounter (see app.connectors.base.EncounterWireTranslator
for the shared contract and app.connectors.medplum.translators.organization's
module docstring for the overall idea — this mirrors it exactly for
Encounter).

Medplum is genuinely FHIR-native, so canonical path/params/body ARE its
real path/params/body — a pure pass-through in every direction, same as
the Organization/.../AppointmentResponse translators. The one exception is
`to_wire_patch` — see app.connectors.medplum.json_patch's docstring for
why PATCH can't be a pass-through here either.
"""

from app.connectors.medplum.json_patch import to_json_patch


class MedplumEncounterTranslator:
    """medplum. See module docstring — near pure pass-through."""

    accept = None  # MedplumConnector's Content-Type is already fixed to FHIR.

    def item_path(self, encounter_id: str) -> str:
        return f"/Encounter/{encounter_id}"

    def list_path(self) -> str:
        return "/Encounter"

    def list_params(
        self,
        status: str | None,
        identifier: str | None,
        subject: str | None,
        class_code: str | None,
        type_code: str | None,
        service_provider: str | None,
        part_of: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Medplum speaks genuine FHIR R4 search params natively —
        `class_code`/`type_code`/`service_provider`/`part_of` map to the
        real spec names `class`/`type`/`service-provider`/`part-of`
        (https://hl7.org/fhir/R4/encounter.html#search), same renaming
        the internal connector's own router aliases apply."""
        params: dict = {"_count": limit, "_offset": offset}
        if status is not None:
            params["status"] = status
        if identifier is not None:
            params["identifier"] = identifier
        if subject is not None:
            params["subject"] = subject
        if class_code is not None:
            params["class"] = class_code
        if type_code is not None:
            params["type"] = type_code
        if service_provider is not None:
            params["service-provider"] = service_provider
        if part_of is not None:
            params["part-of"] = part_of
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return {"resourceType": "Encounter", **data}

    def to_wire_patch(self, data: dict) -> list[dict]:
        return to_json_patch(data)
