"""
Medplum wire translation for the canonical FHIR R4 ServiceRequest shape
used by app.gql.service_request. See
app.connectors.medplum.translators.questionnaire_response's module
docstring for the overall idea — this mirrors it for ServiceRequest.

Medplum is genuinely FHIR-native, so canonical path/params/body ARE its
real path/params/body — a pure pass-through in every direction except
`to_wire_patch` (RFC 6902 JSON Patch). `to_wire_create`/`to_wire_patch`
take the same plain `data`-only signature as every other resource's
Medplum translator — ServiceRequest's auth rollout on the fhir-server
side doesn't affect this connector at all, since Medplum never had an
org_id/created_by/updated_by body-field requirement to begin with.
"""

from app.connectors.medplum.json_patch import to_json_patch


class MedplumServiceRequestTranslator:
    """medplum. See module docstring — near pure pass-through."""

    accept = None  # MedplumConnector's Content-Type is already fixed to FHIR.

    def item_path(self, service_request_id: str) -> str:
        return f"/ServiceRequest/{service_request_id}"

    def list_path(self) -> str:
        return "/ServiceRequest"

    def list_params(
        self,
        status: str | None,
        intent: str | None,
        subject: str | None,
        identifier: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Medplum speaks genuine FHIR R4 search params natively —
        https://hl7.org/fhir/R4/servicerequest.html#search."""
        params: dict = {"_count": limit, "_offset": offset}
        if status is not None:
            params["status"] = status
        if intent is not None:
            params["intent"] = intent
        if subject is not None:
            params["subject"] = subject
        if identifier is not None:
            params["identifier"] = identifier
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return {"resourceType": "ServiceRequest", **data}

    def to_wire_patch(self, data: dict) -> list[dict]:
        return to_json_patch(data)
