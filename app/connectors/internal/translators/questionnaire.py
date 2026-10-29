"""
internal (fhir-server) wire translation for the canonical FHIR R4
Questionnaire shape used by app.gql.questionnaire (see
app.connectors.internal.translators.organization's module docstring for
the overall idea — this mirrors it for Questionnaire).

Canonical shape already matches fhir-server's own
`Accept: application/fhir+json` response exactly on reads — what differs
from genuine FHIR R4 conventions is fhir-server's own path
(`/questionnaires`, not `/Questionnaire`), its own query-param names
(`limit`/`offset`, not FHIR search's `_count`/`_offset`), and — on write
only — its own flattened plain-JSON create/patch body shape (see
_questionnaire_body below).

**Questionnaire is now one of fhir-server's auth-rollout resources**,
same as Organization/Practitioner/etc. — fhir-server derives `org_id`/
`created_by`/`updated_by` from the forwarded JWT itself, so
`to_wire_create`/`to_wire_patch` take no extra keyword-only arguments,
same shape as every other resource's translator. `app.gql.questionnaire.mutations`
calls `connector.post`/`.patch` with `inject_audit=False` the same way
every other rolled-out resource does — `actor` alone is forwarded (via
the Authorization header InternalConnector always sets), and fhir-server
decodes org_id/sub from it itself.

`user_id` is still a plain fhir-server field (like Practitioner's), but
has no canonical-FHIR source to translate from, so it's simply never
populated here — same narrower gap as InternalPractitionerTranslator's
own `user_id`.

Logical-identifier fallback fields with no canonical-FHIR source
(`assigner_identifier_*`) are never populated here, same known gap as
every other resource's translator.
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


def _contact(c: dict) -> dict:
    return {
        "name": c.get("name"),
        "telecom": [
            {
                "system": t.get("system"),
                "value": t.get("value"),
                "use": t.get("use"),
                "rank": t.get("rank"),
                "period_start": (t.get("period") or {}).get("start"),
                "period_end": (t.get("period") or {}).get("end"),
            }
            for t in (c.get("telecom") or [])
        ]
        or None,
    }


def _jurisdiction(j: dict) -> dict:
    return {
        "coding": [_coding(c) for c in (j.get("coding") or [])] or None,
        "text": j.get("text"),
    }


def _use_context(uc: dict) -> dict:
    code = uc.get("code") or {}
    vcc = uc.get("valueCodeableConcept") or {}
    vq = uc.get("valueQuantity") or {}
    vr = uc.get("valueRange") or {}
    vr_low = vr.get("low") or {}
    vr_high = vr.get("high") or {}
    vref = uc.get("valueReference") or {}
    return {
        "code_system": code.get("system"),
        "code_version": code.get("version"),
        "code_code": code.get("code"),
        "code_display": code.get("display"),
        "code_user_selected": code.get("userSelected"),
        "value_codeable_concept_coding": [_coding(c) for c in (vcc.get("coding") or [])] or None,
        "value_codeable_concept_text": vcc.get("text"),
        "value_quantity_value": vq.get("value"),
        "value_quantity_comparator": vq.get("comparator"),
        "value_quantity_unit": vq.get("unit"),
        "value_quantity_system": vq.get("system"),
        "value_quantity_code": vq.get("code"),
        "value_range_low_value": vr_low.get("value"),
        "value_range_low_unit": vr_low.get("unit"),
        "value_range_low_system": vr_low.get("system"),
        "value_range_low_code": vr_low.get("code"),
        "value_range_high_value": vr_high.get("value"),
        "value_range_high_unit": vr_high.get("unit"),
        "value_range_high_system": vr_high.get("system"),
        "value_range_high_code": vr_high.get("code"),
        "value_reference": vref.get("reference"),
        "value_reference_display": vref.get("display"),
    }


def _enable_when(ew: dict) -> dict:
    coding = ew.get("answerCoding") or {}
    qty = ew.get("answerQuantity") or {}
    ref = ew.get("answerReference") or {}
    return {
        "question": ew.get("question"),
        "operator": ew.get("operator"),
        "answer_boolean": ew.get("answerBoolean"),
        "answer_decimal": ew.get("answerDecimal"),
        "answer_integer": ew.get("answerInteger"),
        "answer_date": ew.get("answerDate"),
        "answer_date_time": ew.get("answerDateTime"),
        "answer_time": ew.get("answerTime"),
        "answer_string": ew.get("answerString"),
        "answer_coding_system": coding.get("system"),
        "answer_coding_version": coding.get("version"),
        "answer_coding_code": coding.get("code"),
        "answer_coding_display": coding.get("display"),
        "answer_coding_user_selected": coding.get("userSelected"),
        "answer_quantity_value": qty.get("value"),
        "answer_quantity_comparator": qty.get("comparator"),
        "answer_quantity_unit": qty.get("unit"),
        "answer_quantity_system": qty.get("system"),
        "answer_quantity_code": qty.get("code"),
        "answer_reference": ref.get("reference"),
        "answer_reference_display": ref.get("display"),
    }


def _answer_option(ao: dict) -> dict:
    coding = ao.get("valueCoding") or {}
    ref = ao.get("valueReference") or {}
    return {
        "value_integer": ao.get("valueInteger"),
        "value_date": ao.get("valueDate"),
        "value_time": ao.get("valueTime"),
        "value_string": ao.get("valueString"),
        "value_coding_system": coding.get("system"),
        "value_coding_version": coding.get("version"),
        "value_coding_code": coding.get("code"),
        "value_coding_display": coding.get("display"),
        "value_coding_user_selected": coding.get("userSelected"),
        "value_reference": ref.get("reference"),
        "value_reference_display": ref.get("display"),
        "initial_selected": ao.get("initialSelected"),
    }


def _initial(ini: dict) -> dict:
    attachment = ini.get("valueAttachment") or {}
    coding = ini.get("valueCoding") or {}
    qty = ini.get("valueQuantity") or {}
    ref = ini.get("valueReference") or {}
    return {
        "value_boolean": ini.get("valueBoolean"),
        "value_decimal": ini.get("valueDecimal"),
        "value_integer": ini.get("valueInteger"),
        "value_date": ini.get("valueDate"),
        "value_date_time": ini.get("valueDateTime"),
        "value_time": ini.get("valueTime"),
        "value_string": ini.get("valueString"),
        "value_uri": ini.get("valueUri"),
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
    }


def _item(it: dict) -> dict:
    """Recursive — FhirQuestionnaireItem.item nests to unbounded depth;
    fhir-server's own QuestionnaireItemInput mirrors that same recursion
    (`item: list[QuestionnaireItemInput]`), so this translator recurses
    right alongside it."""
    return {
        "link_id": it.get("linkId"),
        "definition": it.get("definition"),
        "code": [_coding(c) for c in (it.get("code") or [])] or None,
        "prefix": it.get("prefix"),
        "text": it.get("text"),
        "type": it.get("type"),
        "enable_when": [_enable_when(ew) for ew in (it.get("enableWhen") or [])] or None,
        "enable_behavior": it.get("enableBehavior"),
        "required": it.get("required"),
        "repeats": it.get("repeats"),
        "read_only": it.get("readOnly"),
        "max_length": it.get("maxLength"),
        "answer_value_set": it.get("answerValueSet"),
        "answer_option": [_answer_option(ao) for ao in (it.get("answerOption") or [])] or None,
        "initial": [_initial(ini) for ini in (it.get("initial") or [])] or None,
        "item": [_item(child) for child in (it.get("item") or [])] or None,
    }


def _questionnaire_body(data: dict) -> dict:
    """Canonical FHIR Questionnaire dict -> fhir-server's flattened
    QuestionnaireCreateSchema/PatchSchema body. `user_id` has no
    canonical-FHIR source — see module docstring — so it's never
    populated here."""
    effective_period = data.get("effectivePeriod") or {}
    body = {
        "extension": data.get("extension"),
        "url": data.get("url"),
        "identifier": [_identifier(i) for i in (data.get("identifier") or [])] or None,
        "version": data.get("version"),
        "name": data.get("name"),
        "title": data.get("title"),
        "derived_from": data.get("derivedFrom"),
        "status": data.get("status"),
        "experimental": data.get("experimental"),
        "subject_type": data.get("subjectType"),
        "date": data.get("date"),
        "publisher": data.get("publisher"),
        "description": data.get("description"),
        "purpose": data.get("purpose"),
        "copyright": data.get("copyright"),
        "approval_date": data.get("approvalDate"),
        "last_review_date": data.get("lastReviewDate"),
        "effective_period_start": effective_period.get("start"),
        "effective_period_end": effective_period.get("end"),
        "code": [_coding(c) for c in (data.get("code") or [])] or None,
        "contact": [_contact(c) for c in (data.get("contact") or [])] or None,
        "use_context": [_use_context(uc) for uc in (data.get("useContext") or [])] or None,
        "jurisdiction": [_jurisdiction(j) for j in (data.get("jurisdiction") or [])] or None,
        "item": [_item(it) for it in (data.get("item") or [])] or None,
    }
    return {k: v for k, v in body.items() if v is not None}


class InternalQuestionnaireTranslator:
    """internal (fhir-server). See module docstring for what differs from
    genuine FHIR R4 conventions."""

    accept = "application/fhir+json"

    def item_path(self, questionnaire_id: str) -> str:
        return f"/questionnaires/{questionnaire_id}"

    def list_path(self) -> str:
        return "/questionnaires"

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
        params: dict = {"limit": limit, "offset": offset}
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
        return _questionnaire_body(data)

    def to_wire_patch(self, data: dict) -> dict:
        return _questionnaire_body(data)
