"""
Medplum wire translation for the canonical FHIR R4 Schedule shape used by
app.gql.schedule (see app.connectors.base.ScheduleWireTranslator for the
shared contract and app.connectors.medplum.translators.organization's
module docstring for the overall idea — this mirrors it exactly for
Schedule).

Medplum is genuinely FHIR-native, so canonical path/params/body ARE its
real path/params/body — a pure pass-through in every direction, same as
the Organization/Location/HealthcareService/Practitioner/PractitionerRole
translators. The one exception is `to_wire_patch` — see
app.connectors.medplum.json_patch's docstring for why PATCH can't be a
pass-through here either.
"""

from app.connectors.medplum.json_patch import to_json_patch


class MedplumScheduleTranslator:
    """medplum. See module docstring — near pure pass-through."""

    accept = None  # MedplumConnector's Content-Type is already fixed to FHIR.

    def item_path(self, schedule_id: str) -> str:
        return f"/Schedule/{schedule_id}"

    def list_path(self) -> str:
        return "/Schedule"

    def list_params(
        self,
        active: bool | None,
        identifier: str | None,
        service_category: str | None,
        service_type: str | None,
        specialty: str | None,
        actor: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Medplum speaks genuine FHIR R4 search params natively —
        `service_category`/`service_type` map to the real spec names
        `service-category`/`service-type`
        (https://hl7.org/fhir/R4/schedule.html#search), same renaming the
        internal connector's own router aliases apply."""
        params: dict = {"_count": limit, "_offset": offset}
        if active is not None:
            params["active"] = active
        if identifier is not None:
            params["identifier"] = identifier
        if service_category is not None:
            params["service-category"] = service_category
        if service_type is not None:
            params["service-type"] = service_type
        if specialty is not None:
            params["specialty"] = specialty
        if actor is not None:
            params["actor"] = actor
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return {"resourceType": "Schedule", **data}

    def to_wire_patch(self, data: dict) -> list[dict]:
        return to_json_patch(data)
