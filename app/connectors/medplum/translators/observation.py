"""
Medplum wire translation for the canonical FHIR R4 Observation shape
used by app.gql.observation. See
app.connectors.medplum.translators.medication_request's module
docstring for the overall idea — this mirrors it for Observation.

Medplum is genuinely FHIR-native, so canonical path/params/body ARE its
real path/params/body — a pure pass-through in every direction except
`to_wire_patch` (RFC 6902 JSON Patch). `to_wire_create`/`to_wire_patch`
accept the same extra keyword-only arguments as
InternalObservationTranslator's own, purely so
app.gql.observation.mutations can call either translator uniformly —
Medplum itself never had an org_id/created_by/updated_by body-field
requirement, so these are accepted and discarded.
"""

from app.connectors.medplum.json_patch import to_json_patch


class MedplumObservationTranslator:
    """medplum. See module docstring — near pure pass-through."""

    accept = None  # MedplumConnector's Content-Type is already fixed to FHIR.

    def item_path(self, observation_id: str) -> str:
        return f"/Observation/{observation_id}"

    def list_path(self) -> str:
        return "/Observation"

    def list_params(
        self,
        status: str | None,
        subject: str | None,
        identifier: str | None,
        tenant_id: str | None,
        user_id: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Medplum speaks genuine FHIR R4 search params natively —
        https://hl7.org/fhir/R4/observation.html#search. `tenant_id`/
        `user_id` have no FHIR-native equivalent and are never forwarded."""
        params: dict = {"_count": limit, "_offset": offset}
        if status is not None:
            params["status"] = status
        if subject is not None:
            params["subject"] = subject
        if identifier is not None:
            params["identifier"] = identifier
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict, *, tenant_id: str, user_id: str | None, created_by: str) -> dict:
        return {"resourceType": "Observation", **data}

    def to_wire_patch(self, data: dict, *, updated_by: str | None) -> list[dict]:
        return to_json_patch(data)
