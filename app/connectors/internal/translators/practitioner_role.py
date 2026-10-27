"""
internal (fhir-server) wire translation for the canonical FHIR R4
PractitionerRole shape used by app.gql.practitioner_role (see
app.connectors.base.PractitionerRoleWireTranslator for the shared contract
and app.connectors.internal.translators.organization's module docstring for
the overall idea — this mirrors it for PractitionerRole).

Canonical shape already matches fhir-server's own
`Accept: application/fhir+json` response exactly — what differs from
genuine FHIR R4 conventions is fhir-server's own path
(`/practitioner-roles`, not `/PractitionerRole`), its own query-param names
(`limit`/`offset`, not FHIR search's `_count`/`_offset`; `role`/`service`
aliasing `code`/`healthcareService`), and — on write only — its own
flattened plain-JSON create/patch body shape (see _practitioner_role_body
below).

Logical-identifier fallback fields with no canonical-FHIR source
(`assigner_identifier_*`, `practitioner_identifier_*`,
`organization_identifier_*`, `reference_identifier_*`) are never populated
here, same known gap as Organization's/HealthcareService's/Practitioner's
translators.
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
    """FhirIdentifier -> PractitionerRoleIdentifierInput-shaped dict.
    `type.coding[]` is a real 0..* list (type_coding). `assigner` is only
    ever a Reference's reference/display on the canonical side — the
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
    code/specialty."""
    return {
        "coding": [_coding(c) for c in (cc.get("coding") or [])] or None,
        "text": cc.get("text"),
    }


def _reference(ref: dict) -> dict:
    """FhirReference -> {reference, reference_display}-shaped dict —
    shared by location/healthcareService/endpoint."""
    return {
        "reference": ref.get("reference"),
        "reference_display": ref.get("display"),
    }


def _telecom(t: dict) -> dict:
    """FhirContactPoint -> PractitionerRoleTelecomInput-shaped dict."""
    period_start, period_end = _period(t.get("period"))
    return {
        "system": t.get("system"),
        "value": t.get("value"),
        "use": t.get("use"),
        "rank": t.get("rank"),
        "period_start": period_start,
        "period_end": period_end,
    }


def _available_time(at: dict) -> dict:
    """FhirPractitionerRoleAvailableTime -> PractitionerRoleAvailableTimeInput-shaped dict."""
    return {
        "days_of_week": at.get("daysOfWeek"),
        "all_day": at.get("allDay"),
        "available_start_time": at.get("availableStartTime"),
        "available_end_time": at.get("availableEndTime"),
    }


def _not_available(na: dict) -> dict:
    """FhirPractitionerRoleNotAvailable -> PractitionerRoleNotAvailableInput-shaped dict."""
    period_start, period_end = _period(na.get("during"))
    return {
        "description": na.get("description"),
        "during_start": period_start,
        "during_end": period_end,
    }


def _practitioner_role_body(data: dict) -> dict:
    """Canonical FHIR PractitionerRole dict -> fhir-server's flattened
    PractitionerRoleCreateSchema/PatchSchema body. Shared by both — the two
    schemas differ only in which fields are immutable, not in field shape
    for everything this translator populates."""
    period_start, period_end = _period(data.get("period"))
    practitioner = data.get("practitioner") or {}
    organization = data.get("organization") or {}
    body = {
        "active": data.get("active"),
        "period_start": period_start,
        "period_end": period_end,
        "practitioner": practitioner.get("reference"),
        "practitioner_display": practitioner.get("display"),
        "organization": organization.get("reference"),
        "organization_display": organization.get("display"),
        "availability_exceptions": data.get("availabilityExceptions"),
        "identifier": [_identifier(i) for i in (data.get("identifier") or [])] or None,
        "code": [_cc(c) for c in (data.get("code") or [])] or None,
        "specialty": [_cc(sp) for sp in (data.get("specialty") or [])] or None,
        "location": [_reference(loc) for loc in (data.get("location") or [])] or None,
        "healthcare_service": [
            _reference(hs) for hs in (data.get("healthcareService") or [])
        ]
        or None,
        "telecom": [_telecom(t) for t in (data.get("telecom") or [])] or None,
        "available_time": [
            _available_time(at) for at in (data.get("availableTime") or [])
        ]
        or None,
        "not_available": [
            _not_available(na) for na in (data.get("notAvailable") or [])
        ]
        or None,
        "endpoint": [_reference(ep) for ep in (data.get("endpoint") or [])] or None,
    }
    return {k: v for k, v in body.items() if v is not None}


class InternalPractitionerRoleTranslator:
    """internal (fhir-server). See module docstring for what differs from
    genuine FHIR R4 conventions."""

    accept = "application/fhir+json"

    def item_path(self, practitioner_role_id: str) -> str:
        return f"/practitioner-roles/{practitioner_role_id}"

    def list_path(self) -> str:
        return "/practitioner-roles"

    def list_params(
        self,
        active: bool | None,
        identifier: str | None,
        code: str | None,
        specialty: str | None,
        practitioner: str | None,
        organization: str | None,
        location: str | None,
        healthcare_service: str | None,
        endpoint: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """fhir-server's own router aliases `code`/`healthcareService` to
        the real FHIR R4 search parameter names `role`/`service` — see
        app/routers/practitioner_role/core.py in that project."""
        params: dict = {"limit": limit, "offset": offset}
        if active is not None:
            params["active"] = active
        if identifier is not None:
            params["identifier"] = identifier
        if code is not None:
            params["role"] = code
        if specialty is not None:
            params["specialty"] = specialty
        if practitioner is not None:
            params["practitioner"] = practitioner
        if organization is not None:
            params["organization"] = organization
        if location is not None:
            params["location"] = location
        if healthcare_service is not None:
            params["service"] = healthcare_service
        if endpoint is not None:
            params["endpoint"] = endpoint
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return _practitioner_role_body(data)

    def to_wire_patch(self, data: dict) -> dict:
        return _practitioner_role_body(data)
