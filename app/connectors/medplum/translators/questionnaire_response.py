"""
Medplum wire translation for the canonical FHIR R4 QuestionnaireResponse
shape used by app.gql.questionnaire_response (see
app.connectors.medplum.translators.organization's module docstring for
the overall idea — this mirrors it for QuestionnaireResponse).

Medplum is genuinely FHIR-native, so canonical path/params/body ARE its
real path/params/body — a pure pass-through in every direction. The one
exception is `to_wire_patch` — see app.connectors.medplum.json_patch's
docstring for why PATCH can't be a pass-through here either.

`to_wire_create`/`to_wire_patch` accept the SAME extra keyword-only
`tenant_id`/`user_id`/`created_by` / `updated_by` arguments as
InternalQuestionnaireResponseTranslator's own (see that module's
docstring for why those exist at all — QuestionnaireResponse is a default/
gateway-trusted resource on fhir-server, unlike every other resource this
gateway talks to) purely so `app.gql.questionnaire_response.mutations`
can call either translator uniformly without branching on which connector
is active. Medplum itself never had an org_id/created_by/updated_by
body-field requirement to begin with, so these arguments are accepted and
simply discarded here.
"""

from app.connectors.medplum.json_patch import to_json_patch


class MedplumQuestionnaireResponseTranslator:
    """medplum. See module docstring — near pure pass-through."""

    accept = None  # MedplumConnector's Content-Type is already fixed to FHIR.

    def item_path(self, questionnaire_response_id: str) -> str:
        return f"/QuestionnaireResponse/{questionnaire_response_id}"

    def list_path(self) -> str:
        return "/QuestionnaireResponse"

    def list_params(
        self,
        status: str | None,
        questionnaire: str | None,
        subject: str | None,
        identifier: str | None,
        tenant_id: str | None,
        user_id: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Medplum speaks genuine FHIR R4 search params natively —
        https://hl7.org/fhir/R4/questionnaireresponse.html#search.
        `tenant_id`/`user_id` have no FHIR-native equivalent on Medplum
        and are never forwarded."""
        params: dict = {"_count": limit, "_offset": offset}
        if status is not None:
            params["status"] = status
        if questionnaire is not None:
            params["questionnaire"] = questionnaire
        if subject is not None:
            params["subject"] = subject
        if identifier is not None:
            params["identifier"] = identifier
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(
        self,
        data: dict,
        *,
        tenant_id: str,
        user_id: str | None,
        created_by: str,
    ) -> dict:
        return {"resourceType": "QuestionnaireResponse", **data}

    def to_wire_patch(self, data: dict, *, updated_by: str | None) -> list[dict]:
        return to_json_patch(data)
