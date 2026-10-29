"""
internal (fhir-server) wire translation for the canonical FHIR R4 Location
shape used by app.gql.location (see app.connectors.base.LocationWireTranslator
for the shared contract and app.connectors.internal.translators.organization's
module docstring for the overall idea — this mirrors it exactly for Location).

Canonical shape already matches fhir-server's own
`Accept: application/fhir+json` response exactly — what differs from
genuine FHIR R4 conventions is fhir-server's own path (`/locations`, not
`/Location`), its own query-param names (`limit`/`offset`, not FHIR
search's `_count`/`_offset`), and — on write only — its own flattened
plain-JSON create/patch body shape (see _location_body below).

One field-shape difference from Organization's own translator worth
flagging explicitly:
- Location.address is 0..1 (flattened directly onto the body), not 0..*
  like Organization.address — so there's no per-entry translator function,
  just one `_address()` call.

Location.identifier.type, Location.type, and Location.physicalType are
each a real 0..* `coding[]` list on fhir-server's own
LocationIdentifierInput/LocationTypeInput/LocationCreateSchema now (`type_coding`/
`coding`/`physical_type_coding` respectively) — same as Organization's own
identifier.type/type.coding — NOT a single flattened coding. There is no
`physical_type` search filter either: physicalType is a real Location
field, but it was never a registered FHIR R4 SearchParameter for Location
(https://hl7.org/fhir/R4/location.html#search).

Logical-identifier fallback fields with no canonical-FHIR source
(`managing_organization_identifier_*`, `part_of_identifier_*`,
`reference_identifier_*`) are never populated here, same known gap as
Organization's translator.
"""


def _coding(c: dict) -> dict:
    """FhirCoding -> a bare {system, code, display} dict. Shared shape for
    every flattened Coding/CodeableConcept-first-coding below."""
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
    """FhirIdentifier -> LocationIdentifierInput-shaped dict. `type.coding[]`
    is a real 0..* list (type_coding) — a deployment may need its own
    custom identifier-type code AND a standard crosswalk at once — same as
    Organization's identifier.type. `assigner` is only ever a Reference's
    reference/display on the canonical side — the assigner_identifier_*
    logical-identifier fallback has no source here."""
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


def _location_type(cc: dict) -> dict:
    """FhirCodeableConcept -> LocationTypeInput-shaped dict — `coding[]` is
    a real 0..* list, same reasoning as _identifier's type_coding above."""
    return {
        "coding": [_coding(c) for c in (cc.get("coding") or [])] or None,
        "text": cc.get("text"),
    }


def _telecom(t: dict) -> dict:
    """FhirContactPoint -> LocationTelecomInput-shaped dict."""
    period_start, period_end = _period(t.get("period"))
    return {
        "system": t.get("system"),
        "value": t.get("value"),
        "use": t.get("use"),
        "rank": t.get("rank"),
        "period_start": period_start,
        "period_end": period_end,
    }


def _address(a: dict | None) -> dict:
    """FhirAddress -> flattened `address_*` fields on the Location body
    itself. Location.address is 0..1, unlike Organization.address's 0..*,
    so there's no per-entry wrapper — this is called once."""
    a = a or {}
    period_start, period_end = _period(a.get("period"))
    return {
        "address_use": a.get("use"),
        "address_type": a.get("type"),
        "address_text": a.get("text"),
        "address_line": a.get("line"),
        "address_city": a.get("city"),
        "address_district": a.get("district"),
        "address_state": a.get("state"),
        "address_postal_code": a.get("postalCode"),
        "address_country": a.get("country"),
        "address_period_start": period_start,
        "address_period_end": period_end,
    }


def _physical_type(cc: dict | None) -> dict:
    """FhirCodeableConcept (Location.physicalType) -> flattened
    `physical_type_coding`/`physical_type_text` fields on the Location body.
    `physical_type_coding` is a real 0..* list — physicalType itself is
    0..1 at the Location level, but its own coding[] is still 0..* per
    spec, same reasoning as _location_type/_identifier above."""
    cc = cc or {}
    return {
        "physical_type_coding": [_coding(c) for c in (cc.get("coding") or [])]
        or None,
        "physical_type_text": cc.get("text"),
    }


def _operational_status(c: dict | None) -> dict:
    """FhirCoding (Location.operationalStatus) -> flattened
    `operational_status_*` fields. A Coding, not a CodeableConcept — no
    `text` sibling."""
    c = c or {}
    return {
        "operational_status_system": c.get("system"),
        "operational_status_code": c.get("code"),
        "operational_status_display": c.get("display"),
    }


def _position(p: dict | None) -> dict:
    """FhirLocationPosition -> flattened `position_*` fields."""
    p = p or {}
    return {
        "position_longitude": p.get("longitude"),
        "position_latitude": p.get("latitude"),
        "position_altitude": p.get("altitude"),
    }


def _hours_of_operation(h: dict) -> dict:
    """FhirLocationHoursOfOperation -> LocationHoursOfOperationInput-shaped
    dict."""
    return {
        "days_of_week": h.get("daysOfWeek"),
        "all_day": h.get("allDay"),
        "opening_time": h.get("openingTime"),
        "closing_time": h.get("closingTime"),
    }


def _endpoint(e: dict) -> dict:
    """FhirReference (Location.endpoint entry) -> LocationEndpointInput
    -shaped dict. reference_identifier_* fallback has no source here —
    same reasoning as _identifier's assigner_identifier_* gap."""
    return {"reference": e.get("reference"), "reference_display": e.get("display")}


def _location_body(data: dict) -> dict:
    """Canonical FHIR Location dict -> fhir-server's flattened
    LocationCreateSchema/LocationPatchSchema body. Shared by both — the two
    schemas differ in which fields are required, not in field shape."""
    managing_org = data.get("managingOrganization") or {}
    part_of = data.get("partOf") or {}
    body = {
        "status": data.get("status"),
        "mode": data.get("mode"),
        "name": data.get("name"),
        "description": data.get("description"),
        **_operational_status(data.get("operationalStatus")),
        **_address(data.get("address")),
        **_physical_type(data.get("physicalType")),
        **_position(data.get("position")),
        "managing_organization": managing_org.get("reference"),
        "managing_organization_display": managing_org.get("display"),
        "part_of": part_of.get("reference"),
        "part_of_display": part_of.get("display"),
        "availability_exceptions": data.get("availabilityExceptions"),
        "identifier": [_identifier(i) for i in (data.get("identifier") or [])] or None,
        "type": [_location_type(t) for t in (data.get("type") or [])] or None,
        "alias": list(data.get("alias") or []) or None,
        "telecom": [_telecom(t) for t in (data.get("telecom") or [])] or None,
        "hours_of_operation": [
            _hours_of_operation(h) for h in (data.get("hoursOfOperation") or [])
        ]
        or None,
        "endpoint": [_endpoint(e) for e in (data.get("endpoint") or [])] or None,
    }
    return {k: v for k, v in body.items() if v is not None}


class InternalLocationTranslator:
    """internal (fhir-server). See module docstring for what differs from
    genuine FHIR R4 conventions."""

    accept = "application/fhir+json"

    def item_path(self, location_id: str) -> str:
        return f"/locations/{location_id}"

    def list_path(self) -> str:
        return "/locations"

    def list_params(
        self,
        name: str | None,
        identifier: str | None,
        status: str | None,
        operational_status: str | None,
        location_type: str | None,
        address: str | None,
        address_city: str | None,
        address_state: str | None,
        address_postal_code: str | None,
        address_country: str | None,
        address_use: str | None,
        organization: str | None,
        partof: str | None,
        endpoint: str | None,
        near: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """fhir-server's own router already aliases every one of its query
        params to the real FHIR R4 search parameter name (operational-status,
        address-city, ...) — see app/routers/location/core.py in that
        project — so this is a 1:1 rename, not a translation."""
        params: dict = {"limit": limit, "offset": offset}
        if name is not None:
            params["name"] = name
        if identifier is not None:
            params["identifier"] = identifier
        if status is not None:
            params["status"] = status
        if operational_status is not None:
            params["operational-status"] = operational_status
        if location_type is not None:
            params["type"] = location_type
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
        if organization is not None:
            params["organization"] = organization
        if partof is not None:
            params["partof"] = partof
        if endpoint is not None:
            params["endpoint"] = endpoint
        if near is not None:
            params["near"] = near
        return params

    def from_wire(self, raw: dict) -> dict:
        return raw

    def to_wire_create(self, data: dict) -> dict:
        return _location_body(data)

    def to_wire_patch(self, data: dict) -> dict:
        return _location_body(data)
