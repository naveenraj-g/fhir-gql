"""
Medplum wire translation for the canonical FHIR R4 Questionnaire shape
used by app.gql.questionnaire (see
app.connectors.medplum.translators.organization's module docstring for
the overall idea — this mirrors it for Questionnaire).

Medplum is genuinely FHIR-native, so canonical path/params/body ARE its
real path/params/body — a pure pass-through in every direction. The one
exception is `to_wire_patch` — see app.connectors.medplum.json_patch's
docstring for why PATCH can't be a pass-through here either.

`to_wire_create`/`to_wire_patch` take the same plain `data`-only
signature as every other resource's Medplum translator — Questionnaire's
auth rollout on the fhir-server side doesn't affect this connector at
all, since Medplum never had an org_id/created_by/updated_by body-field
requirement to begin with.
"""

from app.connectors.medplum.json_patch import to_json_patch


class MedplumQuestionnaireTranslator:
    """medplum. See module docstring — near pure pass-through."""

    accept = None  # MedplumConnector's Content-Type is already fixed to FHIR.

    def item_path(self, questionnaire_id: str) -> str:
        return f"/Questionnaire/{questionnaire_id}"

    def list_path(self) -> str:
        return "/Questionnaire"

    def list_params(
        self,
        status: str | None,
        url: str | None,
        name: str | None,
        title: str | None,
        publisher: str | None,
        identifier: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Medplum speaks genuine FHIR R4 search params natively —
        https://hl7.org/fhir/R4/questionnaire.html#search."""
        params: dict = {"_count": limit, "_offset": offset}
        if status is not None:
            params["status"] = status
        if url is not None:
            params["url"] = url
        if name is not None:
            params["name"] = name
        if title is not None:
            params["title"] = title
        if publisher is not None:
            params["publisher"] = publisher
        if identifier is not None:
            params["identifier"] = identifier
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return {"resourceType": "Questionnaire", **data}

    def to_wire_patch(self, data: dict) -> list[dict]:
        return to_json_patch(data)
