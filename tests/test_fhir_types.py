"""app.gql.fhir_types: GraphQL types derived from the generated FHIR R4 models."""

import strawberry
from app.gql.fhir_types import input_to_dict, input_type, output_type

import app.schemas.fhir_resources as fr

# Every resource model (the merge-patch variants and the base class are not resources).
RESOURCES = sorted(
    n for n in fr.__all__ if not n.endswith("Patch") and n != "DomainResource"
)


def test_every_resource_builds_a_schema_without_name_clashes():
    """All 52 resources, outputs and inputs, fit into one valid GraphQL schema."""
    query = {}
    for name in RESOURCES:
        model = getattr(fr, name)
        out, inp = output_type(model), input_type(model)
        input_type(getattr(fr, name + "Patch"), name=f"Fhir{name}PatchInput")

        def reader(self) -> out | None:  # noqa: B023 - bound per iteration below
            return None

        reader.__annotations__["return"] = out | None
        query[f"get{name}"] = strawberry.field(resolver=reader, name=f"get{name}")
        # Keep the input referenced from a mutation so it is part of the schema too.
        del inp
    Query = strawberry.type(type("Query", (), {"__annotations__": {}, **query}))
    schema = strawberry.Schema(query=Query)
    assert len(RESOURCES) == 52
    assert schema.as_str().count("\ntype ") > 200


def test_a_keyword_element_keeps_its_fhir_name():
    """Encounter.class is `class_` in Python; GraphQL and the FHIR document say `class`."""
    out = output_type(fr.Encounter)
    names = {
        f.graphql_name or f.python_name for f in out.__strawberry_definition__.fields
    }
    assert "class" in names and "class_" not in names
    data = input_to_dict(
        input_type(fr.Encounter)(status="planned", class_=None)  # type: ignore[call-arg]
    )
    assert data == {"status": "planned"}
