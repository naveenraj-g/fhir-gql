"""
internal (fhir-server) wire translation for the canonical FHIR R4
ServiceRequest shape used by app.gql.service_request. See
app.connectors.internal.translators.questionnaire_response's module
docstring for the overall idea — this mirrors it for ServiceRequest.

ServiceRequest is a default (gateway-trusted) resource on fhir-server —
same as QuestionnaireResponse — so `to_wire_create`/`to_wire_patch` take
the same extra keyword-only `tenant_id`/`user_id`/`created_by`/
`updated_by` arguments.
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


def _reference(r: dict | None) -> dict:
    r = r or {}
    return {"reference": r.get("reference"), "reference_display": r.get("display")}


def _codeable_concept(cc: dict | None) -> dict:
    cc = cc or {}
    return {"coding": [_coding(c) for c in (cc.get("coding") or [])] or None, "text": cc.get("text")}


def _note(n: dict) -> dict:
    author_ref = n.get("authorReference") or {}
    return {
        "author_string": n.get("authorString"),
        "author_reference": author_ref.get("reference"),
        "author_reference_display": author_ref.get("display"),
        "time": n.get("time"),
        "text": n.get("text"),
    }


def _sr_body(data: dict) -> dict:
    """Canonical FHIR ServiceRequest dict -> fhir-server's flattened
    ServiceRequestCreateSchema/PatchSchema body (minus the audit/tenant
    fields — those are added by `to_wire_create`/`to_wire_patch` below)."""
    qty_quantity = data.get("quantityQuantity") or {}
    qty_ratio = data.get("quantityRatio") or {}
    qty_ratio_num = qty_ratio.get("numerator") or {}
    qty_ratio_den = qty_ratio.get("denominator") or {}
    qty_range = data.get("quantityRange") or {}
    qty_range_low = qty_range.get("low") or {}
    qty_range_high = qty_range.get("high") or {}
    occurrence_period = data.get("occurrencePeriod") or {}
    requisition = data.get("requisition")

    body = {
        "extension": data.get("extension"),
        "identifier": [_identifier(i) for i in (data.get("identifier") or [])] or None,
        "instantiates_canonical": data.get("instantiatesCanonical"),
        "instantiates_uri": data.get("instantiatesUri"),
        "based_on": [_reference(r) for r in (data.get("basedOn") or [])] or None,
        "replaces": [_reference(r) for r in (data.get("replaces") or [])] or None,
        "requisition": _identifier(requisition) if requisition else None,
        "status": data.get("status"),
        "intent": data.get("intent"),
        "category": [_codeable_concept(c) for c in (data.get("category") or [])] or None,
        "priority": data.get("priority"),
        "do_not_perform": data.get("doNotPerform"),
        "code": _codeable_concept(data["code"]) if data.get("code") else None,
        "order_detail": [_codeable_concept(c) for c in (data.get("orderDetail") or [])] or None,
        "quantity_quantity_value": qty_quantity.get("value"),
        "quantity_quantity_comparator": qty_quantity.get("comparator"),
        "quantity_quantity_unit": qty_quantity.get("unit"),
        "quantity_quantity_system": qty_quantity.get("system"),
        "quantity_quantity_code": qty_quantity.get("code"),
        "quantity_ratio_numerator_value": qty_ratio_num.get("value"),
        "quantity_ratio_numerator_comparator": qty_ratio_num.get("comparator"),
        "quantity_ratio_numerator_unit": qty_ratio_num.get("unit"),
        "quantity_ratio_numerator_system": qty_ratio_num.get("system"),
        "quantity_ratio_numerator_code": qty_ratio_num.get("code"),
        "quantity_ratio_denominator_value": qty_ratio_den.get("value"),
        "quantity_ratio_denominator_comparator": qty_ratio_den.get("comparator"),
        "quantity_ratio_denominator_unit": qty_ratio_den.get("unit"),
        "quantity_ratio_denominator_system": qty_ratio_den.get("system"),
        "quantity_ratio_denominator_code": qty_ratio_den.get("code"),
        "quantity_range_low_value": qty_range_low.get("value"),
        "quantity_range_low_unit": qty_range_low.get("unit"),
        "quantity_range_low_system": qty_range_low.get("system"),
        "quantity_range_low_code": qty_range_low.get("code"),
        "quantity_range_high_value": qty_range_high.get("value"),
        "quantity_range_high_unit": qty_range_high.get("unit"),
        "quantity_range_high_system": qty_range_high.get("system"),
        "quantity_range_high_code": qty_range_high.get("code"),
        "subject": _reference(data["subject"]) if data.get("subject") else None,
        "encounter": _reference(data["encounter"]) if data.get("encounter") else None,
        "occurrence_date_time": data.get("occurrenceDateTime"),
        "occurrence_period_start": occurrence_period.get("start"),
        "occurrence_period_end": occurrence_period.get("end"),
        "occurrence_timing": data.get("occurrenceTiming"),
        "as_needed_boolean": data.get("asNeededBoolean"),
        "as_needed_codeable_concept": _codeable_concept(data["asNeededCodeableConcept"]) if data.get("asNeededCodeableConcept") else None,
        "authored_on": data.get("authoredOn"),
        "requester": _reference(data["requester"]) if data.get("requester") else None,
        "performer_type": _codeable_concept(data["performerType"]) if data.get("performerType") else None,
        "performer": [_reference(r) for r in (data.get("performer") or [])] or None,
        "location_code": [_codeable_concept(c) for c in (data.get("locationCode") or [])] or None,
        "location_reference": [_reference(r) for r in (data.get("locationReference") or [])] or None,
        "reason_code": [_codeable_concept(c) for c in (data.get("reasonCode") or [])] or None,
        "reason_reference": [_reference(r) for r in (data.get("reasonReference") or [])] or None,
        "insurance": [_reference(r) for r in (data.get("insurance") or [])] or None,
        "supporting_info": [_reference(r) for r in (data.get("supportingInfo") or [])] or None,
        "specimen": [_reference(r) for r in (data.get("specimen") or [])] or None,
        "body_site": [_codeable_concept(c) for c in (data.get("bodySite") or [])] or None,
        "note": [_note(n) for n in (data.get("note") or [])] or None,
        "patient_instruction": data.get("patientInstruction"),
        "relevant_history": [_reference(r) for r in (data.get("relevantHistory") or [])] or None,
    }
    return {k: v for k, v in body.items() if v is not None}


class InternalServiceRequestTranslator:
    """internal (fhir-server). See module docstring for why
    `to_wire_create`/`to_wire_patch` take extra keyword-only arguments."""

    accept = "application/fhir+json"

    def item_path(self, service_request_id: str) -> str:
        return f"/service-requests/{service_request_id}"

    def list_path(self) -> str:
        return "/service-requests"

    def list_params(
        self,
        status: str | None,
        intent: str | None,
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
        if intent is not None:
            params["intent"] = intent
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

    def to_wire_create(self, data: dict, *, tenant_id: str, user_id: str | None, created_by: str) -> dict:
        body = _sr_body(data)
        body["tenant_id"] = tenant_id
        if user_id is not None:
            body["user_id"] = user_id
        body["created_by"] = created_by
        return body

    def to_wire_patch(self, data: dict, *, updated_by: str | None) -> dict:
        body = _sr_body(data)
        if updated_by is not None:
            body["updated_by"] = updated_by
        return body
