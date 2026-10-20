"""
Per-connector translation for the universal-FHIR-GraphQL experiment's
Organization resource (see app.connectors.universal's package docstring for
the overall idea). One module per resource — see
app.connectors.universal.translators's __init__.py.

Each translator bridges the one canonical FHIR R4 shape used at the GraphQL
boundary (app.connectors.universal.schemas.organization) to whatever this
backend actually expects on the wire: path conventions, query-param names,
the Accept header needed to get FHIR shape out of a read, and — on write —
the real field-level remapping a non-FHIR-native backend's create/patch
schema requires.

Both of today's connectors already return genuine FHIR R4 JSON for reads —
fhir-server via its own `Accept: application/fhir+json` content
negotiation, Medplum natively — so `from_wire()` is identity for both.

Writes are NOT symmetric with reads, and that asymmetry is the whole reason
this module has a `to_wire_create`/`to_wire_patch` pair instead of one
`to_wire()`: fhir-server's POST/PATCH only ever accept its own flattened
plain-JSON create/patch schemas, never genuine FHIR JSON, unlike its GET
responses (see app.connectors.internal.schemas.organization.input.core's
OrganizationCreateSchema/OrganizationPatchSchema). `InternalOrganizationTranslator`
does the real flattening; `MedplumOrganizationTranslator` stays close to a
pass-through since Medplum is genuinely FHIR-native already. See
dev-docs/18-universal-fhir-graphql-experiment.md.

A handful of fhir-server's flattened fallback fields have no canonical-FHIR
source to translate from at all — `partof_identifier_*`, `assigner_identifier_*`,
`reference_identifier_*` all exist to carry a Reference's *logical-identifier*
fallback (used when there's nothing to resolve a real reference against), but
`app.connectors.universal.schemas.organization.FhirReference`/`FhirIdentifier.assigner`
don't model one. `InternalOrganizationTranslator` simply never populates
those — a known, narrower gap than full fhir-server-native write support,
not a bug.
"""

from typing import Protocol

from app.core.config import settings


class OrganizationWireTranslator(Protocol):
    """One connector's read/write conventions for canonical-FHIR Organization."""

    #: Accept header to request FHIR R4 shape from this backend, or None if
    #: the backend only ever speaks FHIR (nothing to negotiate).
    accept: str | None

    def item_path(self, organization_id: str) -> str:
        """Path for GET-by-id/PATCH/DELETE, in this backend's own convention."""
        ...

    def list_path(self) -> str:
        """Path for GET-collection (search) and POST-create, in this
        backend's own convention."""
        ...

    def list_params(
        self, name: str | None, active: bool | None, limit: int, offset: int
    ) -> dict:
        """Canonical filter/pagination args -> this backend's own query param names."""
        ...

    def from_wire(self, raw: dict) -> dict:
        """This backend's raw response dict -> canonical FHIR Organization
        (or Bundle) dict. Identity for both connectors today — see module
        docstring."""
        ...

    def to_wire_create(self, data: dict) -> dict:
        """Canonical FHIR Organization dict (from FhirOrganizationInput) ->
        this backend's own POST-create body shape."""
        ...

    def to_wire_patch(self, data: dict) -> dict:
        """Canonical FHIR Organization dict (from FhirOrganizationInput) ->
        this backend's own PATCH-update body shape."""
        ...


# ── internal (fhir-server) write-side field mapping ──────────────────────────
#
# Every helper below takes a plain dict sliced out of a canonical-FHIR
# Organization dict (already `model_dump(exclude_none=True)`'d from
# FhirOrganizationInput) and returns a dict shaped like the matching
# fhir-server Organization*Input sub-schema
# (app.connectors.internal.schemas.organization.input).


def _coding(c: dict) -> dict:
    """FhirCoding -> OrganizationCodingInput-shaped dict."""
    return {"system": c.get("system"), "code": c.get("code"), "display": c.get("display")}


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
    OrganizationContactInput shape — the deepest translation in this module,
    since fhir-server has no nested name/address BackboneElement here at all."""
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
    those two schemas differ only in docstring, not in field shape (see
    their module's docstring: Organization has no required-at-this-layer
    fields, so create and patch bodies are shaped identically)."""
    part_of = data.get("partOf") or {}
    body = {
        "active": data.get("active"),
        "name": data.get("name"),
        "partof": part_of.get("reference"),
        "partof_display": part_of.get("display"),
        "identifier": [_identifier(i) for i in (data.get("identifier") or [])] or None,
        "type": [_codeable_concept_to_type(t) for t in (data.get("type") or [])] or None,
        "alias": [{"value": a} for a in (data.get("alias") or [])] or None,
        "telecom": [_telecom(t) for t in (data.get("telecom") or [])] or None,
        "address": [_address(a) for a in (data.get("address") or [])] or None,
        "contact": [_contact(c) for c in (data.get("contact") or [])] or None,
        "endpoint": [_endpoint(e) for e in (data.get("endpoint") or [])] or None,
        "extension": data.get("extension"),
    }
    return {k: v for k, v in body.items() if v is not None}


class InternalOrganizationTranslator:
    """internal (fhir-server). Canonical FHIR shape already matches its
    `Accept: application/fhir+json` response exactly — what actually differs
    from genuine FHIR R4 conventions is fhir-server's own path (`/organizations`,
    not `/Organization`), its own query-param names (`limit`/`offset`,
    not FHIR search's `_count`/`_offset`), and — on write only — its own
    flattened plain-JSON create/patch body shape (see _organization_body)."""

    accept = "application/fhir+json"

    def item_path(self, organization_id: str) -> str:
        return f"/organizations/{organization_id}"

    def list_path(self) -> str:
        return "/organizations"

    def list_params(
        self, name: str | None, active: bool | None, limit: int, offset: int
    ) -> dict:
        params: dict = {"limit": limit, "offset": offset}
        if name is not None:
            params["name"] = name
        if active is not None:
            params["active"] = active
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return _organization_body(data)

    def to_wire_patch(self, data: dict) -> dict:
        return _organization_body(data)


class MedplumOrganizationTranslator:
    """medplum. Genuinely FHIR-native, so canonical path/params/body ARE its
    real path/params/body — this is closer to a pure pass-through than
    `internal`'s translator is in every direction, not just reads."""

    accept = None  # MedplumConnector's Content-Type is already fixed to FHIR.

    def item_path(self, organization_id: str) -> str:
        return f"/Organization/{organization_id}"

    def list_path(self) -> str:
        return "/Organization"

    def list_params(
        self, name: str | None, active: bool | None, limit: int, offset: int
    ) -> dict:
        params: dict = {"_count": limit, "_offset": offset}
        if name is not None:
            params["name"] = name
        if active is not None:
            params["active"] = active
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return {"resourceType": "Organization", **data}

    def to_wire_patch(self, data: dict) -> dict:
        return {"resourceType": "Organization", **data}


ORGANIZATION_TRANSLATORS: dict[str, OrganizationWireTranslator] = {
    "internal": InternalOrganizationTranslator(),
    "medplum": MedplumOrganizationTranslator(),
}


def active_organization_translator() -> OrganizationWireTranslator:
    """The translator for whichever connector configs/config.yaml's
    `connectors.active` currently selects. Shared by both
    app.connectors.universal.gql.queries and .mutations."""
    return ORGANIZATION_TRANSLATORS[settings.connectors.active]
