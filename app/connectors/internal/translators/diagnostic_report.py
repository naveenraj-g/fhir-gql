"""
internal (fhir-server) wire translation for the canonical FHIR R4
DiagnosticReport shape used by app.gql.diagnostic_report. See
app.connectors.internal.translators.observation's module docstring for
the overall idea — this mirrors it for DiagnosticReport.

**DiagnosticReport is now one of fhir-server's auth-rollout
resources**, same as Observation/ServiceRequest/MedicationRequest/
Questionnaire/etc. — fhir-server derives `org_id`/`created_by`/
`updated_by` from the forwarded JWT itself, so `to_wire_create`/
`to_wire_patch` take no extra keyword-only arguments, same shape as
every other resource's translator. `user_id` is still a plain
fhir-server field, but has no canonical-FHIR source to translate
from, so it's simply never populated here.
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


def _media(m: dict) -> dict:
    link = m.get("link") or {}
    return {
        "comment": m.get("comment"),
        "link_reference": link.get("reference"),
        "link_display": link.get("display"),
    }


def _presented_form(a: dict) -> dict:
    return {
        "content_type": a.get("contentType"),
        "language": a.get("language"),
        "data": a.get("data"),
        "url": a.get("url"),
        "size": a.get("size"),
        "hash": a.get("hash"),
        "title": a.get("title"),
        "creation": a.get("creation"),
    }


def _dr_body(data: dict) -> dict:
    """Canonical FHIR DiagnosticReport dict -> fhir-server's flattened
    DiagnosticReportCreateSchema/PatchSchema body (minus the audit/tenant
    fields — those are added by `to_wire_create`/`to_wire_patch` below)."""
    effective_period = data.get("effectivePeriod") or {}

    body = {
        "extension": data.get("extension"),
        "identifier": [_identifier(i) for i in (data.get("identifier") or [])] or None,
        "based_on": [_reference(r) for r in (data.get("basedOn") or [])] or None,
        "status": data.get("status"),
        "category": [_codeable_concept(c) for c in (data.get("category") or [])] or None,
        "code": _codeable_concept(data["code"]) if data.get("code") else None,
        "subject": _reference(data["subject"]) if data.get("subject") else None,
        "encounter": _reference(data["encounter"]) if data.get("encounter") else None,
        "effective_date_time": data.get("effectiveDateTime"),
        "effective_period_start": effective_period.get("start"),
        "effective_period_end": effective_period.get("end"),
        "issued": data.get("issued"),
        "performer": [_reference(r) for r in (data.get("performer") or [])] or None,
        "results_interpreter": [_reference(r) for r in (data.get("resultsInterpreter") or [])] or None,
        "specimen": [_reference(r) for r in (data.get("specimen") or [])] or None,
        "result": [_reference(r) for r in (data.get("result") or [])] or None,
        "imaging_study": [_reference(r) for r in (data.get("imagingStudy") or [])] or None,
        "media": [_media(m) for m in (data.get("media") or [])] or None,
        "conclusion": data.get("conclusion"),
        "conclusion_code": [_codeable_concept(c) for c in (data.get("conclusionCode") or [])] or None,
        "presented_form": [_presented_form(a) for a in (data.get("presentedForm") or [])] or None,
    }
    return {k: v for k, v in body.items() if v is not None}


class InternalDiagnosticReportTranslator:
    """internal (fhir-server). See module docstring for why
    `to_wire_create`/`to_wire_patch` take extra keyword-only arguments."""

    accept = "application/fhir+json"

    def item_path(self, diagnostic_report_id: str) -> str:
        return f"/diagnostic-reports/{diagnostic_report_id}"

    def list_path(self) -> str:
        return "/diagnostic-reports"

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
        return _dr_body(data)

    def to_wire_patch(self, data: dict) -> dict:
        return _dr_body(data)
