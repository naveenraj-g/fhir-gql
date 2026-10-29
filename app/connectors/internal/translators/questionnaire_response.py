"""
internal (fhir-server) wire translation for the canonical FHIR R4
QuestionnaireResponse shape used by app.gql.questionnaire_response (see
app.connectors.internal.translators.organization's module docstring for
the overall idea — this mirrors it for QuestionnaireResponse).

Canonical shape already matches fhir-server's own
`Accept: application/fhir+json` response exactly on reads — what differs
from genuine FHIR R4 conventions is fhir-server's own path
(`/questionnaire-responses`, not `/QuestionnaireResponse`), its own
query-param names (`limit`/`offset`, not FHIR search's `_count`/
`_offset`), and — on write only — its own flattened plain-JSON
create/patch body shape (see `_qr_body` below).

**QuestionnaireResponse is a default (gateway-trusted) resource on
fhir-server** — unlike every OTHER resource this gateway talks to, it was
never asked to get the JWT-auth-rollout treatment (see fhir-server's
CLAUDE.md "Multi-Tenancy & Ownership" section and
`/resource-auth-rollout`), so `tenant_id`/`user_id`/`created_by`/
`updated_by` are still plain, gateway-forwarded body fields there — the
exact shape Questionnaire's OWN translator used to have before its own
rollout (see git history / fhir-server's CLAUDE.md "Adding a New FHIR
Resource" section, which still documents that conversion as the worked
example). `to_wire_create`/`to_wire_patch` therefore take EXTRA
keyword-only arguments, unlike every other resource's translator in this
gateway — `app.gql.questionnaire_response.mutations` calls
`connector.post`/`.patch` with `inject_audit=False` (InternalConnector's
own generic actor.sub-only mechanism only ever injects `created_by`/
`updated_by`, never `tenant_id`/`user_id` — see
app.connectors.internal.client's docstring) and passes `tenant_id`/
`user_id`/`created_by`/`updated_by` through to this translator explicitly
instead.
"""


def _coding(c: dict) -> dict:
    return {
        "system": c.get("system"),
        "version": c.get("version"),
        "code": c.get("code"),
        "display": c.get("display"),
        "user_selected": c.get("userSelected"),
    }


def _identifier(i: dict) -> dict:
    period = i.get("period") or {}
    type_cc = i.get("type") or {}
    assigner = i.get("assigner") or {}
    return {
        "use": i.get("use"),
        "type_coding": [_coding(c) for c in (type_cc.get("coding") or [])] or None,
        "type_text": type_cc.get("text"),
        "system": i.get("system"),
        "value": i.get("value"),
        "period_start": period.get("start"),
        "period_end": period.get("end"),
        "assigner": assigner.get("reference"),
        "assigner_display": assigner.get("display"),
    }


def _reference(ref: dict | None) -> dict:
    """fhir-server's QuestionnaireResponse basedOn/partOf/subject/
    encounter/author/source all take the same flat `reference`/
    `reference_display` body shape — see
    app.schemas.questionnaire_response.input.reference on the
    fhir-server side."""
    ref = ref or {}
    return {
        "reference": ref.get("reference"),
        "reference_display": ref.get("display"),
    }


def _answer(a: dict) -> dict:
    attachment = a.get("valueAttachment") or {}
    coding = a.get("valueCoding") or {}
    qty = a.get("valueQuantity") or {}
    ref = a.get("valueReference") or {}
    return {
        "value_boolean": a.get("valueBoolean"),
        "value_decimal": a.get("valueDecimal"),
        "value_integer": a.get("valueInteger"),
        "value_date": a.get("valueDate"),
        "value_date_time": a.get("valueDateTime"),
        "value_time": a.get("valueTime"),
        "value_string": a.get("valueString"),
        "value_uri": a.get("valueUri"),
        "value_attachment": {
            "content_type": attachment.get("contentType"),
            "language": attachment.get("language"),
            "data": attachment.get("data"),
            "url": attachment.get("url"),
            "size": attachment.get("size"),
            "hash": attachment.get("hash"),
            "title": attachment.get("title"),
            "creation": attachment.get("creation"),
        }
        if attachment
        else None,
        "value_coding_system": coding.get("system"),
        "value_coding_version": coding.get("version"),
        "value_coding_code": coding.get("code"),
        "value_coding_display": coding.get("display"),
        "value_coding_user_selected": coding.get("userSelected"),
        "value_quantity_value": qty.get("value"),
        "value_quantity_comparator": qty.get("comparator"),
        "value_quantity_unit": qty.get("unit"),
        "value_quantity_system": qty.get("system"),
        "value_quantity_code": qty.get("code"),
        "value_reference": ref.get("reference"),
        "value_reference_display": ref.get("display"),
        "item": [_item(child) for child in (a.get("item") or [])] or None,
    }


def _item(it: dict) -> dict:
    """Recursive and mutually recursive with `_answer` — FhirQuestionnaireResponseItem.item
    nests to unbounded depth, and item.answer.item nests under a specific
    answer instead; fhir-server's own QuestionnaireResponseItemInput
    mirrors both paths (`item: list[QuestionnaireResponseItemInput]`,
    `answer[].item: list[QuestionnaireResponseItemInput]`), so this
    translator recurses right alongside it."""
    return {
        "link_id": it.get("linkId"),
        "definition": it.get("definition"),
        "text": it.get("text"),
        "answer": [_answer(a) for a in (it.get("answer") or [])] or None,
        "item": [_item(child) for child in (it.get("item") or [])] or None,
    }


def _qr_body(data: dict) -> dict:
    """Canonical FHIR QuestionnaireResponse dict -> fhir-server's
    flattened QuestionnaireResponseCreateSchema/PatchSchema body
    (minus the audit/tenant fields — those are added by
    `to_wire_create`/`to_wire_patch` below, since they have no canonical-
    FHIR source)."""
    identifier = data.get("identifier")
    body = {
        "extension": data.get("extension"),
        "identifier": _identifier(identifier) if identifier else None,
        "based_on": [_reference(r) for r in (data.get("basedOn") or [])] or None,
        "part_of": [_reference(r) for r in (data.get("partOf") or [])] or None,
        "questionnaire": data.get("questionnaire"),
        "status": data.get("status"),
        "subject": _reference(data["subject"]) if data.get("subject") else None,
        "encounter": _reference(data["encounter"]) if data.get("encounter") else None,
        "authored": data.get("authored"),
        "author": _reference(data["author"]) if data.get("author") else None,
        "source": _reference(data["source"]) if data.get("source") else None,
        "item": [_item(it) for it in (data.get("item") or [])] or None,
    }
    return {k: v for k, v in body.items() if v is not None}


class InternalQuestionnaireResponseTranslator:
    """internal (fhir-server). See module docstring for what differs from
    genuine FHIR R4 conventions, and for why `to_wire_create`/
    `to_wire_patch` take extra keyword-only arguments unlike every other
    resource's translator."""

    accept = "application/fhir+json"

    def item_path(self, questionnaire_response_id: str) -> str:
        return f"/questionnaire-responses/{questionnaire_response_id}"

    def list_path(self) -> str:
        return "/questionnaire-responses"

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
        params: dict = {"limit": limit, "offset": offset}
        if status is not None:
            params["status"] = status
        if questionnaire is not None:
            params["questionnaire"] = questionnaire
        if subject is not None:
            params["subject"] = subject
        if identifier is not None:
            params["identifier"] = identifier
        if tenant_id is not None:
            params["tenant_id"] = tenant_id
        if user_id is not None:
            params["user_id"] = user_id
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
        body = _qr_body(data)
        body["tenant_id"] = tenant_id
        if user_id is not None:
            body["user_id"] = user_id
        body["created_by"] = created_by
        return body

    def to_wire_patch(self, data: dict, *, updated_by: str | None) -> dict:
        body = _qr_body(data)
        if updated_by is not None:
            body["updated_by"] = updated_by
        return body
