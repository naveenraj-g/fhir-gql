"""
internal (fhir-server) wire translation for the canonical FHIR R4
Practitioner shape used by app.gql.practitioner (see
app.connectors.base.PractitionerWireTranslator for the shared contract and
app.connectors.internal.translators.organization's module docstring for
the overall idea — this mirrors it for Practitioner).

Canonical shape already matches fhir-server's own
`Accept: application/fhir+json` response exactly — what differs from
genuine FHIR R4 conventions is fhir-server's own path (`/practitioners`,
not `/Practitioner`), its own query-param names (`limit`/`offset`, not FHIR
search's `_count`/`_offset`), and — on write only — its own flattened
plain-JSON create/patch body shape (see _practitioner_body below).

Unlike Organization/Location/HealthcareService, fhir-server's own
PractitionerCreateSchema keeps a plain `user_id` field — but it has no
FHIR R4 Practitioner source to translate from (see
app.fhir.schemas.practitioner.FhirPractitionerInput's docstring), so it's
simply never populated here, same narrower-gap shape as the
assigner_identifier_*/reference_identifier_* fallbacks below.

Logical-identifier fallback fields with no canonical-FHIR source
(`assigner_identifier_*`, `issuer_identifier_*`) are never populated here,
same known gap as Organization's/HealthcareService's translators.
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
    """FhirIdentifier -> PractitionerIdentifierInput-shaped dict.
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


def _name(n: dict) -> dict:
    """FhirHumanName -> PractitionerNameInput-shaped dict."""
    period_start, period_end = _period(n.get("period"))
    return {
        "use": n.get("use"),
        "text": n.get("text"),
        "family": n.get("family"),
        "given": n.get("given"),
        "prefix": n.get("prefix"),
        "suffix": n.get("suffix"),
        "period_start": period_start,
        "period_end": period_end,
    }


def _telecom(t: dict) -> dict:
    """FhirContactPoint -> PractitionerTelecomInput-shaped dict."""
    period_start, period_end = _period(t.get("period"))
    return {
        "system": t.get("system"),
        "value": t.get("value"),
        "use": t.get("use"),
        "rank": t.get("rank"),
        "period_start": period_start,
        "period_end": period_end,
    }


def _address(a: dict) -> dict:
    """FhirAddress -> PractitionerAddressInput-shaped dict."""
    period_start, period_end = _period(a.get("period"))
    return {
        "use": a.get("use"),
        "type": a.get("type"),
        "text": a.get("text"),
        "line": a.get("line"),
        "city": a.get("city"),
        "district": a.get("district"),
        "state": a.get("state"),
        "postal_code": a.get("postalCode"),
        "country": a.get("country"),
        "period_start": period_start,
        "period_end": period_end,
    }


def _photo(p: dict) -> dict:
    """FhirAttachment -> PractitionerPhotoInput-shaped dict — unprefixed
    (unlike HealthcareService's flattened photo_* columns) since
    Practitioner.photo is a real 0..* child table."""
    return {
        "content_type": p.get("contentType"),
        "language": p.get("language"),
        "data": p.get("data"),
        "url": p.get("url"),
        "size": p.get("size"),
        "hash": p.get("hash"),
        "title": p.get("title"),
        "creation": p.get("creation"),
    }


def _qualification(q: dict) -> dict:
    """FhirPractitionerQualification -> PractitionerQualificationInput
    -shaped dict. `code.coding[]` is a real 0..* list (code_coding).
    `issuer` is only ever a Reference's reference/display on the canonical
    side — the issuer_identifier_* logical-identifier fallback has no
    source here."""
    code_cc = q.get("code") or {}
    period_start, period_end = _period(q.get("period"))
    issuer = q.get("issuer") or {}
    return {
        "identifier": [_identifier(i) for i in (q.get("identifier") or [])] or None,
        "code_coding": [_coding(c) for c in (code_cc.get("coding") or [])] or None,
        "code_text": code_cc.get("text"),
        "period_start": period_start,
        "period_end": period_end,
        "issuer": issuer.get("reference"),
        "issuer_display": issuer.get("display"),
    }


def _communication(c: dict) -> dict:
    """FhirCodeableConcept -> PractitionerCommunicationInput-shaped dict."""
    return {
        "coding": [_coding(x) for x in (c.get("coding") or [])] or None,
        "text": c.get("text"),
    }


def _practitioner_body(data: dict) -> dict:
    """Canonical FHIR Practitioner dict -> fhir-server's flattened
    PractitionerCreateSchema/PatchSchema body. Shared by both — the two
    schemas differ only in which fields are immutable (user_id), not in
    field shape for everything this translator populates."""
    body = {
        "active": data.get("active"),
        "gender": data.get("gender"),
        "birth_date": data.get("birthDate"),
        "identifier": [_identifier(i) for i in (data.get("identifier") or [])] or None,
        "name": [_name(n) for n in (data.get("name") or [])] or None,
        "telecom": [_telecom(t) for t in (data.get("telecom") or [])] or None,
        "address": [_address(a) for a in (data.get("address") or [])] or None,
        "photo": [_photo(p) for p in (data.get("photo") or [])] or None,
        "qualification": [
            _qualification(q) for q in (data.get("qualification") or [])
        ]
        or None,
        "communication": [
            _communication(c) for c in (data.get("communication") or [])
        ]
        or None,
        "extension": data.get("extension"),
    }
    return {k: v for k, v in body.items() if v is not None}


class InternalPractitionerTranslator:
    """internal (fhir-server). See module docstring for what differs from
    genuine FHIR R4 conventions."""

    accept = "application/fhir+json"

    def item_path(self, practitioner_id: str) -> str:
        return f"/practitioners/{practitioner_id}"

    def list_path(self) -> str:
        return "/practitioners"

    def list_params(
        self,
        name: str | None,
        family: str | None,
        given: str | None,
        identifier: str | None,
        active: bool | None,
        gender: str | None,
        communication: str | None,
        telecom: str | None,
        phone: str | None,
        email: str | None,
        address: str | None,
        address_city: str | None,
        address_state: str | None,
        address_postal_code: str | None,
        address_country: str | None,
        address_use: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """fhir-server's own router already aliases every one of its query
        params to the real FHIR R4 search parameter name (address-city,
        address-postalcode, ...) — see app/routers/practitioner/core.py in
        that project — so this is a 1:1 rename, not a translation."""
        params: dict = {"limit": limit, "offset": offset}
        if name is not None:
            params["name"] = name
        if family is not None:
            params["family"] = family
        if given is not None:
            params["given"] = given
        if identifier is not None:
            params["identifier"] = identifier
        if active is not None:
            params["active"] = active
        if gender is not None:
            params["gender"] = gender
        if communication is not None:
            params["communication"] = communication
        if telecom is not None:
            params["telecom"] = telecom
        if phone is not None:
            params["phone"] = phone
        if email is not None:
            params["email"] = email
        if address is not None:
            params["address"] = address
        if address_city is not None:
            params["address-city"] = address_city
        if address_state is not None:
            params["address-state"] = address_state
        if address_postal_code is not None:
            params["address-postalcode"] = address_postal_code
        if address_country is not None:
            params["address-country"] = address_country
        if address_use is not None:
            params["address-use"] = address_use
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return _practitioner_body(data)

    def to_wire_patch(self, data: dict) -> dict:
        return _practitioner_body(data)
