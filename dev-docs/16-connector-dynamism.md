# Connector Dynamism: What Can Actually Be Config-Driven, and What Can't

## The question

Today, adding a connector means writing a Python class by hand
(`app/connectors/fhir_server.py`'s `FhirServerConnector`) that satisfies the
`Connector` Protocol, registering it in `app/connectors/registry.py`, and
flipping `connectors.active` in `configs/config.yaml`. That's config-driven
*selection*, but each connector's own internals are still hand-written.

The question raised: can connectors themselves be generated/populated from
something like an OpenAPI spec instead of hand-written — the way a REST
client can be codegenned from a backend's OpenAPI document — and if so,
how does that map onto a GraphQL gateway, where queries/mutations are
hand-written, not generated from a spec? Or is hand-written ("static")
simply correct, with *our own* OpenAPI spec generated *from* that static
code (the normal FastAPI direction), rather than the other way round?

## The answer in one sentence

**These are two different layers, and only one of them is a legitimate
candidate for spec-driven dynamism.** The GraphQL schema must stay static
and backend-agnostic; the connector's *internal* REST-calling logic can
legitimately become more dynamic — but the right lever for that isn't
"parse an arbitrary OpenAPI spec," it's "exploit the fact that FHIR is
already a standard."

## Layer 1: the GraphQL schema — must stay static, by design

This was the whole point of introducing the connector abstraction earlier:
one GraphQL schema, shaped like the FHIR R4 resource model, that every
connector is adapted *to* — not derived *from*. That decision doesn't
change here, for three concrete reasons:

1. **Clients code against the schema, not the backend.** If the schema's
   shape depended on which connector happened to be active, every GraphQL
   client (web app, mobile app, another service) would need to handle N
   possible schemas instead of one. That defeats the reason a GraphQL
   gateway exists in front of multiple backends at all.
2. **A GraphQL resolver does more than echo wire shape.** `require_gql_permission`,
   actor binding (`created_by`/`updated_by` from the verified JWT), cross-resource
   validation — none of that is derivable from any spec, OpenAPI or otherwise.
   A spec describes shape; it says nothing about your authorization rules.
3. **Strawberry resolves queries/mutations to Python functions at import
   time**, via `@strawberry.field`/`@strawberry.mutation` decorators on real
   methods. There's no supported "load this resolver from a spec parsed at
   runtime" mechanism without essentially writing a second meta-framework
   on top of Strawberry — a lot of machinery to maintain for a problem that
   doesn't need solving, since REST clients are the ones that genuinely
   benefit from spec-driven codegen, not GraphQL ones.

So: no, GraphQL queries/mutations should never be generated from a
connector's OpenAPI spec. That part of the current, hand-written design is
correct and shouldn't change.

## Layer 2: the connector's internals — this is where dynamism actually fits

A resolver never talks to a connector's HTTP details directly — it goes
through the `Connector` Protocol's four generic verbs (`post`/`get`/`patch`/
`delete`). From the resolver's point of view, it is *already* irrelevant
whether a connector's internals are:

- hardcoded paths (what `FhirServerConnector` does today), or
- generated from a spec at build time, or
- resolved from a spec at runtime.

All three look identical from above. This is why the question "how do we
map OpenAPI-populated things to GQL queries/mutations" has a clean answer:
**you don't map them directly — the connector sits between them, and the
Connector Protocol's generic verbs are the entire interface.** Nothing about
a connector's internal dynamism ever needs to reach the resolver layer.

### Why "parse an arbitrary OpenAPI spec" is the wrong lever here

Generic OpenAPI-spec-driven client generation (`openapi-generator`,
`datamodel-code-generator`, runtime walkers like `openapi-core`) solves a
real problem: *"I don't know this backend's shape in advance, so derive a
client from its published spec."* But our actual problem is narrower and
easier: **every connector we'll plausibly add is a FHIR R4 server** —
Medplum, HAPI FHIR, Smile CDR, any certified EHR's FHIR API. FHIR R4 isn't
"some API with an OpenAPI spec" — it's a *standard* with a fixed RESTful
convention per resource type:

```
GET    /{ResourceType}/{id}        read
GET    /{ResourceType}?params      search
POST   /{ResourceType}             create
PUT    /{ResourceType}/{id}        update (full)
PATCH  /{ResourceType}/{id}        update (partial)
DELETE /{ResourceType}/{id}        delete
```

Every standards-compliant FHIR server implements exactly this. That means
you don't need to fetch and parse *any* spec to build a generic connector
for them — you need one connector class, parameterized by `base_url` (and
maybe small per-backend auth quirks), that builds `f"/{resource_type}/{id}"`-style
paths instead of hardcoding each resource's path the way `FhirServerConnector`
does today.

**The one connector that can't be generic is `FhirServerConnector` itself**
— specifically *because* our own fhir-server deliberately doesn't follow
the canonical FHIR path convention (`/api/fhir/v1/organizations` instead of
`/Organization`), a decision made earlier in this project for REST-ergonomics
reasons unrelated to FHIR-spec compliance. Every other FHIR-compliant
backend wouldn't need a bespoke class at all.

### Where an actual spec (CapabilityStatement, not OpenAPI) earns its place

FHIR servers publish a `CapabilityStatement` at `GET /metadata` — the
FHIR-native equivalent of an OpenAPI document: which resource types a
server supports, which search parameters, which operations. A generic FHIR
connector *can* legitimately read this at startup to:

- confirm the backend actually supports a resource type before a resolver
  tries to use it (fail fast with a clear error instead of a confusing 404
  mid-request), and
- discover supported search parameters dynamically instead of hardcoding
  each resource's filter list.

This is real, valuable dynamism — but it's discovery/validation layered on
top of the fixed FHIR REST convention above, not a replacement for it. It
never touches the GraphQL schema.

### When you'd actually need OpenAPI-style dynamism (and why it doesn't remove hand-written work)

If a future connector target *isn't* FHIR-native — some legacy EMR with its
own bespoke REST API and an OpenAPI doc, not a FHIR server — spec-driven
codegen *can* automate the transport half (how to form the HTTP request,
what the response shape is). It cannot automate the other half: deciding
that this backend's `patientName` field *means* FHIR's `Patient.name`, or
that its `status: "A"` *means* `active: true`. That's a semantic mapping
decision a human makes once per backend — the same "anti-corruption layer"
adapter work discussed when this connector concept was first designed.
OpenAPI dynamism shrinks the transport-plumbing part of writing that
adapter; it doesn't remove the adapter.

## Direct answer: static or dynamic?

**Both, at different layers, and that split is the actual design:**

| Layer | Static or dynamic | Why |
|---|---|---|
| GraphQL schema (queries/mutations/types) | **Static**, hand-written | One stable contract every connector is adapted *to* — see above |
| *Which* connector is active | **Dynamic**, config-driven | Already built — `connectors.active` in `configs/config.yaml` |
| A FHIR-standard connector's path-building | **Can become generic/semi-dynamic** | Exploit FHIR's own fixed REST convention — one class covers every compliant backend |
| A FHIR-standard connector's capabilities | **Can be runtime-discovered** | Read the backend's own `CapabilityStatement`, not an OpenAPI doc |
| A non-FHIR backend's field mapping | **Always hand-written** | No spec says what a foreign field *means* in FHIR terms |

Generating our *own* OpenAPI spec from static code (the direction you
floated as "more static") isn't actually in tension with any of this —
that's just FastAPI's normal behavior for whatever REST surface this
gateway itself exposes (today: none, since the REST routers were removed —
see dev-doc on that). It's unrelated to how a connector talks to *its own*
downstream backend.

## If this turns into real work later

The natural next concrete step, if a second connector is ever actually
needed, is **not** "build an OpenAPI-spec parser." It's: write one
`GenericFhirConnector(base_url, auth_style)` implementing the `Connector`
Protocol against the standard FHIR REST conventions above, register it
once, and point `connectors.active` (or a new backend's own config entry)
at it. That single class would cover Medplum and most other FHIR-R4-shaped
systems without any backend-specific code — the bespoke, hand-written
`FhirServerConnector` stays the exception precisely because our own
fhir-server is the one connector that breaks the convention.
