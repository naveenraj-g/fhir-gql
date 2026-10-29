"""
internal (fhir-server) wire translation for the canonical FHIR R4
Encounter shape used by app.gql.encounter (see
app.connectors.base.EncounterWireTranslator for the shared contract and
app.connectors.internal.translators.organization's module docstring for
the overall idea — this mirrors it for Encounter).

Canonical shape already matches fhir-server's own
`Accept: application/fhir+json` response exactly — what differs from
genuine FHIR R4 conventions is fhir-server's own path (`/encounters`, not
`/Encounter`), its own query-param names (`limit`/`offset`, not FHIR
search's `_count`/`_offset`; `class`/`type`/`service-provider`/`part-of`
aliasing `class_code`/`type_code`/`service_provider`/`part_of`), and — on
write only — its own flattened plain-JSON create/patch body shape (see
_encounter_body below).

fhir-server's own EncounterCreateSchema.status already accepts the true
hyphenated FHIR code directly (its Pydantic enum's .value IS the wire
code — see that project's app/models/encounter/enums.py's docstring for
why the *model* layer differs), so `status`/`statusHistory[].status`/
`location[].status` need no translation here, unlike every Reference/
CodeableConcept field. `length.comparator` is the one exception worth
calling out — fhir-server's own wire-level `EncounterLengthComparator`
Pydantic enum also already carries the true symbolic FHIR values
(`<`/`<=`/`>=`/`>`) directly; only fhir-server's *internal* model layer
re-maps them by member name, which this translator never touches.

Logical-identifier fallback fields with no canonical-FHIR source
(`assigner_identifier_*`, `reference_identifier_*`, `individual_identifier_*`,
`condition_identifier_*`, `*_identifier_*` on hospitalization/location)
are never populated here, same known gap as every other resource's
translator (Organization/HealthcareService/PractitionerRole/Schedule/
Slot/Appointment/AppointmentResponse).
"""


def _coding(c: dict) -> dict:
    """FhirCoding -> a bare {system, code, display} dict."""
    return {
        "system": c.get("system"),
        "code": c.get("code"),
        "display": c.get("display"),
    }


def _identifier(i: dict) -> dict:
    """FhirIdentifier -> EncounterIdentifierInput-shaped dict. `type.coding[]`
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
    type/reasonCode/participant.type/diagnosis.use/hospitalization's
    dietPreference/specialCourtesy/specialArrangement list entries."""
    return {
        "coding": [_coding(c) for c in (cc.get("coding") or [])] or None,
        "text": cc.get("text"),
    }


def _reference_item(ref: dict) -> dict:
    """FhirReference -> {reference, reference_display}-shaped dict — shared
    by episodeOfCare/basedOn/appointment/reasonReference/account, each a
    bare 0..* Reference list on the canonical side."""
    return {
        "reference": ref.get("reference"),
        "reference_display": ref.get("display"),
    }


def _period(p: dict) -> dict:
    return {"start": p.get("start"), "end": p.get("end")}


def _status_history(sh: dict) -> dict:
    period = sh.get("period") or {}
    return {
        "status": sh.get("status"),
        "period_start": period.get("start"),
        "period_end": period.get("end"),
    }


def _class_history(ch: dict) -> dict:
    period = ch.get("period") or {}
    return {
        "class_coding": _coding(ch["class"]) if ch.get("class") else None,
        "period_start": period.get("start"),
        "period_end": period.get("end"),
    }


def _participant(p: dict) -> dict:
    """FhirEncounterParticipant -> EncounterParticipantInput-shaped dict."""
    individual = p.get("individual") or {}
    period = p.get("period") or {}
    return {
        "type": [_cc(t) for t in (p.get("type") or [])] or None,
        "period_start": period.get("start"),
        "period_end": period.get("end"),
        "individual": individual.get("reference"),
        "individual_display": individual.get("display"),
    }


def _diagnosis(d: dict) -> dict:
    """FhirEncounterDiagnosis -> EncounterDiagnosisInput-shaped dict."""
    condition = d.get("condition") or {}
    use = d.get("use") or {}
    return {
        "condition": condition.get("reference"),
        "condition_display": condition.get("display"),
        "use_coding": [_coding(c) for c in (use.get("coding") or [])] or None,
        "use_text": use.get("text"),
        "rank": d.get("rank"),
    }


def _hospitalization(h: dict) -> dict:
    """FhirEncounterHospitalization -> EncounterHospitalizationInput-shaped dict."""
    pre_admission_identifier = h.get("preAdmissionIdentifier") or {}
    pre_admission_period = pre_admission_identifier.get("period") or {}
    pre_admission_type = pre_admission_identifier.get("type") or {}
    origin = h.get("origin") or {}
    admit_source = h.get("admitSource") or {}
    re_admission = h.get("reAdmission") or {}
    destination = h.get("destination") or {}
    discharge_disposition = h.get("dischargeDisposition") or {}
    return {
        "pre_admission_identifier_use": pre_admission_identifier.get("use"),
        "pre_admission_identifier_type_coding": [
            _coding(c) for c in (pre_admission_type.get("coding") or [])
        ]
        or None,
        "pre_admission_identifier_type_text": pre_admission_type.get("text"),
        "pre_admission_identifier_system": pre_admission_identifier.get("system"),
        "pre_admission_identifier_value": pre_admission_identifier.get("value"),
        "pre_admission_identifier_period_start": pre_admission_period.get("start"),
        "pre_admission_identifier_period_end": pre_admission_period.get("end"),
        "origin": origin.get("reference"),
        "origin_display": origin.get("display"),
        "admit_source_coding": [
            _coding(c) for c in (admit_source.get("coding") or [])
        ]
        or None,
        "admit_source_text": admit_source.get("text"),
        "re_admission_coding": [
            _coding(c) for c in (re_admission.get("coding") or [])
        ]
        or None,
        "re_admission_text": re_admission.get("text"),
        "diet_preference": [_cc(dp) for dp in (h.get("dietPreference") or [])]
        or None,
        "special_courtesy": [_cc(sc) for sc in (h.get("specialCourtesy") or [])]
        or None,
        "special_arrangement": [
            _cc(sa) for sa in (h.get("specialArrangement") or [])
        ]
        or None,
        "destination": destination.get("reference"),
        "destination_display": destination.get("display"),
        "discharge_disposition_coding": [
            _coding(c) for c in (discharge_disposition.get("coding") or [])
        ]
        or None,
        "discharge_disposition_text": discharge_disposition.get("text"),
    }


def _location_entry(loc: dict) -> dict:
    """FhirEncounterLocation -> EncounterLocationInput-shaped dict."""
    location = loc.get("location") or {}
    physical_type = loc.get("physicalType") or {}
    period = loc.get("period") or {}
    return {
        "location": location.get("reference"),
        "location_display": location.get("display"),
        "status": loc.get("status"),
        "physical_type_coding": [
            _coding(c) for c in (physical_type.get("coding") or [])
        ]
        or None,
        "physical_type_text": physical_type.get("text"),
        "period_start": period.get("start"),
        "period_end": period.get("end"),
    }


def _encounter_body(data: dict) -> dict:
    """Canonical FHIR Encounter dict -> fhir-server's flattened
    EncounterCreateSchema/PatchSchema body. Shared by both — the two
    schemas differ only in which fields are immutable, not in field shape
    for everything this translator populates."""
    service_type = data.get("serviceType") or {}
    priority = data.get("priority") or {}
    subject = data.get("subject") or {}
    length = data.get("length") or {}
    period = data.get("period") or {}
    service_provider = data.get("serviceProvider") or {}
    part_of = data.get("partOf") or {}
    hospitalization = data.get("hospitalization")
    body = {
        "status": data.get("status"),
        "class_coding": _coding(data["class"]) if data.get("class") else None,
        "service_type_coding": [
            _coding(c) for c in (service_type.get("coding") or [])
        ]
        or None,
        "service_type_text": service_type.get("text"),
        "priority_coding": [_coding(c) for c in (priority.get("coding") or [])]
        or None,
        "priority_text": priority.get("text"),
        "subject": subject.get("reference"),
        "subject_display": subject.get("display"),
        "period_start": period.get("start"),
        "period_end": period.get("end"),
        "length_value": length.get("value"),
        "length_comparator": length.get("comparator"),
        "length_unit": length.get("unit"),
        "length_system": length.get("system"),
        "length_code": length.get("code"),
        "service_provider": service_provider.get("reference"),
        "service_provider_display": service_provider.get("display"),
        "part_of": part_of.get("reference"),
        "part_of_display": part_of.get("display"),
        "identifier": [_identifier(i) for i in (data.get("identifier") or [])]
        or None,
        "status_history": [
            _status_history(sh) for sh in (data.get("statusHistory") or [])
        ]
        or None,
        "class_history": [
            _class_history(ch) for ch in (data.get("classHistory") or [])
        ]
        or None,
        "type": [_cc(t) for t in (data.get("type") or [])] or None,
        "episode_of_care": [
            _reference_item(eoc) for eoc in (data.get("episodeOfCare") or [])
        ]
        or None,
        "based_on": [_reference_item(bo) for bo in (data.get("basedOn") or [])]
        or None,
        "appointment": [
            _reference_item(ap) for ap in (data.get("appointment") or [])
        ]
        or None,
        "reason_code": [_cc(rc) for rc in (data.get("reasonCode") or [])] or None,
        "reason_reference": [
            _reference_item(rr) for rr in (data.get("reasonReference") or [])
        ]
        or None,
        "account": [_reference_item(ac) for ac in (data.get("account") or [])]
        or None,
        "participant": [
            _participant(p) for p in (data.get("participant") or [])
        ]
        or None,
        "diagnosis": [_diagnosis(d) for d in (data.get("diagnosis") or [])]
        or None,
        "hospitalization": _hospitalization(hospitalization)
        if hospitalization
        else None,
        "location": [_location_entry(loc) for loc in (data.get("location") or [])]
        or None,
    }
    return {k: v for k, v in body.items() if v is not None}


class InternalEncounterTranslator:
    """internal (fhir-server). See module docstring for what differs from
    genuine FHIR R4 conventions."""

    accept = "application/fhir+json"

    def item_path(self, encounter_id: str) -> str:
        return f"/encounters/{encounter_id}"

    def list_path(self) -> str:
        return "/encounters"

    def list_params(
        self,
        status: str | None,
        identifier: str | None,
        subject: str | None,
        class_code: str | None,
        type_code: str | None,
        service_provider: str | None,
        part_of: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """fhir-server's own router aliases `class_code`/`type_code`/
        `service_provider`/`part_of` to `class`/`type`/`service-provider`/
        `part-of` — see app/routers/encounter/core.py in that project."""
        params: dict = {"limit": limit, "offset": offset}
        if status is not None:
            params["status"] = status
        if identifier is not None:
            params["identifier"] = identifier
        if subject is not None:
            params["subject"] = subject
        if class_code is not None:
            params["class"] = class_code
        if type_code is not None:
            params["type"] = type_code
        if service_provider is not None:
            params["service-provider"] = service_provider
        if part_of is not None:
            params["part-of"] = part_of
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return _encounter_body(data)

    def to_wire_patch(self, data: dict) -> dict:
        return _encounter_body(data)
