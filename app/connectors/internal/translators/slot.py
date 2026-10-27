"""
internal (fhir-server) wire translation for the canonical FHIR R4 Slot
shape used by app.gql.slot (see app.connectors.base.SlotWireTranslator for
the shared contract and app.connectors.internal.translators.organization's
module docstring for the overall idea — this mirrors it for Slot).

Canonical shape already matches fhir-server's own
`Accept: application/fhir+json` response exactly — what differs from
genuine FHIR R4 conventions is fhir-server's own path (`/slots`, not
`/Slot`), its own query-param names (`limit`/`offset`, not FHIR search's
`_count`/`_offset`; `service-category`/`service-type` aliasing
`serviceCategory`/`serviceType`), and — on write only — its own flattened
plain-JSON create/patch body shape (see _slot_body below).

fhir-server's own SlotCreateSchema.status already accepts the true
hyphenated FHIR code directly (its Pydantic enum's .value IS the wire
code — see that project's app/models/slot/enums.py's docstring for why
the *model* layer differs), so `status` needs no translation here, unlike
every Reference/CodeableConcept field.

Logical-identifier fallback fields with no canonical-FHIR source
(`assigner_identifier_*`, `schedule_identifier_*`) are never populated
here, same known gap as Organization's/HealthcareService's/
PractitionerRole's/Schedule's translators.
"""


def _coding(c: dict) -> dict:
    """FhirCoding -> a bare {system, code, display} dict."""
    return {
        "system": c.get("system"),
        "code": c.get("code"),
        "display": c.get("display"),
    }


def _identifier(i: dict) -> dict:
    """FhirIdentifier -> SlotIdentifierInput-shaped dict. `type.coding[]`
    is a real 0..* list (type_coding). `assigner` is only ever a
    Reference's reference/display on the canonical side — the
    assigner_identifier_* logical-identifier fallback has no source here."""
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
    serviceCategory/serviceType/specialty/appointmentType."""
    return {
        "coding": [_coding(c) for c in (cc.get("coding") or [])] or None,
        "text": cc.get("text"),
    }


def _slot_body(data: dict) -> dict:
    """Canonical FHIR Slot dict -> fhir-server's flattened
    SlotCreateSchema/PatchSchema body. Shared by both — the two schemas
    differ only in which fields are immutable, not in field shape for
    everything this translator populates."""
    schedule = data.get("schedule") or {}
    appointment_type = data.get("appointmentType") or {}
    body = {
        "schedule": schedule.get("reference"),
        "schedule_display": schedule.get("display"),
        "status": data.get("status"),
        "start": data.get("start"),
        "end": data.get("end"),
        "appointment_type_coding": [
            _coding(c) for c in (appointment_type.get("coding") or [])
        ]
        or None,
        "appointment_type_text": appointment_type.get("text"),
        "overbooked": data.get("overbooked"),
        "comment": data.get("comment"),
        "identifier": [_identifier(i) for i in (data.get("identifier") or [])] or None,
        "service_category": [
            _cc(sc) for sc in (data.get("serviceCategory") or [])
        ]
        or None,
        "service_type": [_cc(st) for st in (data.get("serviceType") or [])] or None,
        "specialty": [_cc(sp) for sp in (data.get("specialty") or [])] or None,
    }
    return {k: v for k, v in body.items() if v is not None}


class InternalSlotTranslator:
    """internal (fhir-server). See module docstring for what differs from
    genuine FHIR R4 conventions."""

    accept = "application/fhir+json"

    def item_path(self, slot_id: str) -> str:
        return f"/slots/{slot_id}"

    def list_path(self) -> str:
        return "/slots"

    def list_params(
        self,
        status: str | None,
        identifier: str | None,
        service_category: str | None,
        service_type: str | None,
        specialty: str | None,
        schedule: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """fhir-server's own router aliases `service_category`/
        `service_type` to the real FHIR R4 search parameter names
        `service-category`/`service-type` — see
        app/routers/slot/core.py in that project."""
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
        if schedule is not None:
            params["schedule"] = schedule
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return _slot_body(data)

    def to_wire_patch(self, data: dict) -> dict:
        return _slot_body(data)
