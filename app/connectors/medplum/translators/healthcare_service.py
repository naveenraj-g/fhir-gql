"""
Medplum wire translation for the canonical FHIR R4 HealthcareService shape
used by app.gql.healthcare_service (see
app.connectors.base.HealthcareServiceWireTranslator for the shared contract
and app.connectors.medplum.translators.organization's module docstring for
the overall idea — this mirrors it for HealthcareService).

Medplum is genuinely FHIR-native, so canonical path/params/body ARE its
real path/params/body — a pure pass-through in every direction, same as
the Organization/Location translators. The one exception is
`to_wire_patch` — see app.connectors.medplum.json_patch's docstring for
why PATCH can't be a pass-through here either.
"""

from app.connectors.medplum.json_patch import to_json_patch


class MedplumHealthcareServiceTranslator:
    """medplum. See module docstring — near pure pass-through."""

    accept = None  # MedplumConnector's Content-Type is already fixed to FHIR.

    def item_path(self, healthcare_service_id: str) -> str:
        return f"/HealthcareService/{healthcare_service_id}"

    def list_path(self) -> str:
        return "/HealthcareService"

    def list_params(
        self,
        name: str | None,
        identifier: str | None,
        active: bool | None,
        category: str | None,
        service_type: str | None,
        specialty: str | None,
        characteristic: str | None,
        program: str | None,
        organization: str | None,
        location: str | None,
        coverage_area: str | None,
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
        if identifier is not None:
            params["identifier"] = identifier
        if active is not None:
            params["active"] = active
        if category is not None:
            params["service-category"] = category
        if service_type is not None:
            params["service-type"] = service_type
        if specialty is not None:
            params["specialty"] = specialty
        if characteristic is not None:
            params["characteristic"] = characteristic
        if program is not None:
            params["program"] = program
        if organization is not None:
            params["organization"] = organization
        if location is not None:
            params["location"] = location
        if coverage_area is not None:
            params["coverage-area"] = coverage_area
        if endpoint is not None:
            params["endpoint"] = endpoint
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return {"resourceType": "HealthcareService", **data}

    def to_wire_patch(self, data: dict) -> list[dict]:
        return to_json_patch(data)
