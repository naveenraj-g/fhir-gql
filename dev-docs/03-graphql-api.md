# GraphQL API — Medplum vs fhir-gql Feature Inventory

Scope: Medplum's FHIR-GraphQL engine (`packages/fhir-router/src/graphql/{graphql,input-types,output-types,utils,index}.ts`)
compared against fhir-gql's current Strawberry implementation (`app/gql/{schema,context,permissions,errors}.py`,
`app/gql/resolvers/patient.py`, `app/gql/types/{patient,enums}.py`).

Baseline understanding of fhir-gql today: one hand-written Strawberry schema slice for exactly one resource
(Patient). `PatientQuery`/`PatientMutation` are `@strawberry.type` mixins hand-composed into a root `Query`/`Mutation`
in `app/gql/schema.py`; GraphQL object/input types are hand-derived from existing Pydantic REST schemas via
`strawberry.experimental.pydantic.type/input` (`app/gql/types/patient.py`); every field is a flat CRUD operation
that calls straight into `PatientService` — there is no generic resource resolution, no cross-resource reference
traversal, and no FHIR search-parameter surface in GraphQL (REST-only). Auth is a single `require_gql_permission()`
call per resolver (`app/gql/permissions.py`), not a schema-wide access-control layer.

Medplum's engine, by contrast, builds its *entire* schema (all ~150 FHIR resource types, every query/mutation field,
every reverse-reference edge) programmatically at process startup from FHIR StructureDefinitions
(`getDataType()`/`getSearchParameters()` from `@medplum/core`), and mounts as a single generic `$graphql` FHIR
operation rather than per-resource hand-written fields.

---

### Generic Get-by-ID Field Per Resource Type

- **What it does:** Every FHIR resource type automatically gets a root query field named exactly after the resource
  type (`Patient(id: ID!)`, `Observation(id: ID!)`, `Organization(id: ID!)`, ...) that fetches one resource by id.
  ```graphql
  { Patient(id: "123") { id name { family given } } }
  ```
- **Source files:** `packages/fhir-router/src/graphql/graphql.ts` — `buildRootSchema()` (loop over
  `getResourceTypes()`, registers `fields[resourceType]`), resolver `resolveById()`.
- **How it works:** `buildRootSchema()` iterates every resource type known to the FHIR StructureDefinition registry
  and registers one field per type with a single `id: GraphQLNonNull(GraphQLID)` arg, resolved via `resolveById`,
  which builds a `Reference` string (`${resourceType}/${id}`) and loads it through a per-request `DataLoader`
  (`ctx.dataLoader.load(...)` -> batches with `repo.readReferences(keys)`).
- **Gap vs fhir-gql today:** Fully absent as a generic mechanism. `app/gql/resolvers/patient.py`'s `patient(patient_id: int)`
  field is the hand-written, resource-specific equivalent for exactly one type; there is no code path that would
  produce the same field for a second resource without writing an entirely new resolver module.
- **Port notes for fhir-gql (Strawberry/Python):** This is the highest-leverage generalization to make once a
  second resource (e.g. Organization) is ported: extract a `make_query_type(resource_name, service_getter,
  id_field)` factory that returns a `strawberry.field`-decorated resolver, rather than hand-writing `patient()` /
  `organization()` verbatim each time. Since fhir-gql resources are typed per-Pydantic-model (not one shared FHIR
  `Resource` union like Medplum), a full generic/dynamic version isn't as natural — favor a lighter pattern: a small
  code-gen or mixin-factory helper invoked once per resource module (`app/gql/resolvers/<resource>.py`) that
  builds the `Query`/`Mutation` mixins from a declarative config (resource name, service class, id-field name,
  type/input classes), so adding resource #2 through #15 is data, not 500 lines of copy-pasted boilerplate like
  `patient.py`.
- **Priority:** High — every future resource needs this; the resolver-per-field pattern in `patient.py` will not
  scale to 15 resources without some factoring, even if fhir-gql doesn't go as far as full StructureDefinition-driven
  generation.

---

### StructureDefinition-Driven Dynamic Schema Generation

- **What it does:** The GraphQL schema itself (every object type, every field, every scalar mapping, every input
  type) is not hand-written — it's built at runtime by walking each resource type's `InternalTypeSchema`
  (Medplum's compiled FHIR StructureDefinition representation) and emitting a matching `GraphQLObjectType` /
  `GraphQLInputObjectType`.
- **Source files:**
  - `output-types.ts` — `buildGraphQLOutputType()`, `buildGraphQLOutputFields()`, `buildOutputPropertyField()`,
    `getOutputPropertyType()`.
  - `input-types.ts` — `buildGraphQLInputType()`, `buildGraphQLInputFields()`, `buildInputPropertyField()`.
  - `utils.ts` — `typeCache` (static map of FHIR primitive types -> GraphQL scalars: `string`->`GraphQLString`,
    `decimal`/`integer`->`GraphQLFloat`, `id`->`GraphQLID`, `boolean`->`GraphQLBoolean`, everything else defaults to
    `GraphQLString`).
- **How it works:** For each resource type, `getDataType(resourceType)` (from `@medplum/core`) returns a schema
  object (`elements: Record<path, InternalSchemaElement>`) compiled from the resource's StructureDefinition +
  extensions. `buildOutputPropertyField` walks every element: resolves `Element`/`BackboneElement` down to their
  concrete inner type, maps FHIR type codes to GraphQL types via `getGraphQLOutputType` (recursive — nested
  BackboneElements like `Patient.contact` become their own `GraphQLObjectType`s), wraps in `GraphQLList` when
  `max > 1`, wraps in `GraphQLNonNull` when `min > 0`. Input types mirror this in `input-types.ts` but *skip* fields
  typed `Resource` entirely (comment: "GraphQL does not support union types on input... we do not support
  Resource.contained on GraphQL input"). Types are memoized in a shared cache (`outputTypeCache`/`inputTypeCache`,
  seeded from `typeCache`) keyed by type name, with the output type map pre-populated with placeholder types up
  front in `buildRootSchema()` specifically to break circular references (e.g. `Patient.generalPractitioner` ->
  `Practitioner` -> ... -> `Patient`).
- **Gap vs fhir-gql today:** Lacks entirely, and this is architecturally the sharpest divergence. fhir-gql has no
  StructureDefinition ingestion at all — `app/gql/types/patient.py` types are hand-declared, one
  `@strawberry.experimental.pydantic.type` class per Pydantic response/input schema, with an explicit
  `all_fields=True` per class and manual declaration-ordering comments ("leaf sub-resource types must be declared
  before anything that nests them") because Python class definitions can't forward-reference the way Medplum's
  lazy `fields: () => ...` thunks can.
- **Port notes for fhir-gql (Strawberry/Python):** Full runtime dynamic generation is a large, likely
  disproportionate investment given fhir-gql's architecture (it already has hand-maintained Pydantic
  Create/Patch/Response schemas per resource in `app/schemas/<resource>/{input,response}.py` — those *are*
  fhir-gql's StructureDefinition equivalent). Two realistic paths, in order of increasing effort:
  1. **Keep hand-authored types but templatize.** Since every resource already follows the exact same shape
     (`<X>Response`->`<X>Type`, `<X>CreateSchema`->`<X>CreateInput`, per the naming convention documented at the
     top of `app/gql/types/patient.py`), write a small generator script (not runtime, a one-time codegen step) that
     emits `app/gql/types/<resource>.py` boilerplate from the existing Pydantic models via introspection
     (`model.model_fields`), which a human then reviews/edits — mirrors what Medplum does at runtime but done at
     dev time, fitting Strawberry's static-class idiom better.
  2. **True runtime generation**, if desired later: Strawberry supports building types dynamically via
     `strawberry.type(type(name, (), {...}))` or the lower-level `strawberry.experimental.pydantic.type` called
     programmatically in a loop over `app/schemas/*/response.py` modules; circular refs would need the same
     "placeholder-first, fill-in-later" two-pass trick Medplum uses (`buildRootSchema`'s first loop), which is
     more awkward in Strawberry than in `graphql-js` since Strawberry resolves types eagerly from Python type
     hints rather than lazy thunks — would likely require `strawberry.lazy()` annotations throughout.
  Recommendation: start with (1); only invest in (2) if resource count and schema churn make hand-maintenance
  genuinely painful.
- **Priority:** Medium — valuable for velocity as more resources are added, but not blocking; fhir-gql's existing
  per-resource Pydantic-schema pattern is a reasonable substitute for now, and Patient (9 sub-resources) already
  proved the hand-written pattern works at meaningful complexity.

---

### Reverse-Reference Lookup Fields (`*List` / `*Connection` with `_reference`)

- **What it does:** For every resource type `R`, and every *other* resource type `C` that has a search parameter
  targeting `R`, a field `C + 'List'` (and `C + 'Connection'`) is added onto `R`'s GraphQL object type, letting a
  client fetch "all resources of type C that reference this R" as a nested field — e.g. fetching a Patient and, in
  the same query, all Conditions that reference that patient:
  ```graphql
  {
    Patient(id: "123") {
      name { family }
      ConditionList(_reference: patient) { code { text } }
    }
  }
  ```
- **Source files:** `output-types.ts` — `buildReverseLookupFields()` (called from `buildGraphQLOutputFields()`
  alongside the forward-property fields); `utils.ts` — `parseSearchArgsWithReference()` (pulls `_reference` out of
  args, builds a `Filter` matching `code=_reference, operator=EQUALS, value=<this resource's reference string>`,
  merges it into the child search).
- **How it works:** At schema-build time, for each `(resourceType, childResourceType)` pair, Medplum scans
  `getSearchParameters(childResourceType)` for any search param whose `target` array includes `resourceType`
  (e.g. `Condition.patient` targets `Patient`); if any exist, it builds a `GraphQLEnumType` named
  `<R>_<C>_reference` enumerating the valid reverse-reference search-param codes, adds it as a required `_reference`
  arg alongside the normal search args (via `buildSearchArgs(childResourceType)`), and registers `resolveBySearch`
  /`resolveByConnectionApi` as the resolver — same resolvers used for top-level `*List`/`*Connection` fields, just
  parameterized with `source` (the parent resource) so `parseSearchArgsWithReference` can inject the reference
  filter.
- **Gap vs fhir-gql today:** Absent entirely. Nothing in `app/gql/resolvers/patient.py` performs any cross-resource
  traversal — `PatientType` embeds only Patient's own sub-resource arrays (name, identifier, etc., which are
  first-class Patient child records, not separate FHIR resources referencing Patient). Fetching e.g. "all
  Encounters for a Patient" today requires a separate REST/GraphQL round trip once Encounter exists as its own
  resource; there is no `_reference`-style embedded traversal concept anywhere in `app/gql/`.
- **Port notes for fhir-gql (Strawberry/Python):** This is the single most valuable capability to design in
  deliberately once 2+ interlinked resources exist (e.g. Patient <-> Organization, or Patient <-> a future
  Encounter/Condition). Approach: for each resource pair with a real FK-style relationship, add a `strawberry.field`
  with its own resolver on the parent's `Type` class — e.g. on `PatientType`, an `encounters` field whose resolver
  calls `EncounterService.list(filters={"patient_id": root.id}, ...)`. Strawberry resolves fields lazily per-object
  by default (each field on a type is its own resolver function taking `self`/`root`), so this is natural to add
  incrementally per resource pair rather than needing Medplum's blanket "scan every resource pair" step — but that
  also means each reverse-edge must be added by hand; there's no automatic discovery unless fhir-gql later encodes
  its own FK/reference metadata (e.g. from `app/schemas/*/response.py` reference fields) and generates these
  fields programmatically the way Medplum does. Use `strawberry.field(resolver=...)` and thread `info` through so
  the resolver can still call `require_gql_permission`/DataLoader.
- **Priority:** High — this is the core "graph" value proposition of GraphQL for FHIR and the most-requested-style
  feature once resources beyond Patient exist; sequence it right after the second/third resource lands so the
  pattern is established before N further resources copy it.

---

### FHIR Search-as-a-Field (`*List`, Search Parameter Arguments, `_count`/`_offset`/`_sort`/`_filter`/`_cursor`)

- **What it does:** Every resource type gets a top-level list field (`PatientList`) whose arguments are exactly its
  FHIR search parameters (rendered as GraphQL string args, dashes converted to underscores), plus standard FHIR
  paging/sort/filter controls.
  ```graphql
  { PatientList(name: "Smith", birthdate: "1990-01-01", _count: 20, _sort: "-_lastUpdated") { id name { family } } }
  ```
- **Source files:** `utils.ts` — `buildSearchArgs()` (adds `_count`, `_offset`, `_sort`, `_id`, `_lastUpdated`,
  `_filter`, `_cursor`, plus one arg per `getSearchParameters(resourceType)` entry), `resolveBySearch()`,
  `graphQLFieldToFhirParam()`/`fhirParamToGraphQLField()` (dash<->underscore translation since GraphQL identifiers
  disallow `-`). `graphql.ts` — field registration `fields[resourceType + 'List']`.
- **How it works:** `buildSearchArgs` is the single source of truth for a resource's queryable surface, reused
  identically for top-level list fields *and* reverse-lookup fields (see above) *and* the Connection API (below) —
  same args map, three different field names/resolvers. `resolveBySearch` translates GraphQL args back into a FHIR
  `SearchRequest` via `parseSearchRequest()` (the same search-parsing code path REST search uses), applies a
  server-side max page size (`applyMaxCount`), and — notably — supports **batched reverse-lookup searches**: when
  resolving as a *reverse* field with a configured `graphqlBatchedSearchSize`, it builds a per-`SearchRequest`-shape
  `DataLoader` (keyed by a stable JSON-sorted stringify of the request) so that N sibling reverse-lookup fields in
  one query (e.g. 50 Patients each requesting `ConditionList`) get coalesced into one `repo.searchByReference()`
  call instead of N separate searches — this is the N+1 avoidance mechanism specifically for the reverse-edge case.
- **Gap vs fhir-gql today:** Partially present in spirit, absent in form. fhir-gql's `patients()` query field
  (`app/gql/resolvers/patient.py`) *does* expose filtering (`family_name`, `given_name`, `gender`, `active`,
  `user_id`, `org_id`) and pagination (`limit`/`offset`, default 50 max 200) as explicit typed GraphQL arguments —
  conceptually the same idea as `buildSearchArgs`. But it is hand-declared per-field with a bespoke filter set
  (`ListPatientsSchema`), not derived from a canonical FHIR search-parameter registry, has no `_sort`/`_filter`/
  `_cursor`, and does not (and structurally cannot yet, since fhir-gql has no second resource with a reference to
  Patient) support the reverse-lookup-with-batching case.
- **Port notes for fhir-gql (Strawberry/Python):** fhir-gql already returns FHIR-shaped resources from a
  downstream fhir-server (REST layer supports `accept` for Bundle format per the docstring in `patient.py`), so
  building a `getSearchParameters()`-equivalent isn't from scratch — likely there's already a canonical search-param
  set per resource used by REST list endpoints (`ListPatientsSchema` and its siblings). The port is mechanical:
  factor a `build_search_args(resource)`-style helper that both REST's Pydantic filter schema and a GraphQL
  resolver's keyword args can share, so a new resource's `<resource>s()` query field doesn't hand-roll its filter
  list. `_sort`/`_cursor` should only be added if/when the underlying fhir-server actually supports them — don't
  build UI for capability the backend lacks.
- **Priority:** Medium — the *filtering* half is already adequately covered per-resource; the main missing pieces
  (`_sort`, `_cursor`, a shared search-arg builder, and pairing with reverse-lookup batching) are worth doing but
  are refinements, not blockers, unless/until reverse-reference fields (High priority above) are built, at which
  point the DataLoader-batching part of this feature becomes load-bearing.

---

### FHIR GraphQL Connection API (Cursor Pagination + Total Count)

- **What it does:** Alongside the plain `*List` field, every resource also gets a `*Connection` field returning a
  richer envelope with `count`, `offset`, `pageSize`, `first`/`previous`/`next`/`last` cursor links, and `edges`
  (each with `mode`, `score`, and the nested `resource`) — this is the FHIR spec's own Connection pattern (distinct
  from, though similar in spirit to, the Relay cursor-connection convention).
  ```graphql
  { PatientConnection(name: "Smith", _count: 10) { count edges { score resource { id name { family } } } next } }
  ```
- **Source files:** `graphql.ts` — `buildConnectionType()`, `getConnectionType()` (memoized per resource type),
  `resolveByConnectionApi()`, `getNextCursor()`. Registered both at top level (`fields[resourceType + 'Connection']`)
  and per reverse-lookup edge (`output-types.ts` `buildReverseLookupFields`).
- **How it works:** `resolveByConnectionApi` inspects which sub-fields were actually requested
  (`isFieldRequested(info, 'count')` -> sets `searchRequest.total = 'accurate'` only if needed, since counting is
  expensive; `isFieldRequested(info, 'edges')` -> sets `count = 0` to skip fetching entries if the caller only
  wants the count) — a small but deliberate cost-avoidance optimization driven by the GraphQL selection set itself.
  Cursor is extracted from the underlying FHIR `Bundle.link[relation=next].url`'s `_cursor` query param.
- **Gap vs fhir-gql today:** Absent. `PaginatedPatientType` (`app/gql/types/patient.py`) is a `data`/`total`/
  `limit`/`offset` envelope — offset-based, no cursor, no per-entry `score`/`mode`, and critically no
  selection-set-aware cost avoidance (fhir-gql's `patients()` resolver always does the same work regardless of
  which sub-fields the client asked for).
- **Port notes for fhir-gql (Strawberry/Python):** Strawberry exposes the equivalent of `isFieldRequested` via
  `info.selected_fields` (walk `info.selected_fields[0].selections` for a matching field name) — same technique
  is directly portable. Whether to adopt FHIR's Connection shape (score/mode/edges) vs. sticking with the existing
  `Paginated<X>Type` pattern (which is simpler and already consistent with REST's paginated-list response shape)
  is a product decision, not just a technical one — recommend keeping `Paginated<X>Type` for consistency with REST,
  but stealing the "only count when `total` is actually selected" optimization regardless.
- **Priority:** Low — fhir-gql's existing paginated-envelope pattern is functionally adequate; the main win here
  (avoiding an unnecessary count query) is a nice-to-have perf refinement, not a capability gap.

---

### `ResourceList` Union Type for Polymorphic Reference Resolution

- **What it does:** A `Reference.resource` field resolves the referenced object as whatever concrete resource type
  it actually is, typed in GraphQL as a union of all resource types (`ResourceList`), letting clients follow any
  reference generically and select type-specific fields via inline fragments:
  ```graphql
  { Observation(id: "1") { subject { resource { ... on Patient { name { family } } ... on Group { name } } } } }
  ```
- **Source files:** `output-types.ts` — `buildGraphQLOutputType()`'s `resourceType === 'ResourceList'` branch
  (builds a `GraphQLUnionType` over every resource type via `getResourceTypes().map(getGraphQLOutputType)`),
  `resolveTypeByReference()` (union's `resolveType`), `resolveByReference()` (the field resolver, uses the shared
  request-scoped `ctx.dataLoader`).
- **How it works:** Any FHIR element typed `Reference` gets a `resource` sub-field of GraphQL type `ResourceList`
  (a union). `graphql-js` requires unions to declare a `resolveType` function so it knows, given the resolved JS
  object, which member type it actually is — `resolveTypeByReference` reads `.resourceType` off the loaded resource
  and maps it back to the matching `GraphQLObjectType.name`. The actual fetch goes through the DataLoader keyed by
  reference string, batching N sibling reference fields across one query into one `repo.readReferences(keys)` call
  — this is Medplum's primary N+1 defense for *forward* reference-following (as opposed to the reverse-lookup
  DataLoader described earlier).
- **Gap vs fhir-gql today:** Absent, and structurally can't exist yet — fhir-gql has only one GraphQL object type
  (`PatientType`), so there is nothing to union over. Even Patient's own reference-shaped fields
  (`generalPractitioner`, which can point at Organization/Practitioner/PractitionerRole per
  `GeneralPractitionerReferenceType`) are exposed today as a flat `PatientGeneralPractitionerType` record carrying
  a `referenceType` string field and presumably an id/reference string — not as a resolvable, typed union that
  fetches the actual target resource.
- **Port notes for fhir-gql (Strawberry/Python):** Strawberry supports unions via
  `SomeUnion = strawberry.union("SomeUnion", (TypeA, TypeB, ...))` with resolvers returning a concrete instance
  (Strawberry infers the member type from the Python object's class, no separate `resolve_type` needed the way
  raw `graphql-js` requires — simpler than Medplum's approach here). This only becomes buildable once >= 2
  resource types exist. When it does: add a `strawberry.field` resolver on `PatientGeneralPractitionerType` (and
  any other reference-shaped field) that dispatches to the correct service by `referenceType` and returns one of a
  growing union; batch these lookups with a `strawberry.dataloader.DataLoader` keyed by `(resource_type, id)` to
  avoid N+1, mirroring Medplum's `ctx.dataLoader`.
- **Priority:** Low for now (blocked on resource count), rising to Medium/High once 3+ referenceable resources
  exist — track it as a prerequisite-gated item rather than dropping it, since `generalPractitioner` is exactly the
  kind of polymorphic reference this feature is for.

---

### DataLoader-Based N+1 Batching (Forward References *and* Reverse-Lookup Searches)

- **What it does:** Two independent DataLoader instances per GraphQL request prevent N+1 query storms: one batches
  "fetch resource by reference" calls (used by `Reference.resource` and the top-level get-by-id fields), the other
  batches reverse-lookup searches that share the same underlying search shape.
- **Source files:** `graphql.ts` — `graphqlHandler()` (constructs `new DataLoader<Reference, Resource, string>(...)`
  once per request, stored on `GraphQLContext.dataLoader`); `utils.ts` — `buildResolveBySearchDataLoader()` (lazily
  created per unique search shape, cached in `ctx.searchDataLoaders`, keyed by a sorted-JSON hash of the
  `SearchRequest`).
- **How it works:** `dataloader` (npm package) coalesces same-tick `.load()` calls into a single batched
  `repo.readReferences(keys)` / `repo.searchByReference(...)` call, keyed by `cacheKeyFn`. Both loaders are
  request-scoped (fresh `GraphQLContext` per HTTP request in `graphqlHandler`), so caching never leaks across
  requests/users. `graphqlBatchedSearchSize` (a project-level setting, `0` by default = disabled) controls the
  reverse-lookup loader's `maxBatchSize`; forward-reference batching has no such gate and is always on.
- **Gap vs fhir-gql today:** Absent entirely — `app/gql/resolvers/patient.py` calls `PatientService` directly per
  field with no batching layer, but this is currently harmless because there is only one resource and no
  cross-resource traversal to N+1 on. This gap only becomes real once reverse-reference/union features (above) are
  built without a DataLoader underneath them.
- **Port notes for fhir-gql (Strawberry/Python):** Strawberry ships `strawberry.dataloader.DataLoader` (same
  batch/cache-per-tick semantics as the JS `dataloader` package Medplum uses) — construct one per resource-fetch
  type inside `get_context()` (`app/gql/context.py`), store it on `GraphQLContext` (e.g.
  `self.patient_loader = DataLoader(load_fn=batch_load_patients)`), and have resolvers call
  `await info.context.patient_loader.load(patient_id)` instead of calling the service directly whenever a field
  might be requested many times in one query (i.e., as soon as any reverse-reference or reference-union field is
  added). Build this loader layer *at the same time* as the first reverse-reference field, not before — no reason
  to add it while only one flat resource exists.
- **Priority:** Medium — not urgent today (no N+1 risk yet), but should be treated as a hard prerequisite the
  moment reverse-reference fields or reference-following unions ship, so flag it as a co-requirement of those two
  High-priority items above rather than a separately schedulable item.

---

### Generic Create / Update / Patch / Delete Mutations Per Resource Type

- **What it does:** Every resource type automatically gets four mutation fields: `<R>Create(res: <R>CreateInput!)`,
  `<R>Update(id: ID!, res: <R>UpdateInput!)`, `<R>Patch(id: ID!, patch: [PatchOperationInput!]!)` (RFC 6902 JSON
  Patch), `<R>Delete(id: ID!)`.
  ```graphql
  mutation { PatientCreate(res: { resourceType: "Patient", name: [{ family: "Smith" }] }) { id } }
  mutation { PatientPatch(id: "123", patch: [{ op: "replace", path: "/active", value: "false" }]) { id active } }
  ```
- **Source files:** `graphql.ts` — `buildRootSchema()` (mutation field registration loop), `buildCreateArgs()`,
  `buildUpdateArgs()`, `buildPatchArgs()`, `resolveByCreate()`, `resolveByUpdate()`, `resolveByPatch()`,
  `resolveByDelete()`; `input-types.ts` — `getPatchOperationInputType()` (the shared `PatchOperationInput` type:
  `op`/`path`/`value:GraphQLString` — note `value` is a plain string because "GraphQL input types are limited",
  i.e. no true `any` scalar, so patch values are string-encoded).
- **How it works:** Create/Update validate that the input's `resourceType` field (and, for update, `id`) matches
  the field name/args before delegating straight to `ctx.repo.createResource`/`updateResource`/`patchResource`/
  `deleteResource` — i.e. these mutations are thin pass-throughs to the exact same repository layer REST uses, with
  no resource-specific business logic in the GraphQL layer itself (all such logic lives in the shared `repo`).
  Inputs are `deepClone`d before use specifically because GraphQL parses argument objects with a null prototype
  (`Object.create(null)`), which breaks FHIRPath evaluation elsewhere in the stack that expects real `Object`
  prototypes.
- **Gap vs fhir-gql today:** fhir-gql has this in substantially richer, resource-tailored form for Patient, not
  generic form. `PatientMutation` (`app/gql/resolvers/patient.py`) exposes 27 mutations: not just flat
  create/update/delete but dedicated add/patch/delete triples for each of Patient's 9 sub-resources
  (name/identifier/telecom/address/photo/contact/communication/generalPractitioner/link), plus `createPatientFull`/
  `updatePatientFull` atomic multi-sub-resource transactions with documented array replace-vs-merge semantics, and
  a real typed JSON Patch equivalent is not present — patching happens through dedicated scalar-field
  `PatientPatchInput` mutations, not RFC 6902 patch documents. In short: fhir-gql's design is *more* expressive per
  resource (bespoke sub-resource endpoints) where Medplum's is *more* uniform across resources (one generic shape
  reused 150 times) — this is a real design fork, not a strict subset/superset relationship.
- **Port notes for fhir-gql (Strawberry/Python):** No change needed to the philosophy — `PatientMutation`'s
  bespoke-per-sub-resource pattern is intentional and arguably better UX than Medplum's generic
  create/update/patch for resources with rich nested structure like Patient. What's missing and worth borrowing:
  (1) a generic RFC 6902-style `Patch` mutation as a *fallback* escape hatch for scalar-field edits not worth a
  dedicated mutation, using a `PatchOperationInput` type identical in shape to Medplum's; (2) the
  resourceType/id-consistency validation pattern (`resourceArgs.resourceType !== resourceType` check) as a
  reusable guard if/when fhir-gql adds any generic (non-per-field) mutation path.
- **Priority:** Low — fhir-gql's existing bespoke-mutation pattern for Patient already covers this need well and
  should be replicated per-resource as before; a generic JSON-Patch fallback is a nice-to-have, not a gap that
  blocks anything.

---

### Query Cost Limiting & Max-Depth Guarding

- **What it does:** Two custom GraphQL validation rules run before every query executes: one estimates a numeric
  "cost" for the query (weighting search fields and linked-resource traversal higher, exponentially via branching
  factor) and warns if it exceeds a threshold (`10,000` default); another computes the query's field-nesting depth
  and warns past a threshold (`12` default). Both are currently **warn-only** (the actual `reportError`/rejection
  calls are commented out in the source — see `graphql.ts` lines ~540 and ~637) — i.e., shipped as logging/observability,
  not enforcement, in this version of Medplum.
- **Source files:** `graphql.ts` — `MaxDepthRule`/`MaxDepthVisitor`, `QueryCostRule`/`QueryCostVisitor`,
  `isSearchField()` (fields ending in `List` cost more), `isLinkedResource()` (fields named `resource`, i.e. the
  `ResourceList` union resolution, cost more).
- **How it works:** Registered as additional `validate()` rules alongside `specifiedRules` (GraphQL's built-in
  validation) in `graphqlHandler`. `QueryCostVisitor.calculateCost` recursively costs each field: base cost 8 +
  branching-factor-multiplied child cost for search (`*List`) fields (branching factor = the query's own `_count`
  arg if given, else 20 — i.e. it assumes worst-case fan-out), base cost 1 + branching factor 2 for `resource`
  (reference-following) fields, with fragment costs cached per fragment name to avoid recomputation.
- **Gap vs fhir-gql today:** Absent. fhir-gql has no query-cost or depth analysis at the GraphQL layer at all;
  `limit`/`offset` bounds (max 200 per the `patients()` docstring) are the only cost control, enforced inside the
  resolver rather than at validation time.
- **Port notes for fhir-gql (Strawberry/Python):** Strawberry supports custom validation via
  `strawberry.extensions` (e.g. `AddValidationRules`, or a custom `SchemaExtension` with `on_validate` hooks) or
  the simpler `strawberry.extensions.QueryDepthLimiter`-style community extensions. Given fhir-gql's flat,
  hand-declared field structure today, unbounded-depth risk is low (no recursive reference-following exists yet)
  — but this becomes directly relevant the moment reverse-reference/union features (both High priority above) ship,
  since those introduce real cyclic traversal potential (Patient -> Condition -> Patient -> ...). Recommend
  building this alongside those features, using Strawberry's `MaxTokensLimiter`/custom depth-limiting extension
  rather than porting Medplum's bespoke visitor, and — unlike Medplum's current warn-only posture — actually
  enforcing the limit (reject via `GraphQLError`) since fhir-gql is starting fresh with no existing client queries
  to avoid breaking.
- **Priority:** Medium — not needed while the schema is flat/acyclic, but should land in the same iteration as
  reverse-reference traversal, before that feature reaches production traffic.

---

### Introspection Gating

- **What it does:** GraphQL schema introspection (the `__schema` meta-query that powers GraphiQL's Docs panel and
  any client-side codegen) can be disabled per-deployment; if disabled and a client sends an introspection query,
  the server returns `403 Forbidden` instead of the schema.
- **Source files:** `graphql.ts` — `isIntrospectionQuery()` (string-matches `query IntrospectionQuery` or
  `__schema`), the `introspection && !router.options?.introspectionEnabled` check in `graphqlHandler`. Wired from
  `packages/server/src/fhir/routes.ts` (`introspectionEnabled: getConfig().introspectionEnabled`) — a
  deployment-level config flag, not per-request/per-user.
- **How it works:** Introspection results are also memoized in a process-wide `LRUCache` (`introspectionResults`)
  keyed by the raw query string, since the standard IDE introspection query is large, identical across clients, and
  expensive to compute against a ~150-type dynamically-built schema — caching only makes sense *because* the schema
  is static after `buildRootSchema()` runs once at startup.
- **Gap vs fhir-gql today:** Conceptually present but via a different, arguably better-fitted mechanism. fhir-gql
  gates the entire GraphiQL IDE (which is what exposes introspection interactively) by environment: `graphql_ide`
  is `None` in production (`app/gql/schema.py`). This blocks the IDE shell but — worth double-checking — does
  **not** appear to block a raw `POST /graphql` request containing `{"query": "{ __schema { types { name } } }" }`
  from a scripted client in production; Strawberry's `GraphQLRouter` has no built-in introspection-query rejection
  independent of the IDE toggle.
- **Port notes for fhir-gql (Strawberry/Python):** Strawberry ships exactly this as a built-in extension:
  `strawberry.extensions.disable_validation.` — more precisely, `strawberry.extensions.DisableIntrospection` (or
  older `strawberry.schema_extensions` for the same purpose), added via the `schema = strawberry.Schema(...,
  extensions=[DisableIntrospection()])` — this can be applied conditionally based on `settings.ENVIRONMENT`
  exactly the way `graphql_ide` already is, in `app/gql/schema.py`. Given the schema is small today, this is low
  urgency, but worth closing since it's a one-line fix and closes a real (if currently low-value) reconnaissance
  vector.
- **Priority:** Low today (small schema, low information leakage), but cheap to fix — worth bundling into any
  otherwise-unrelated `app/gql/schema.py` change rather than scheduling as standalone work.

---

### Reader/Writer Repository Mode Selection (Read Replica Routing)

- **What it does:** Pure-query GraphQL requests (no mutations present) are routed to a read-replica-capable
  repository mode; requests containing mutations use the primary/writer connection.
- **Source files:** `graphql.ts` — `includesMutations()` (string search for the literal `mutation` keyword in the
  raw query text), `repo.setMode(RepositoryMode.READER)` call in `graphqlHandler`.
- **How it works:** A crude but cheap heuristic (substring match, not AST-based) run before parsing, gating whether
  the shared `FhirRepository` instance for this request is told it may prefer a read replica.
- **Gap vs fhir-gql today:** Not applicable in the same form — fhir-gql is a middleware layer in front of a
  separate downstream fhir-server (per the project description), so there is no local repository/DB connection
  whose reader/writer mode fhir-gql itself controls; this concern, if it exists at all, lives inside the downstream
  fhir-server, not in `app/gql/`.
- **Port notes for fhir-gql (Strawberry/Python):** Not directly portable given the architecture; note only for
  completeness. If the downstream fhir-server exposes a read-vs-write endpoint distinction reachable via headers
  or routing, `get_context()` (`app/gql/context.py`) would be the natural place to inspect the parsed operation
  type and set a corresponding hint — but there's no evidence this is needed today.
- **Priority:** Low / not applicable — architectural mismatch, not a genuine gap.

---

## Summary Table

| Feature | Priority | Gap status |
|---|---|---|
| Generic get-by-ID field per resource type | High | Absent as a generic mechanism; hand-written per-resource equivalent exists for Patient only |
| StructureDefinition-driven dynamic schema generation | Medium | Absent entirely; hand-declared types via `strawberry.experimental.pydantic` substitute adequately for now |
| Reverse-reference lookup fields (`*List`/`*Connection` + `_reference`) | High | Absent entirely; no cross-resource traversal concept exists in fhir-gql's GraphQL layer |
| FHIR search-as-a-field (search params as GraphQL args, incl. batching) | Medium | Partially present (per-resource hand-rolled filters/pagination); missing `_sort`/`_cursor`, shared search-arg builder, and reverse-lookup batching |
| Connection API (cursor pagination, count, edges) | Low | Absent; existing offset-based `Paginated<X>Type` is an adequate substitute |
| `ResourceList` union for polymorphic reference resolution | Low (rising to High once 3+ resources exist) | Absent; structurally blocked on having more than one GraphQL object type |
| DataLoader-based N+1 batching | Medium | Absent; currently harmless (single flat resource), becomes a hard prerequisite once reverse-reference/union features ship |
| Generic Create/Update/Patch/Delete per resource | Low | Design fork, not a gap — fhir-gql's bespoke per-sub-resource mutations are richer for Patient; missing only a generic JSON-Patch fallback |
| Query cost limiting & max-depth guarding | Medium | Absent; low risk today (flat schema), needed once cyclic traversal (reverse-reference) ships |
| Introspection gating | Low | Partially present via GraphiQL-IDE env gating; raw introspection queries may not be blocked in production |
| Reader/writer repo mode routing | Low / N/A | Architectural mismatch — fhir-gql has no local repository layer to route |

## Recommended Next Steps

Sequence around the fact that fhir-gql's real gap isn't missing GraphQL mechanics in general — CRUD, RBAC, error
translation, and pagination are already solid, proven patterns in `app/gql/`) — it's the complete absence of any
*cross-resource graph traversal*, which is the entire reason to prefer GraphQL over REST in the first place. Concretely:

1. **Port the second and third resources using the existing hand-written pattern** (`app/gql/types/<resource>.py`
   + `app/gql/resolvers/<resource>.py` + mixin into `Query`/`Mutation` in `app/gql/schema.py`), exactly as the
   module docstrings in `schema.py` already describe. Resist generalizing prematurely — two data points aren't
   enough to design a good abstraction.
2. **The moment two resources have a real reference relationship** (e.g. Patient.generalPractitioner ->
   Organization/Practitioner, or a future Encounter.patient), build the first **reverse-reference field** by hand
   on the relevant `Type` class, together with a **`strawberry.dataloader.DataLoader`** underneath it from the
   start — do not defer batching, since retrofitting it after N+1 patterns are already baked into resolver code is
   more expensive than building it in from the first traversal field.
3. **Factor the resolver/type boilerplate into a shared helper** once resource #3 or #4 makes the copy-paste cost
   in `patient.py`-style modules (500+ lines for one resource) obviously unsustainable — a declarative
   config-driven mixin factory, not full StructureDefinition-driven runtime generation, is the right level of
   investment given fhir-gql's Pydantic-schema-first architecture.
4. **Add max-depth/cost guarding and close the introspection gap** in the same iteration as step 2, once cyclic
   traversal is actually possible — both are cheap and this is exactly the point at which an unbounded query
   becomes a real risk rather than a theoretical one.
5. **Defer** the Connection API, generic JSON-Patch mutations, and full dynamic schema generation indefinitely
   unless a concrete need emerges (e.g. an external client wanting Relay-style cursor pagination, or resource count
   growing past ~10-15 making hand-maintenance genuinely painful) — these are the lowest-leverage items relative to
   their cost given fhir-gql's current trajectory.
