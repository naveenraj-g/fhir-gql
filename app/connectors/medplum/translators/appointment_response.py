"""
Medplum wire translation for the canonical FHIR R4 AppointmentResponse
shape used by app.gql.appointment_response (see
app.connectors.base.AppointmentResponseWireTranslator for the shared
contract and app.connectors.medplum.translators.organization's module
docstring for the overall idea — this mirrors it exactly for
AppointmentResponse).

Medplum is genuinely FHIR-native, so canonical path/params/body ARE its
real path/params/body — a pure pass-through in every direction, same as
every earlier translator in this repo. The one exception is
`to_wire_patch` — see app.connectors.medplum.json_patch's docstring for
why PATCH can't be a pass-through here either.
"""

from app.connectors.medplum.json_patch import to_json_patch


class MedplumAppointmentResponseTranslator:
    """medplum. See module docstring — near pure pass-through."""

    accept = None  # MedplumConnector's Content-Type is already fixed to FHIR.

    def item_path(self, appointment_response_id: str) -> str:
        return f"/AppointmentResponse/{appointment_response_id}"

    def list_path(self) -> str:
        return "/AppointmentResponse"

    def list_params(
        self,
        identifier: str | None,
        appointment: str | None,
        actor: str | None,
        part_status: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Medplum speaks genuine FHIR R4 search params natively —
        `part_status` maps to the real spec name `part-status`
        (https://hl7.org/fhir/R4/appointmentresponse.html#search), same
        renaming the internal connector's own router alias applies."""
        params: dict = {"_count": limit, "_offset": offset}
        if identifier is not None:
            params["identifier"] = identifier
        if appointment is not None:
            params["appointment"] = appointment
        if actor is not None:
            params["actor"] = actor
        if part_status is not None:
            params["part-status"] = part_status
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return {"resourceType": "AppointmentResponse", **data}

    def to_wire_patch(self, data: dict) -> list[dict]:
        return to_json_patch(data)
