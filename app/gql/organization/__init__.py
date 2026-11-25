"""
The Organization resource on the GraphQL gateway.

One canonical, genuinely FHIR R4-shaped Organization, whichever connector
(internal = our own fhir-server, medplum) is active. There is no per-field
mapping anywhere in this package: the GraphQL types, the Pydantic models
(app.schemas.fhir_resources, shared with fhir-server) and both backends all speak FHIR R4 JSON, and
a connector translator only supplies the URL paths, the search wiring and the
PATCH body shape.

Layout:
- queries.py        `getFhirOrganization` (by id), `searchFhirOrganizations`
                    (the whole searchset: matches, includes, total, paging,
                    warnings) and `getFhirOrganizations` (older, matches-only
                    form of the same search). All three need the
                    `organization:read` permission.
- mutations.py      `createFhirOrganization`, `updateFhirOrganization`,
                    `deleteFhirOrganization` (`organization:create` /
                    `:update` / `:delete`).
- search_params.py  The R4 Organization search parameters as typed GraphQL
                    arguments, plus `fhir_filters()` which maps them back to
                    FHIR parameter names.
- types/            GraphQL object, input and search-result types, generated
                    from app.schemas.fhir_resources (see app.gql.fhir_types).

Request path: resolver -> `require_gql_permission` -> the active connector
(`app.connectors.translator_registry.active_organization_translator()` for
the paths/params, `info.context` container's connector for the HTTP call) ->
fhir-server or Medplum. Search is genuine FHIR R4 search on both backends
(app.connectors.fhir_search); modifiers, chains and anything else not
declared as a typed argument go through the generic `params` argument.

Writes: the create/update input is a FHIR R4 Organization and goes to the
backend as-is. `internal` takes create as a FHIR body and PATCH as a plain
partial-object merge-patch (a supplied top-level element replaces the stored
one); `medplum` needs an RFC 6902 JSON Patch array, built by
app.connectors.medplum.json_patch.

app.gql.location mirrors this package exactly.
"""
