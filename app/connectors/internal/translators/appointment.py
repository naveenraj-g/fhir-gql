"""
internal (fhir-server) wire translation for the canonical FHIR R4
Appointment shape used by app.gql.appointment (see
app.connectors.base.AppointmentWireTranslator for the shared contract and
app.connectors.internal.translators.organization's module docstring for
the overall idea — this mirrors it for Appointment).

Canonical shape already matches fhir-server's own
`Accept: application/fhir+json` response exactly — what differs from
genuine FHIR R4 conventions is fhir-server's own path (`/appointments`,
not `/Appointment`), its own query-param names (`limit`/`offset`, not
FHIR search's `_count`/`_offset`; `service-category`/`service-type`
aliasing `serviceCategory`/`serviceType`), and — on write only — its own
flattened plain-JSON create/patch body shape (see _appointment_body
below).

fhir-server's own AppointmentCreateSchema.status already accepts the true
hyphenated FHIR code directly (its Pydantic enum's .value IS the wire
code — see that project's app/models/appointment/enums.py's docstring for
why the *model* layer differs), so `status`/`participant[].required`/
`participant[].status` need no translation here, unlike every Reference/
CodeableConcept field.

Logical-identifier fallback fields with no canonical-FHIR source
(`assigner_identifier_*`, `reference_identifier_*`, `actor_identifier_*`)
are never populated here, same known gap as Organization's/
HealthcareService's/PractitionerRole's/Schedule's/Slot's translators.
"""


def _coding(c: dict) -> dict:
    """FhirCoding -> a bare {system, code, display} dict."""
    return {
        "system": c.get("system"),
        "code": c.get("code"),
        "display": c.get("display"),
    }


def _identifier(i: dict) -> dict:
    """FhirIdentifier -> AppointmentIdentifierInput-shaped dict. `type.coding[]`
    is a real 0..* list (type_coding). `assigner` is only ever a Reference's
    reference/display on the canonical side — the assigner_identifier_*
    logical-identifier fallback has no source here."""
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


def _cc(cc: dict) -> dict:
    """FhirCodeableConcept -> {coding, text}-shaped dict — shared by
    serviceCategory/serviceType/specialty/reasonCode/appointmentType/
    cancelationReason/participant.type."""
    return {
        "coding": [_coding(c) for c in (cc.get("coding") or [])] or None,
        "text": cc.get("text"),
    }


def _reference_item(ref: dict) -> dict:
    """FhirReference -> {reference, reference_display}-shaped dict — shared
    by reasonReference/supportingInformation/slot/basedOn, each a bare 0..*
    Reference list on the canonical side."""
    return {
        "reference": ref.get("reference"),
        "reference_display": ref.get("display"),
    }


def _period(p: dict) -> dict:
    return {"start": p.get("start"), "end": p.get("end")}


def _participant(p: dict) -> dict:
    """FhirAppointmentParticipant -> AppointmentParticipantInput-shaped dict."""
    actor = p.get("actor") or {}
    period = p.get("period") or {}
    return {
        "type": [_cc(t) for t in (p.get("type") or [])] or None,
        "actor": actor.get("reference"),
        "actor_display": actor.get("display"),
        "required": p.get("required"),
        "status": p.get("status"),
        "period_start": period.get("start"),
        "period_end": period.get("end"),
    }


def _appointment_body(data: dict) -> dict:
    """Canonical FHIR Appointment dict -> fhir-server's flattened
    AppointmentCreateSchema/PatchSchema body. Shared by both — the two
    schemas differ only in which fields are immutable, not in field shape
    for everything this translator populates."""
    cancelation_reason = data.get("cancelationReason") or {}
    appointment_type = data.get("appointmentType") or {}
    body = {
        "status": data.get("status"),
        "cancelation_reason_coding": [
            _coding(c) for c in (cancelation_reason.get("coding") or [])
        ]
        or None,
        "cancelation_reason_text": cancelation_reason.get("text"),
        "appointment_type_coding": [
            _coding(c) for c in (appointment_type.get("coding") or [])
        ]
        or None,
        "appointment_type_text": appointment_type.get("text"),
        "priority": data.get("priority"),
        "description": data.get("description"),
        "start": data.get("start"),
        "end": data.get("end"),
        "minutes_duration": data.get("minutesDuration"),
        "created": data.get("created"),
        "comment": data.get("comment"),
        "patient_instruction": data.get("patientInstruction"),
        "identifier": [_identifier(i) for i in (data.get("identifier") or [])] or None,
        "service_category": [_cc(sc) for sc in (data.get("serviceCategory") or [])]
        or None,
        "service_type": [_cc(st) for st in (data.get("serviceType") or [])] or None,
        "specialty": [_cc(sp) for sp in (data.get("specialty") or [])] or None,
        "reason_code": [_cc(rc) for rc in (data.get("reasonCode") or [])] or None,
        "reason_reference": [
            _reference_item(rr) for rr in (data.get("reasonReference") or [])
        ]
        or None,
        "supporting_information": [
            _reference_item(si) for si in (data.get("supportingInformation") or [])
        ]
        or None,
        "slot": [_reference_item(s) for s in (data.get("slot") or [])] or None,
        "based_on": [_reference_item(bo) for bo in (data.get("basedOn") or [])] or None,
        "requested_period": [
            _period(rp) for rp in (data.get("requestedPeriod") or [])
        ]
        or None,
        "participant": [_participant(p) for p in (data.get("participant") or [])]
        or None,
    }
    return {k: v for k, v in body.items() if v is not None}


class InternalAppointmentTranslator:
    """internal (fhir-server). See module docstring for what differs from
    genuine FHIR R4 conventions."""

    accept = "application/fhir+json"

    def item_path(self, appointment_id: str) -> str:
        return f"/appointments/{appointment_id}"

    def list_path(self) -> str:
        return "/appointments"

    def list_params(
        self,
        status: str | None,
        identifier: str | None,
        service_category: str | None,
        service_type: str | None,
        specialty: str | None,
        actor: str | None,
        slot: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """fhir-server's own router aliases `service_category`/
        `service_type` to the real FHIR R4 search parameter names
        `service-category`/`service-type` — see
        app/routers/appointment/core.py in that project."""
        params: dict = {"limit": limit, "offset": offset}
        if status is not None:
            params["status"] = status
        if identifier is not None:
            params["identifier"] = identifier
        if service_category is not None:
            params["service-category"] = service_category
        if service_type is not None:
            params["service-type"] = service_type
        if specialty is not None:
            params["specialty"] = specialty
        if actor is not None:
            params["actor"] = actor
        if slot is not None:
            params["slot"] = slot
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return _appointment_body(data)

    def to_wire_patch(self, data: dict) -> dict:
        return _appointment_body(data)
