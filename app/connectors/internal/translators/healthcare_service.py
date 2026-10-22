"""
internal (fhir-server) wire translation for the canonical FHIR R4
HealthcareService shape used by app.gql.healthcare_service (see
app.connectors.base.HealthcareServiceWireTranslator for the shared contract
and app.connectors.internal.translators.organization's module docstring
for the overall idea — this mirrors it for HealthcareService).

Canonical shape already matches fhir-server's own
`Accept: application/fhir+json` response exactly — what differs from
genuine FHIR R4 conventions is fhir-server's own path
(`/healthcare-services`, not `/HealthcareService`), its own query-param
names (`limit`/`offset`, not FHIR search's `_count`/`_offset`), and — on
write only — its own flattened plain-JSON create/patch body shape (see
_healthcare_service_body below).

Every CodeableConcept-list field (category, type, specialty,
serviceProvisionCode, program, characteristic, communication,
referralMethod, identifier.type, eligibility.code) is a real 0..* `coding[]`
list on fhir-server's own Create/PatchSchema — same shape Organization's
own identifier.type/type.coding already uses, so no single-flattened-coding
special-casing is needed here (unlike the original, since-corrected
Location translator).

Logical-identifier fallback fields with no canonical-FHIR source
(`provided_by_identifier_*`, `assigner_identifier_*`,
`reference_identifier_*`) are never populated here, same known gap as
Organization's/Location's translators.
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


def _cc_list_body(cc: dict) -> dict:
    """FhirCodeableConcept -> {coding: [...], text} dict — shared by every
    HealthcareService CodeableConcept-list field (category/type/specialty/
    serviceProvisionCode/program/characteristic/communication/
    referralMethod)."""
    return {
        "coding": [_coding(c) for c in (cc.get("coding") or [])] or None,
        "text": cc.get("text"),
    }


def _identifier(i: dict) -> dict:
    """FhirIdentifier -> HealthcareServiceIdentifierInput-shaped dict.
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


def _reference_entry(r: dict) -> dict:
    """FhirReference (location[]/coverageArea[]/endpoint[] entry) ->
    {reference, reference_display}-shaped dict. reference_identifier_*
    fallback has no source here — same reasoning as _identifier's
    assigner_identifier_* gap."""
    return {"reference": r.get("reference"), "reference_display": r.get("display")}


def _telecom(t: dict) -> dict:
    """FhirContactPoint -> HealthcareServiceTelecomInput-shaped dict."""
    period_start, period_end = _period(t.get("period"))
    return {
        "system": t.get("system"),
        "value": t.get("value"),
        "use": t.get("use"),
        "rank": t.get("rank"),
        "period_start": period_start,
        "period_end": period_end,
    }


def _eligibility(e: dict) -> dict:
    """FhirHealthcareServiceEligibility -> HealthcareServiceEligibilityInput
    -shaped dict. `code.coding[]` is a real 0..* list (code_coding)."""
    code_cc = e.get("code") or {}
    return {
        "code_coding": [_coding(c) for c in (code_cc.get("coding") or [])] or None,
        "code_text": code_cc.get("text"),
        "comment": e.get("comment"),
    }


def _available_time(at: dict) -> dict:
    """FhirHealthcareServiceAvailableTime -> HealthcareServiceAvailableTimeInput
    -shaped dict."""
    return {
        "days_of_week": at.get("daysOfWeek"),
        "all_day": at.get("allDay"),
        "available_start_time": at.get("availableStartTime"),
        "available_end_time": at.get("availableEndTime"),
    }


def _not_available(na: dict) -> dict:
    """FhirHealthcareServiceNotAvailable -> HealthcareServiceNotAvailableInput
    -shaped dict."""
    during_start, during_end = _period(na.get("during"))
    return {
        "description": na.get("description"),
        "during_start": during_start,
        "during_end": during_end,
    }


def _healthcare_service_body(data: dict) -> dict:
    """Canonical FHIR HealthcareService dict -> fhir-server's flattened
    HealthcareServiceCreateSchema/PatchSchema body. Shared by both — the
    two schemas differ in which fields are required, not in field shape."""
    provided_by = data.get("providedBy") or {}
    photo = data.get("photo") or {}
    body = {
        "active": data.get("active"),
        "name": data.get("name"),
        "provided_by": provided_by.get("reference"),
        "provided_by_display": provided_by.get("display"),
        "comment": data.get("comment"),
        "extra_details": data.get("extraDetails"),
        "photo_content_type": photo.get("contentType"),
        "photo_language": photo.get("language"),
        "photo_data": photo.get("data"),
        "photo_url": photo.get("url"),
        "photo_size": photo.get("size"),
        "photo_hash": photo.get("hash"),
        "photo_title": photo.get("title"),
        "photo_creation": photo.get("creation"),
        "appointment_required": data.get("appointmentRequired"),
        "availability_exceptions": data.get("availabilityExceptions"),
        "identifier": [_identifier(i) for i in (data.get("identifier") or [])] or None,
        "category": [_cc_list_body(c) for c in (data.get("category") or [])] or None,
        "type": [_cc_list_body(t) for t in (data.get("type") or [])] or None,
        "specialty": [_cc_list_body(s) for s in (data.get("specialty") or [])] or None,
        "location": [_reference_entry(l) for l in (data.get("location") or [])]
        or None,
        "telecom": [_telecom(t) for t in (data.get("telecom") or [])] or None,
        "coverage_area": [
            _reference_entry(ca) for ca in (data.get("coverageArea") or [])
        ]
        or None,
        "service_provision_code": [
            _cc_list_body(s) for s in (data.get("serviceProvisionCode") or [])
        ]
        or None,
        "eligibility": [
            _eligibility(e) for e in (data.get("eligibility") or [])
        ]
        or None,
        "program": [_cc_list_body(p) for p in (data.get("program") or [])] or None,
        "characteristic": [
            _cc_list_body(c) for c in (data.get("characteristic") or [])
        ]
        or None,
        "communication": [
            _cc_list_body(c) for c in (data.get("communication") or [])
        ]
        or None,
        "referral_method": [
            _cc_list_body(r) for r in (data.get("referralMethod") or [])
        ]
        or None,
        "available_time": [
            _available_time(at) for at in (data.get("availableTime") or [])
        ]
        or None,
        "not_available": [
            _not_available(na) for na in (data.get("notAvailable") or [])
        ]
        or None,
        "endpoint": [_reference_entry(e) for e in (data.get("endpoint") or [])]
        or None,
    }
    return {k: v for k, v in body.items() if v is not None}


class InternalHealthcareServiceTranslator:
    """internal (fhir-server). See module docstring for what differs from
    genuine FHIR R4 conventions."""

    accept = "application/fhir+json"

    def item_path(self, healthcare_service_id: str) -> str:
        return f"/healthcare-services/{healthcare_service_id}"

    def list_path(self) -> str:
        return "/healthcare-services"

    def list_params(
        self,
        name: str | None,
        identifier: str | None,
        active: bool | None,
        category: str | None,
        service_type: str | None,
        specialty: str | None,
        characteristic: str | None,
        program: str | None,
        organization: str | None,
        location: str | None,
        coverage_area: str | None,
        endpoint: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """fhir-server's own router already aliases every one of its query
        params to the real FHIR R4 search parameter name (service-category,
        service-type, organization, coverage-area, ...) — see
        app/routers/healthcare_service/core.py in that project — so this is
        a 1:1 rename, not a translation."""
        params: dict = {"limit": limit, "offset": offset}
        if name is not None:
            params["name"] = name
        if identifier is not None:
            params["identifier"] = identifier
        if active is not None:
            params["active"] = active
        if category is not None:
            params["service-category"] = category
        if service_type is not None:
            params["service-type"] = service_type
        if specialty is not None:
            params["specialty"] = specialty
        if characteristic is not None:
            params["characteristic"] = characteristic
        if program is not None:
            params["program"] = program
        if organization is not None:
            params["organization"] = organization
        if location is not None:
            params["location"] = location
        if coverage_area is not None:
            params["coverage-area"] = coverage_area
        if endpoint is not None:
            params["endpoint"] = endpoint
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return _healthcare_service_body(data)

    def to_wire_patch(self, data: dict) -> dict:
        return _healthcare_service_body(data)
