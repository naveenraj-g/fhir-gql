"""
Medplum wire translation for the canonical FHIR R4 PractitionerRole shape
used by app.gql.practitioner_role (see
app.connectors.base.PractitionerRoleWireTranslator for the shared contract
and app.connectors.medplum.translators.organization's module docstring for
the overall idea — this mirrors it exactly for PractitionerRole).

Medplum is genuinely FHIR-native, so canonical path/params/body ARE its
real path/params/body — a pure pass-through in every direction, same as
the Organization/Location/HealthcareService/Practitioner translators. The
one exception is `to_wire_patch` — see app.connectors.medplum.json_patch's
docstring for why PATCH can't be a pass-through here either.
"""

from app.connectors.medplum.json_patch import to_json_patch


class MedplumPractitionerRoleTranslator:
    """medplum. See module docstring — near pure pass-through."""

    accept = None  # MedplumConnector's Content-Type is already fixed to FHIR.

    def item_path(self, practitioner_role_id: str) -> str:
        return f"/PractitionerRole/{practitioner_role_id}"

    def list_path(self) -> str:
        return "/PractitionerRole"

    def list_params(
        self,
        active: bool | None,
        identifier: str | None,
        code: str | None,
        specialty: str | None,
        practitioner: str | None,
        organization: str | None,
        location: str | None,
        healthcare_service: str | None,
        endpoint: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Medplum speaks genuine FHIR R4 search params natively — `code`
        and `healthcareService` map to the real spec names `role`/`service`
        (https://hl7.org/fhir/R4/practitionerrole.html#search), same
        renaming the internal connector's own router aliases apply."""
        params: dict = {"_count": limit, "_offset": offset}
        if active is not None:
            params["active"] = active
        if identifier is not None:
            params["identifier"] = identifier
        if code is not None:
            params["role"] = code
        if specialty is not None:
            params["specialty"] = specialty
        if practitioner is not None:
            params["practitioner"] = practitioner
        if organization is not None:
            params["organization"] = organization
        if location is not None:
            params["location"] = location
        if healthcare_service is not None:
            params["service"] = healthcare_service
        if endpoint is not None:
            params["endpoint"] = endpoint
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return {"resourceType": "PractitionerRole", **data}

    def to_wire_patch(self, data: dict) -> list[dict]:
        return to_json_patch(data)
