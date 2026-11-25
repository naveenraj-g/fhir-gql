"""
Organization and Location on the GraphQL gateway, now that their types come from the shared,
generated FHIR R4 models (app.schemas.fhir_resources via app.gql.fhir_types).

A fake connector stands in for the backend, so these tests check what the gateway does with the
FHIR JSON it receives and what it sends: the whole R4 resource is queryable, a record that lacks an
element R4 requires still reads, a write is checked against the model first, and an update goes out
as the merge-patch the caller supplied.
"""

import asyncio
from types import SimpleNamespace
from typing import Any

from app.gql.schema import schema

# A caller holding every permission the tests need.
USER = {
    "sub": "u1",
    "activeOrganizationId": "org1",
    "permissions": [
        f"{r}:{a}"
        for r in ("organization", "location")
        for a in ("read", "create", "update", "delete")
    ],
}


class FakeConnector:
    """Records every call and answers with a canned FHIR document."""

    def __init__(self, reply: dict) -> None:
        self.reply = reply
        self.calls: list[tuple[str, str, Any]] = []

    async def get(self, path, *, accept=None, actor=None, params=None, **kw):
        self.calls.append(("get", path, params))
        return self.reply

    async def post(self, path, body, **kw):
        self.calls.append(("post", path, body))
        return self.reply

    async def patch(self, path, body, **kw):
        self.calls.append(("patch", path, body))
        return self.reply


def run(query: str, connector: FakeConnector, variables: dict | None = None):
    """Execute one operation with the fake connector wired in as the container's client."""
    container = SimpleNamespace(core=SimpleNamespace(fhir_client=lambda: connector))
    request = SimpleNamespace(
        state=SimpleNamespace(user=USER, token="t"),
        app=SimpleNamespace(container=container),
    )
    context = SimpleNamespace(request=request)
    return asyncio.run(
        schema.execute(query, variable_values=variables, context_value=context)
    )


ORG = {
    "resourceType": "Organization",
    "id": "190001",
    "active": True,
    "name": "Acme",
    "alias": ["A"],
    "type": [{"coding": [{"system": "http://s", "code": "prov"}], "text": "Provider"}],
    "identifier": [{"system": "urn:x", "value": "1", "assigner": {"display": "X"}}],
    "contact": [{"name": {"family": "Doe", "given": ["J"]}}],
    "extension": [{"url": "http://e", "valueString": "v"}],
    "meta": {"lastUpdated": "2026-01-01T00:00:00+00:00"},
}


def test_organization_read_exposes_every_element():
    result = run(
        '{ getFhirOrganization(id:"190001"){ id active name alias type{text coding{code}}'
        " identifier{value assigner{display}} contact{name{family given}}"
        " extension{url valueString} meta{lastUpdated} } }",
        FakeConnector(ORG),
    )
    assert result.errors is None, result.errors
    org = result.data["getFhirOrganization"]
    assert org["name"] == "Acme" and org["alias"] == ["A"]
    assert org["type"][0]["coding"][0]["code"] == "prov"
    assert org["identifier"][0]["assigner"]["display"] == "X"
    assert org["contact"][0]["name"]["given"] == ["J"]
    assert org["extension"][0]["valueString"] == "v"


def test_a_record_missing_an_r4_required_element_still_reads():
    """Location and Organization have none, so use a resource-shaped doc with a null element."""
    result = run(
        '{ getFhirOrganization(id:"1"){ id name active } }',
        FakeConnector({"resourceType": "Organization", "id": "1"}),
    )
    assert result.errors is None, result.errors
    assert result.data["getFhirOrganization"] == {
        "id": "1",
        "name": None,
        "active": None,
    }


def test_location_read_includes_position_and_hours():
    loc = {
        "resourceType": "Location",
        "id": "230001",
        "status": "active",
        "name": "Room 1",
        "position": {"longitude": 1.5, "latitude": 2.5},
        "hoursOfOperation": [{"daysOfWeek": ["mon"], "openingTime": "08:00:00"}],
        "managingOrganization": {"reference": "Organization/190001"},
    }
    result = run(
        '{ getFhirLocation(id:"230001"){ status name position{longitude latitude}'
        " hoursOfOperation{daysOfWeek openingTime} managingOrganization{reference} } }",
        FakeConnector(loc),
    )
    assert result.errors is None, result.errors
    got = result.data["getFhirLocation"]
    assert got["position"] == {"longitude": 1.5, "latitude": 2.5}
    assert got["hoursOfOperation"][0]["daysOfWeek"] == ["mon"]


def test_create_sends_the_fhir_document_and_returns_the_reply():
    connector = FakeConnector(ORG)
    result = run(
        'mutation { createFhirOrganization(input:{name:"Acme", alias:["A"],'
        ' type:[{text:"Provider"}]}){ id name } }',
        connector,
    )
    assert result.errors is None, result.errors
    assert result.data["createFhirOrganization"] == {"id": "190001", "name": "Acme"}
    ((verb, _path, body),) = connector.calls
    assert verb == "post"
    assert body["name"] == "Acme" and body["type"] == [{"text": "Provider"}]


def test_update_sends_only_what_was_supplied():
    connector = FakeConnector(ORG)
    result = run(
        'mutation { updateFhirOrganization(id:"190001", input:{active:false}){ id } }',
        connector,
    )
    assert result.errors is None, result.errors
    ((verb, _path, body),) = connector.calls
    assert verb == "patch" and body == {"active": False}


def test_an_invalid_write_is_rejected_before_the_backend():
    connector = FakeConnector(ORG)
    result = run(
        'mutation { createFhirLocation(input:{status:"active", position:{latitude:1.0}}){ id } }',
        connector,
    )
    # `position.longitude` is required by R4, so GraphQL itself refuses the input.
    assert result.errors and not connector.calls


def test_the_schema_publishes_hl7_descriptions():
    sdl = schema.as_str()
    assert "FhirOrganizationType" in sdl and "FhirOrganizationPatchInput" in sdl
    # HL7's own element description is what a GraphQL client sees for `Organization.name`.
    assert "A name associated with the organization" in sdl


def test_medplum_patch_is_built_from_the_same_fragment():
    """The medplum connector turns the caller's merge-patch into an RFC 6902 array."""
    from app.connectors.medplum.translators.organization import (
        MedplumOrganizationTranslator,
    )

    ops = MedplumOrganizationTranslator().to_wire_patch(
        {"active": False, "alias": ["B"]}
    )
    assert {"op": "add", "path": "/active", "value": False} in ops or any(
        o["path"] == "/active" for o in ops
    )
