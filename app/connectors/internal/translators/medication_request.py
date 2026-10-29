"""
internal (fhir-server) wire translation for the canonical FHIR R4
MedicationRequest shape used by app.gql.medication_request. See
app.connectors.internal.translators.service_request's module docstring
for the overall idea — this mirrors it for MedicationRequest.

MedicationRequest is a default (gateway-trusted) resource on fhir-server
— same as ServiceRequest — so `to_wire_create`/`to_wire_patch` take the
same extra keyword-only `tenant_id`/`user_id`/`created_by`/`updated_by`
arguments.
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


def _dosage(d: dict) -> dict:
    max_admin = d.get("maxDosePerAdministration") or {}
    max_life = d.get("maxDosePerLifetime") or {}
    return {
        "sequence": d.get("sequence"),
        "text": d.get("text"),
        "additional_instruction": [_codeable_concept(c) for c in (d.get("additionalInstruction") or [])] or None,
        "patient_instruction": d.get("patientInstruction"),
        "timing": d.get("timing"),
        "as_needed_boolean": d.get("asNeededBoolean"),
        "as_needed_codeable_concept": _codeable_concept(d["asNeededCodeableConcept"]) if d.get("asNeededCodeableConcept") else None,
        "site": _codeable_concept(d["site"]) if d.get("site") else None,
        "route": _codeable_concept(d["route"]) if d.get("route") else None,
        "method": _codeable_concept(d["method"]) if d.get("method") else None,
        "dose_and_rate": d.get("doseAndRate"),
        "max_dose_per_period": d.get("maxDosePerPeriod"),
        "max_dose_per_administration_value": max_admin.get("value"),
        "max_dose_per_administration_unit": max_admin.get("unit"),
        "max_dose_per_administration_system": max_admin.get("system"),
        "max_dose_per_administration_code": max_admin.get("code"),
        "max_dose_per_lifetime_value": max_life.get("value"),
        "max_dose_per_lifetime_unit": max_life.get("unit"),
        "max_dose_per_lifetime_system": max_life.get("system"),
        "max_dose_per_lifetime_code": max_life.get("code"),
    }


def _mr_body(data: dict) -> dict:
    """Canonical FHIR MedicationRequest dict -> fhir-server's flattened
    MedicationRequestCreateSchema/PatchSchema body (minus the audit/tenant
    fields — those are added by `to_wire_create`/`to_wire_patch` below)."""
    group_identifier = data.get("groupIdentifier")
    dispense_request = data.get("dispenseRequest") or {}
    initial_fill = dispense_request.get("initialFill") or {}
    initial_fill_quantity = initial_fill.get("quantity") or {}
    initial_fill_duration = initial_fill.get("duration") or {}
    dispense_interval = dispense_request.get("dispenseInterval") or {}
    validity_period = dispense_request.get("validityPeriod") or {}
    dr_quantity = dispense_request.get("quantity") or {}
    expected_supply_duration = dispense_request.get("expectedSupplyDuration") or {}
    dispense_performer = dispense_request.get("performer")
    substitution = data.get("substitution") or {}

    body = {
        "extension": data.get("extension"),
        "identifier": [_identifier(i) for i in (data.get("identifier") or [])] or None,
        "status": data.get("status"),
        "status_reason": _codeable_concept(data["statusReason"]) if data.get("statusReason") else None,
        "intent": data.get("intent"),
        "category": [_codeable_concept(c) for c in (data.get("category") or [])] or None,
        "priority": data.get("priority"),
        "do_not_perform": data.get("doNotPerform"),
        "reported_boolean": data.get("reportedBoolean"),
        "reported_reference": _reference(data["reportedReference"]) if data.get("reportedReference") else None,
        "medication_codeable_concept": _codeable_concept(data["medicationCodeableConcept"]) if data.get("medicationCodeableConcept") else None,
        "medication_reference": _reference(data["medicationReference"]) if data.get("medicationReference") else None,
        "subject": _reference(data["subject"]) if data.get("subject") else None,
        "encounter": _reference(data["encounter"]) if data.get("encounter") else None,
        "supporting_information": [_reference(r) for r in (data.get("supportingInformation") or [])] or None,
        "authored_on": data.get("authoredOn"),
        "requester": _reference(data["requester"]) if data.get("requester") else None,
        "performer": _reference(data["performer"]) if data.get("performer") else None,
        "performer_type": _codeable_concept(data["performerType"]) if data.get("performerType") else None,
        "recorder": _reference(data["recorder"]) if data.get("recorder") else None,
        "reason_code": [_codeable_concept(c) for c in (data.get("reasonCode") or [])] or None,
        "reason_reference": [_reference(r) for r in (data.get("reasonReference") or [])] or None,
        "instantiates_canonical": data.get("instantiatesCanonical"),
        "instantiates_uri": data.get("instantiatesUri"),
        "based_on": [_reference(r) for r in (data.get("basedOn") or [])] or None,
        "group_identifier": _identifier(group_identifier) if group_identifier else None,
        "course_of_therapy_type": _codeable_concept(data["courseOfTherapyType"]) if data.get("courseOfTherapyType") else None,
        "insurance": [_reference(r) for r in (data.get("insurance") or [])] or None,
        "note": [_note(n) for n in (data.get("note") or [])] or None,
        "dosage_instruction": [_dosage(d) for d in (data.get("dosageInstruction") or [])] or None,
        "dispense_request_initial_fill_quantity_value": initial_fill_quantity.get("value"),
        "dispense_request_initial_fill_quantity_comparator": initial_fill_quantity.get("comparator"),
        "dispense_request_initial_fill_quantity_unit": initial_fill_quantity.get("unit"),
        "dispense_request_initial_fill_quantity_system": initial_fill_quantity.get("system"),
        "dispense_request_initial_fill_quantity_code": initial_fill_quantity.get("code"),
        "dispense_request_initial_fill_duration_value": initial_fill_duration.get("value"),
        "dispense_request_initial_fill_duration_unit": initial_fill_duration.get("unit"),
        "dispense_request_initial_fill_duration_system": initial_fill_duration.get("system"),
        "dispense_request_initial_fill_duration_code": initial_fill_duration.get("code"),
        "dispense_request_dispense_interval_value": dispense_interval.get("value"),
        "dispense_request_dispense_interval_unit": dispense_interval.get("unit"),
        "dispense_request_dispense_interval_system": dispense_interval.get("system"),
        "dispense_request_dispense_interval_code": dispense_interval.get("code"),
        "dispense_request_validity_period_start": validity_period.get("start"),
        "dispense_request_validity_period_end": validity_period.get("end"),
        "dispense_request_number_of_repeats_allowed": dispense_request.get("numberOfRepeatsAllowed"),
        "dispense_request_quantity_value": dr_quantity.get("value"),
        "dispense_request_quantity_unit": dr_quantity.get("unit"),
        "dispense_request_quantity_system": dr_quantity.get("system"),
        "dispense_request_quantity_code": dr_quantity.get("code"),
        "dispense_request_expected_supply_duration_value": expected_supply_duration.get("value"),
        "dispense_request_expected_supply_duration_unit": expected_supply_duration.get("unit"),
        "dispense_request_expected_supply_duration_system": expected_supply_duration.get("system"),
        "dispense_request_expected_supply_duration_code": expected_supply_duration.get("code"),
        "dispense_request_performer": _reference(dispense_performer) if dispense_performer else None,
        "substitution_allowed_boolean": substitution.get("allowedBoolean"),
        "substitution_allowed_codeable_concept": _codeable_concept(substitution["allowedCodeableConcept"]) if substitution.get("allowedCodeableConcept") else None,
        "substitution_reason": _codeable_concept(substitution["reason"]) if substitution.get("reason") else None,
        "prior_prescription": _reference(data["priorPrescription"]) if data.get("priorPrescription") else None,
        "detected_issue": [_reference(r) for r in (data.get("detectedIssue") or [])] or None,
        "event_history": [_reference(r) for r in (data.get("eventHistory") or [])] or None,
    }
    return {k: v for k, v in body.items() if v is not None}


class InternalMedicationRequestTranslator:
    """internal (fhir-server). See module docstring for why
    `to_wire_create`/`to_wire_patch` take extra keyword-only arguments."""

    accept = "application/fhir+json"

    def item_path(self, medication_request_id: str) -> str:
        return f"/medication-requests/{medication_request_id}"

    def list_path(self) -> str:
        return "/medication-requests"

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
        body = _mr_body(data)
        body["tenant_id"] = tenant_id
        if user_id is not None:
            body["user_id"] = user_id
        body["created_by"] = created_by
        return body

    def to_wire_patch(self, data: dict, *, updated_by: str | None) -> dict:
        body = _mr_body(data)
        if updated_by is not None:
            body["updated_by"] = updated_by
        return body
