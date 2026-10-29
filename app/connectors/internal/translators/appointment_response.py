"""
internal (fhir-server) wire translation for the canonical FHIR R4
AppointmentResponse shape used by app.gql.appointment_response (see
app.connectors.base.AppointmentResponseWireTranslator for the shared
contract and app.connectors.internal.translators.organization's module
docstring for the overall idea — this mirrors it for AppointmentResponse).

Canonical shape already matches fhir-server's own
`Accept: application/fhir+json` response exactly — what differs from
genuine FHIR R4 conventions is fhir-server's own path
(`/appointment-responses`, not `/AppointmentResponse`), its own
query-param names (`limit`/`offset`, not FHIR search's `_count`/`_offset`;
`part-status` aliasing `participantStatus`), and — on write only — its own
flattened plain-JSON create/patch body shape (see
_appointment_response_body below).

fhir-server's own AppointmentResponseCreateSchema.participant_status
already accepts the true hyphenated FHIR code directly (its Pydantic
enum's .value IS the wire code — see that project's
app/models/appointment_response/enums.py's docstring for why the *model*
layer differs), so `participantStatus` needs no translation here, unlike
every Reference/CodeableConcept field.

Logical-identifier fallback fields with no canonical-FHIR source
(`assigner_identifier_*`, `appointment_identifier_*`, `actor_identifier_*`)
are never populated here, same known gap as every earlier translator in
this repo.
"""


def _coding(c: dict) -> dict:
    """FhirCoding -> a bare {system, code, display} dict."""
    return {
        "system": c.get("system"),
        "code": c.get("code"),
        "display": c.get("display"),
    }


def _identifier(i: dict) -> dict:
    """FhirIdentifier -> AppointmentResponseIdentifierInput-shaped dict.
    `type.coding[]` is a real 0..* list (type_coding). `assigner` is only
    ever a Reference's reference/display on the canonical side — the
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


def _participant_type(cc: dict) -> dict:
    """FhirCodeableConcept -> {coding, text}-shaped dict."""
    return {
        "coding": [_coding(c) for c in (cc.get("coding") or [])] or None,
        "text": cc.get("text"),
    }


def _appointment_response_body(data: dict) -> dict:
    """Canonical FHIR AppointmentResponse dict -> fhir-server's flattened
    AppointmentResponseCreateSchema/PatchSchema body. Shared by both — the
    two schemas differ only in which fields are immutable, not in field
    shape for everything this translator populates."""
    appointment = data.get("appointment") or {}
    actor = data.get("actor") or {}
    body = {
        "appointment": appointment.get("reference"),
        "appointment_display": appointment.get("display"),
        "start": data.get("start"),
        "end": data.get("end"),
        "actor": actor.get("reference"),
        "actor_display": actor.get("display"),
        "participant_status": data.get("participantStatus"),
        "comment": data.get("comment"),
        "identifier": [_identifier(i) for i in (data.get("identifier") or [])] or None,
        "participant_type": [
            _participant_type(pt) for pt in (data.get("participantType") or [])
        ]
        or None,
    }
    return {k: v for k, v in body.items() if v is not None}


class InternalAppointmentResponseTranslator:
    """internal (fhir-server). See module docstring for what differs from
    genuine FHIR R4 conventions."""

    accept = "application/fhir+json"

    def item_path(self, appointment_response_id: str) -> str:
        return f"/appointment-responses/{appointment_response_id}"

    def list_path(self) -> str:
        return "/appointment-responses"

    def list_params(
        self,
        identifier: str | None,
        appointment: str | None,
        actor: str | None,
        part_status: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """fhir-server's own router aliases `part_status` to the real
        FHIR R4 search parameter name `part-status` — see
        app/routers/appointment_response/core.py in that project."""
        params: dict = {"limit": limit, "offset": offset}
        if identifier is not None:
            params["identifier"] = identifier
        if appointment is not None:
            params["appointment"] = appointment
        if actor is not None:
            params["actor"] = actor
        if part_status is not None:
            params["part-status"] = part_status
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return _appointment_response_body(data)

    def to_wire_patch(self, data: dict) -> dict:
        return _appointment_response_body(data)
