"""
internal (fhir-server) wire translation for the canonical FHIR R4
Observation shape used by app.gql.observation. See
app.connectors.internal.translators.medication_request's module
docstring for the overall idea — this mirrors it for Observation.

**Observation is now one of fhir-server's auth-rollout resources**,
same as ServiceRequest/MedicationRequest/Questionnaire/etc. —
fhir-server derives `org_id`/`created_by`/`updated_by` from the
forwarded JWT itself, so `to_wire_create`/`to_wire_patch` take no
extra keyword-only arguments, same shape as every other resource's
translator. `user_id` is still a plain fhir-server field, but has no
canonical-FHIR source to translate from, so it's simply never
populated here.
"""


def _coding(c: dict) -> dict:
    return {
        "system": c.get("system"),
        "version": c.get("version"),
        "code": c.get("code"),
        "display": c.get("display"),
        "user_selected": c.get("userSelected"),
    }


def _codeable_concept(cc: dict | None) -> dict:
    cc = cc or {}
    return {"coding": [_coding(c) for c in (cc.get("coding") or [])] or None, "text": cc.get("text")}


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


def _note(n: dict) -> dict:
    author_ref = n.get("authorReference") or {}
    return {
        "author_string": n.get("authorString"),
        "author_reference": author_ref.get("reference"),
        "author_reference_display": author_ref.get("display"),
        "time": n.get("time"),
        "text": n.get("text"),
    }


def _reference_range(rr: dict) -> dict:
    low = rr.get("low") or {}
    high = rr.get("high") or {}
    age = rr.get("age") or {}
    age_low = age.get("low") or {}
    age_high = age.get("high") or {}
    return {
        "low_value": low.get("value"),
        "low_unit": low.get("unit"),
        "low_system": low.get("system"),
        "low_code": low.get("code"),
        "high_value": high.get("value"),
        "high_unit": high.get("unit"),
        "high_system": high.get("system"),
        "high_code": high.get("code"),
        "type": _codeable_concept(rr["type"]) if rr.get("type") else None,
        "applies_to": [_codeable_concept(c) for c in (rr.get("appliesTo") or [])] or None,
        "age_low_value": age_low.get("value"),
        "age_low_unit": age_low.get("unit"),
        "age_low_system": age_low.get("system"),
        "age_low_code": age_low.get("code"),
        "age_high_value": age_high.get("value"),
        "age_high_unit": age_high.get("unit"),
        "age_high_system": age_high.get("system"),
        "age_high_code": age_high.get("code"),
        "text": rr.get("text"),
    }


def _value_x(data: dict) -> dict:
    """Shared `value[x]` (11-variant choice) flattening — identical shape
    for the root resource and its own `component`."""
    vq = data.get("valueQuantity") or {}
    vr = data.get("valueRange") or {}
    vr_low = vr.get("low") or {}
    vr_high = vr.get("high") or {}
    vratio = data.get("valueRatio") or {}
    vratio_num = vratio.get("numerator") or {}
    vratio_den = vratio.get("denominator") or {}
    vsd = data.get("valueSampledData") or {}
    vsd_origin = vsd.get("origin") or {}
    vperiod = data.get("valuePeriod") or {}
    return {
        "value_quantity_value": vq.get("value"),
        "value_quantity_comparator": vq.get("comparator"),
        "value_quantity_unit": vq.get("unit"),
        "value_quantity_system": vq.get("system"),
        "value_quantity_code": vq.get("code"),
        "value_codeable_concept": _codeable_concept(data["valueCodeableConcept"]) if data.get("valueCodeableConcept") else None,
        "value_string": data.get("valueString"),
        "value_boolean": data.get("valueBoolean"),
        "value_integer": data.get("valueInteger"),
        "value_range_low_value": vr_low.get("value"),
        "value_range_low_unit": vr_low.get("unit"),
        "value_range_low_system": vr_low.get("system"),
        "value_range_low_code": vr_low.get("code"),
        "value_range_high_value": vr_high.get("value"),
        "value_range_high_unit": vr_high.get("unit"),
        "value_range_high_system": vr_high.get("system"),
        "value_range_high_code": vr_high.get("code"),
        "value_ratio_numerator_value": vratio_num.get("value"),
        "value_ratio_numerator_comparator": vratio_num.get("comparator"),
        "value_ratio_numerator_unit": vratio_num.get("unit"),
        "value_ratio_numerator_system": vratio_num.get("system"),
        "value_ratio_numerator_code": vratio_num.get("code"),
        "value_ratio_denominator_value": vratio_den.get("value"),
        "value_ratio_denominator_comparator": vratio_den.get("comparator"),
        "value_ratio_denominator_unit": vratio_den.get("unit"),
        "value_ratio_denominator_system": vratio_den.get("system"),
        "value_ratio_denominator_code": vratio_den.get("code"),
        "value_sampled_data_origin_value": vsd_origin.get("value"),
        "value_sampled_data_origin_unit": vsd_origin.get("unit"),
        "value_sampled_data_origin_system": vsd_origin.get("system"),
        "value_sampled_data_origin_code": vsd_origin.get("code"),
        "value_sampled_data_period": vsd.get("period"),
        "value_sampled_data_factor": vsd.get("factor"),
        "value_sampled_data_lower_limit": vsd.get("lowerLimit"),
        "value_sampled_data_upper_limit": vsd.get("upperLimit"),
        "value_sampled_data_dimensions": vsd.get("dimensions"),
        "value_sampled_data_data": vsd.get("data"),
        "value_time": data.get("valueTime"),
        "value_date_time": data.get("valueDateTime"),
        "value_period_start": vperiod.get("start"),
        "value_period_end": vperiod.get("end"),
    }


def _component(c: dict) -> dict:
    body = {"code": _codeable_concept(c["code"]) if c.get("code") else None}
    body.update(_value_x(c))
    body["data_absent_reason"] = _codeable_concept(c["dataAbsentReason"]) if c.get("dataAbsentReason") else None
    body["interpretation"] = [_codeable_concept(cc) for cc in (c.get("interpretation") or [])] or None
    body["reference_range"] = [_reference_range(rr) for rr in (c.get("referenceRange") or [])] or None
    return {k: v for k, v in body.items() if v is not None}


def _obs_body(data: dict) -> dict:
    """Canonical FHIR Observation dict -> fhir-server's flattened
    ObservationCreateSchema/PatchSchema body (minus the audit/tenant
    fields — those are added by `to_wire_create`/`to_wire_patch` below)."""
    effective_period = data.get("effectivePeriod") or {}

    body = {
        "extension": data.get("extension"),
        "identifier": [_identifier(i) for i in (data.get("identifier") or [])] or None,
        "based_on": [_reference(r) for r in (data.get("basedOn") or [])] or None,
        "part_of": [_reference(r) for r in (data.get("partOf") or [])] or None,
        "status": data.get("status"),
        "category": [_codeable_concept(c) for c in (data.get("category") or [])] or None,
        "code": _codeable_concept(data["code"]) if data.get("code") else None,
        "subject": _reference(data["subject"]) if data.get("subject") else None,
        "focus": [_reference(r) for r in (data.get("focus") or [])] or None,
        "encounter": _reference(data["encounter"]) if data.get("encounter") else None,
        "effective_date_time": data.get("effectiveDateTime"),
        "effective_period_start": effective_period.get("start"),
        "effective_period_end": effective_period.get("end"),
        "effective_timing": data.get("effectiveTiming"),
        "effective_instant": data.get("effectiveInstant"),
        "issued": data.get("issued"),
        "performer": [_reference(r) for r in (data.get("performer") or [])] or None,
        "data_absent_reason": _codeable_concept(data["dataAbsentReason"]) if data.get("dataAbsentReason") else None,
        "interpretation": [_codeable_concept(c) for c in (data.get("interpretation") or [])] or None,
        "note": [_note(n) for n in (data.get("note") or [])] or None,
        "body_site": _codeable_concept(data["bodySite"]) if data.get("bodySite") else None,
        "method": _codeable_concept(data["method"]) if data.get("method") else None,
        "specimen": _reference(data["specimen"]) if data.get("specimen") else None,
        "device": _reference(data["device"]) if data.get("device") else None,
        "reference_range": [_reference_range(rr) for rr in (data.get("referenceRange") or [])] or None,
        "has_member": [_reference(r) for r in (data.get("hasMember") or [])] or None,
        "derived_from": [_reference(r) for r in (data.get("derivedFrom") or [])] or None,
        "component": [_component(c) for c in (data.get("component") or [])] or None,
    }
    body.update(_value_x(data))
    return {k: v for k, v in body.items() if v is not None}


class InternalObservationTranslator:
    """internal (fhir-server). See module docstring for why
    `to_wire_create`/`to_wire_patch` take extra keyword-only arguments."""

    accept = "application/fhir+json"

    def item_path(self, observation_id: str) -> str:
        return f"/observations/{observation_id}"

    def list_path(self) -> str:
        return "/observations"

    def list_params(
        self,
        status: str | None,
        subject: str | None,
        identifier: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        params: dict = {"limit": limit, "offset": offset}
        if status is not None:
            params["status"] = status
        if subject is not None:
            params["subject"] = subject
        if identifier is not None:
            params["identifier"] = identifier
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return _obs_body(data)

    def to_wire_patch(self, data: dict) -> dict:
        return _obs_body(data)
