"""
EXPERIMENTAL — a second, standalone GraphQL vertical proving out "one
universal, FHIR R4-shaped GraphQL schema, with per-connector translation"
as an alternative to this project's existing per-connector GQL architecture
(app.connectors.internal.gql, mixed into the main schema at
app/gql/schema.py via app.connectors.gql_registry).

Where this differs from that existing architecture: today, each connector
(internal, medplum, ...) gets its own GraphQL Query/Mutation mixin, shaped
however is most natural for that connector's own backend (internal's
Organization mirrors fhir-server's plain/flattened convention, not genuine
FHIR). Here, there is exactly ONE GraphQL schema — genuinely FHIR R4-shaped
— and whichever connector is active translates between that one canonical
shape and its own wire format. See
dev-docs/18-universal-fhir-graphql-experiment.md for the full reasoning,
including the asymmetry that originally shaped this experiment: reads are
near-free to unify (both of today's connectors already speak real FHIR
JSON for reads), while writes against `internal` are NOT — fhir-server's
own POST/PATCH only ever accept its own flattened plain-JSON shape, never
genuine FHIR JSON. Full CRUD (create/read/update/delete) is now covered;
`app.connectors.universal.translators`'s `InternalOrganizationTranslator`
does the real field-level flattening that asymmetry requires on write.

This package is purely additive: it does not import from, get imported by,
or modify anything in app.connectors.internal, app.connectors.medplum,
app.connectors.registry, app.connectors.gql_registry, or app/gql/schema.py.
It is mounted at its own path (see app/main.py) specifically so it can be
evaluated side-by-side with the existing architecture without touching it.

Modules:
    schemas/     — one canonical FHIR R4 Pydantic shape module per resource
                    (organization.py so far), for both read (reused from
                    app.connectors.internal, not redefined) and write
                    (FhirOrganizationInput, new here — see that module's
                    docstring). schemas/__init__.py re-exports everything so
                    callers import from app.connectors.universal.schemas
                    without caring which resource module a name lives in.
    translators/ — one per-connector translation module per resource
                    (organization.py so far): path/query-param conventions
                    and Accept headers for reads; real field-level remapping
                    for writes against a non-FHIR-native connector
                    (internal). Same re-export convention as schemas/.
    gql/         — Strawberry types (types.py), Query resolvers
                    (queries.py), and Mutation resolvers (mutations.py).
    schema.py    — the standalone strawberry.Schema + GraphQLRouter.
"""
