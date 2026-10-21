"""
internal (fhir-server) wire translation for the canonical FHIR R4
Organization shape used by app.gql.organization (see
app.connectors.base.OrganizationWireTranslator for the shared contract and
app.gql.organization's package docstring for the overall idea).

Canonical shape already matches fhir-server's own
`Accept: application/fhir+json` response exactly — what actually differs
from genuine FHIR R4 conventions is fhir-server's own path (`/organizations`,
not `/Organization`), its own query-param names (`limit`/`offset`, not FHIR
search's `_count`/`_offset`), and — on write only — its own flattened
plain-JSON create/patch body shape (see _organization_body below).

A handful of fhir-server's flattened fallback fields have no canonical-FHIR
source to translate from at all — `partof_identifier_*`, `assigner_identifier_*`,
`reference_identifier_*` all exist to carry a Reference's *logical-identifier*
fallback (used when there's nothing to resolve a real reference against), but
app.fhir.schemas.datatypes' FhirReference/FhirIdentifier.assigner don't
model one. This translator simply never populates those — a known,
narrower gap than full fhir-server-native write support, not a bug.
"""


def _coding(c: dict) -> dict:
    """FhirCoding -> OrganizationCodingInput-shaped dict."""
    return {
        "system": c.get("system"),
        "code": c.get("code"),
        "display": c.get("display"),
    }


def _codeable_concept_to_type(cc: dict) -> dict:
    """FhirCodeableConcept -> OrganizationTypeInput-shaped dict (used for
    Organization.type; also reused for Organization.identifier.type and
    Organization.contact.purpose via their own flattened *_coding/*_text pairs
    below, since those are the same CodeableConcept shape with a different
    field-name prefix)."""
    return {
        "coding": [_coding(c) for c in (cc.get("coding") or [])] or None,
        "text": cc.get("text"),
    }


def _period(p: dict | None) -> tuple[str | None, str | None]:
    """FhirPeriod -> (period_start, period_end)."""
    if not p:
        return None, None
    return p.get("start"), p.get("end")


def _identifier(i: dict) -> dict:
    """FhirIdentifier -> OrganizationIdentifierInput-shaped dict.
    `assigner` is only ever a Reference's reference/display on the canonical
    side (see FhirIdentifier.assigner's `dict | None` typing) — the
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


def _telecom(t: dict) -> dict:
    """FhirContactPoint -> OrganizationTelecomInput/OrganizationContactTelecomInput
    -shaped dict (identical flattened shape in both places)."""
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
    """FhirAddress -> OrganizationAddressInput-shaped dict."""
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


def _contact(c: dict) -> dict:
    """FhirOrgContact (purpose/name/telecom/address) -> the fully-flattened
    OrganizationContactInput shape — the deepest translation here, since
    fhir-server has no nested name/address BackboneElement here at all."""
    purpose = c.get("purpose") or {}
    name = c.get("name") or {}
    address = c.get("address") or {}
    name_period_start, name_period_end = _period(name.get("period"))
    address_period_start, address_period_end = _period(address.get("period"))
    return {
        "purpose_coding": [_coding(x) for x in (purpose.get("coding") or [])] or None,
        "purpose_text": purpose.get("text"),
        "name_use": name.get("use"),
        "name_text": name.get("text"),
        "name_family": name.get("family"),
        "name_given": name.get("given"),
        "name_prefix": name.get("prefix"),
        "name_suffix": name.get("suffix"),
        "name_period_start": name_period_start,
        "name_period_end": name_period_end,
        "address_use": address.get("use"),
        "address_type": address.get("type"),
        "address_text": address.get("text"),
        "address_line": address.get("line"),
        "address_city": address.get("city"),
        "address_district": address.get("district"),
        "address_state": address.get("state"),
        "address_postal_code": address.get("postalCode"),
        "address_country": address.get("country"),
        "address_period_start": address_period_start,
        "address_period_end": address_period_end,
        "telecom": [_telecom(t) for t in (c.get("telecom") or [])] or None,
    }


def _endpoint(e: dict) -> dict:
    """FhirReference (Organization.endpoint entry) -> OrganizationEndpointInput
    -shaped dict. reference_identifier_* fallback has no source here — same
    reasoning as _identifier's assigner_identifier_* gap."""
    return {"reference": e.get("reference"), "reference_display": e.get("display")}


def _organization_body(data: dict) -> dict:
    """Canonical FHIR Organization dict -> fhir-server's flattened
    OrganizationCreateSchema/OrganizationPatchSchema body. Shared by both —
    those two schemas differ only in docstring, not in field shape, since
    Organization has no required-at-this-layer fields, so create and patch
    bodies are shaped identically."""
    part_of = data.get("partOf") or {}
    body = {
        "active": data.get("active"),
        "name": data.get("name"),
        "partof": part_of.get("reference"),
        "partof_display": part_of.get("display"),
        "identifier": [_identifier(i) for i in (data.get("identifier") or [])] or None,
        "type": [_codeable_concept_to_type(t) for t in (data.get("type") or [])]
        or None,
        "alias": [{"value": a} for a in (data.get("alias") or [])] or None,
        "telecom": [_telecom(t) for t in (data.get("telecom") or [])] or None,
        "address": [_address(a) for a in (data.get("address") or [])] or None,
        "contact": [_contact(c) for c in (data.get("contact") or [])] or None,
        "endpoint": [_endpoint(e) for e in (data.get("endpoint") or [])] or None,
        "extension": data.get("extension"),
    }
    return {k: v for k, v in body.items() if v is not None}


class InternalOrganizationTranslator:
    """internal (fhir-server). See module docstring for what differs from
    genuine FHIR R4 conventions."""

    accept = "application/fhir+json"

    def item_path(self, organization_id: str) -> str:
        return f"/organizations/{organization_id}"

    def list_path(self) -> str:
        return "/organizations"

    def list_params(
        self,
        name: str | None,
        active: bool | None,
        identifier: str | None,
        org_type: str | None,
        address: str | None,
        address_city: str | None,
        address_state: str | None,
        address_postal_code: str | None,
        address_country: str | None,
        address_use: str | None,
        partof: str | None,
        endpoint: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """fhir-server's own router already aliases every one of its query
        params to the real FHIR R4 search parameter name (address-city,
        address-postalcode, ...) — see app/routers/organization/core.py in
        that project — so this is a 1:1 rename, not a translation."""
        params: dict = {"limit": limit, "offset": offset}
        if name is not None:
            params["name"] = name
        if active is not None:
            params["active"] = active
        if identifier is not None:
            params["identifier"] = identifier
        if org_type is not None:
            params["type"] = org_type
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
        if partof is not None:
            params["partof"] = partof
        if endpoint is not None:
            params["endpoint"] = endpoint
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return _organization_body(data)

    def to_wire_patch(self, data: dict) -> dict:
        return _organization_body(data)
