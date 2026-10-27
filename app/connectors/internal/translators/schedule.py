"""
internal (fhir-server) wire translation for the canonical FHIR R4 Schedule
shape used by app.gql.schedule (see
app.connectors.base.ScheduleWireTranslator for the shared contract and
app.connectors.internal.translators.organization's module docstring for
the overall idea — this mirrors it for Schedule).

Canonical shape already matches fhir-server's own
`Accept: application/fhir+json` response exactly — what differs from
genuine FHIR R4 conventions is fhir-server's own path (`/schedules`, not
`/Schedule`), its own query-param names (`limit`/`offset`, not FHIR
search's `_count`/`_offset`; `service-category`/`service-type` aliasing
`serviceCategory`/`serviceType`), and — on write only — its own flattened
plain-JSON create/patch body shape (see _schedule_body below).

Logical-identifier fallback fields with no canonical-FHIR source
(`assigner_identifier_*`, `reference_identifier_*`) are never populated
here, same known gap as Organization's/HealthcareService's/
PractitionerRole's translators.
"""


def _coding(c: dict) -> dict:
    """FhirCoding -> a bare {system, code, display} dict."""
    return {
        "system": c.get("system"),
        "code": c.get("code"),
        "display": c.get("display"),
    }


def _period(p: dict | None) -> tuple[str | None, str | None]:
    """FhirPeriod -> (period_start, period_end)."""
    if not p:
        return None, None
    return p.get("start"), p.get("end")


def _identifier(i: dict) -> dict:
    """FhirIdentifier -> ScheduleIdentifierInput-shaped dict. `type.coding[]`
    is a real 0..* list (type_coding). `assigner` is only ever a
    Reference's reference/display on the canonical side — the
    assigner_identifier_* logical-identifier fallback has no source here."""
    period_start, period_end = _period(i.get("period"))
    type_cc = i.get("type") or {}
    assigner = i.get("assigner") or {}
    return {
        "use": i.get("use"),
        "type_coding": [_coding(c) for c in (type_cc.get("coding") or [])] or None,
        "type_text": type_cc.get("text"),
        "system": i.get("system"),
        "value": i.get("value"),
        "period_start": period_start,
        "period_end": period_end,
        "assigner": assigner.get("reference"),
        "assigner_display": assigner.get("display"),
    }


def _cc(cc: dict) -> dict:
    """FhirCodeableConcept -> {coding, text}-shaped dict — shared by
    serviceCategory/serviceType/specialty."""
    return {
        "coding": [_coding(c) for c in (cc.get("coding") or [])] or None,
        "text": cc.get("text"),
    }


def _reference(ref: dict) -> dict:
    """FhirReference -> {reference, reference_display}-shaped dict — used
    by actor."""
    return {
        "reference": ref.get("reference"),
        "reference_display": ref.get("display"),
    }


def _schedule_body(data: dict) -> dict:
    """Canonical FHIR Schedule dict -> fhir-server's flattened
    ScheduleCreateSchema/PatchSchema body. Shared by both — the two
    schemas differ only in which fields are immutable, not in field shape
    for everything this translator populates."""
    period_start, period_end = _period(data.get("planningHorizon"))
    body = {
        "active": data.get("active"),
        "planning_horizon_start": period_start,
        "planning_horizon_end": period_end,
        "comment": data.get("comment"),
        "identifier": [_identifier(i) for i in (data.get("identifier") or [])] or None,
        "service_category": [
            _cc(sc) for sc in (data.get("serviceCategory") or [])
        ]
        or None,
        "service_type": [_cc(st) for st in (data.get("serviceType") or [])] or None,
        "specialty": [_cc(sp) for sp in (data.get("specialty") or [])] or None,
        "actor": [_reference(a) for a in (data.get("actor") or [])] or None,
    }
    return {k: v for k, v in body.items() if v is not None}


class InternalScheduleTranslator:
    """internal (fhir-server). See module docstring for what differs from
    genuine FHIR R4 conventions."""

    accept = "application/fhir+json"

    def item_path(self, schedule_id: str) -> str:
        return f"/schedules/{schedule_id}"

    def list_path(self) -> str:
        return "/schedules"

    def list_params(
        self,
        active: bool | None,
        identifier: str | None,
        service_category: str | None,
        service_type: str | None,
        specialty: str | None,
        actor: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """fhir-server's own router aliases `service_category`/
        `service_type` to the real FHIR R4 search parameter names
        `service-category`/`service-type` — see
        app/routers/schedule/core.py in that project."""
        params: dict = {"limit": limit, "offset": offset}
        if active is not None:
            params["active"] = active
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
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return _schedule_body(data)

    def to_wire_patch(self, data: dict) -> dict:
        return _schedule_body(data)
