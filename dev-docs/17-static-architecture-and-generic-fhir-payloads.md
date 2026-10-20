# Static GraphQL/Connectors + What a Truly FHIR-Standard Payload Buys Us

Case study referenced throughout: `E:\work\practice\langcare-mcp-fhir` (a Go MCP
server that fronts Epic, Cerner, Google Cloud Healthcare, OpenEMR, and generic
FHIR R4 backends with exactly **4 tools**). This report does not touch
`16-connector-dynamism.md` — it's a separate, follow-on analysis.

## 1. The static decision is correct — and here's the MCP-specific reason why

The call to go static (hand-written GraphQL schema + hand-written connectors,
selected by config, not generated at runtime) was already reached
independently in `16-connector-dynamism.md`, for three reasons: clients need
one stable schema, resolvers carry authorization/business logic no spec can
express, and Strawberry binds queries/mutations to Python functions at import
time — there's no "load this resolver from a spec at runtime" path.

There's a fourth reason, specific to the MCP angle raised this time: **FastMCP
generates tools from the OpenAPI/GraphQL contract at build/startup time.** If
the GraphQL schema's shape varied with which connector happened to be active,
the MCP tool surface would have to be regenerated in lockstep every time the
connector changed — two independently-versioned dynamic layers that must stay
synchronized, with no single source of truth for "what can an AI caller
currently do." A static schema means the MCP tool list is exactly as stable as
the schema is, full stop. That's the concrete cost a dynamic schema would
impose, beyond the three already-documented reasons.

So: GraphQL schema stays static, connector *selection* stays config-driven
(`connectors.active`), each connector's internals stay hand-written — no
change to that conclusion. The useful new question is what the reference
project reveals about *how far* "hand-written" needs to go.

## 2. Case study: how langcare-mcp-fhir covers ~40 FHIR resource types with 4 tools

The four tools are `fhir_create`, `fhir_read`, `fhir_search`, `fhir_update`
(`internal/tools/fhir_*.go`). None of them is resource-specific. Every one
takes `resourceType` as a runtime **string** argument, not a type:

```go
// internal/tools/fhir_create.go — InputSchema()
"resourceType": {"type": "string", "description": "...e.g., Patient, Observation, Medication"},
"resource":     {"type": "object", "description": "The FHIR resource data to create"},
```

Underneath, every tool calls through one `Provider` interface
(`internal/fhir/providers/provider.go`) with exactly 4 generic methods —
`Read`, `Search`, `Create`, `Update`, parameterized by `resourceType string`,
never one method per resource:

```go
type Provider interface {
    Read(ctx, resourceType, id string) (json.RawMessage, error)
    Search(ctx, resourceType, queryParams string) (json.RawMessage, error)
    Create(ctx, resourceType string, resource json.RawMessage) (json.RawMessage, error)
    Update(ctx, resourceType, id string, resource json.RawMessage) (json.RawMessage, error)
}
```

`BaseProvider.doRequest` (shared by every backend) builds
`{baseURL}/{resourceType}/{id}` and sends/receives the body completely
untouched as `json.RawMessage` — no per-resource struct, no field mapping —
while hardcoding `Accept: application/fhir+json` / `Content-Type:
application/fhir+json` on every call:

```go
url := fmt.Sprintf("%s/%s/%s", b.baseURL, resourceType, id)
req.Header.Set("Accept", "application/fhir+json")
req.Header.Set("Content-Type", "application/fhir+json")   // only when body != nil
```

Five backends (`epic.go`, `cerner.go`, `gcp.go`, `openemr.go`, `generic.go`)
each supply only auth/base-URL wiring and reuse this same request logic —
none of them overrides `Read`/`Search`/`Create`/`Update` with resource-aware
code.

**Why this works with only 4 tools covering every resource type:** genericity
here is a property of the *wire contract*, not of Go or MCP. Every backend
behind this already (a) follows FHIR's one fixed REST convention — `GET/POST/
PUT /{ResourceType}/{id}` — and (b) exchanges literal, unmodified FHIR R4 JSON
in both directions. Because both of those are true for every provider, one
generic request-builder plus one generic JSON passthrough covers all of them.
Take away either property — a backend with its own URL shape, or a backend
that needs its JSON translated to/from FHIR — and the 4-tools model breaks;
you'd be back to writing one adapter per backend, exactly like
`FhirServerConnector` already is in our own project.

## 3. Can fhir-gql's GraphQL layer do the same? Partly — and it mostly already does

A literal copy — one generic `fhirRequest(resourceType: String, op: String,
payload: JSON): JSON` field — would technically work, but throws away
everything a typed GraphQL schema is for: field selection, client-side
codegen, compile-time validation. That's not a new conclusion; it's reasons 1
and 2 from `16-connector-dynamism.md` restated (clients code against a stable
contract; a resolver carries authz/business logic no generic field could
express).

But look one layer below the schema: **the `Connector` Protocol already is
our version of `Provider`.** Both are a small, fixed set of generic verbs
(`post`/`get`/`patch`/`delete` vs. `Create`/`Read`/`Search`/`Update`) that
every backend implements once, instead of once per resource type. The
reference project's 4 Go tools and our Connector Protocol are the same idea
at the same layer — generic-by-resourceType plumbing underneath a stable,
typed, resource-aware surface above it (MCP tool schema there; GraphQL schema
here). This part of the architecture was already right.

## 4. The actual gap, and the one change that would unify both worlds

Where we differ from every provider in the reference project is **fhir-server
itself** — and `16-connector-dynamism.md` already named this precisely:

> "The one connector that can't be generic is `FhirServerConnector` itself —
> specifically *because* our own fhir-server deliberately doesn't follow the
> canonical FHIR path convention (`/api/fhir/v1/organizations` instead of
> `/Organization`)..."

Lay that next to what the reference project needs from a backend to treat it
generically (section 2 above), and the gap splits into exactly two pieces:

| What a generic FHIR backend needs | fhir-server today |
|---|---|
| Fixed path shape: `/{ResourceType}/{id}` | `/api/fhir/v1/organizations/{organization_id}` — ergonomic, not FHIR-shaped |
| FHIR JSON out | **Already there** — `Accept: application/fhir+json` → full FHIR R4 camelCase (`app/core/content_negotiation.py`) |
| FHIR JSON in (create/update) | **Not there** — `OrganizationCreateSchema`/`PatchSchema` only accept the "plain" shape; there's no symmetric input path |

Only the first and third rows are real gaps — the response side was already
solved before this report, by the existing `Accept`-header negotiation.

**If both gaps were closed** — a `Content-Type: application/fhir+json`
write path (mirroring the existing `Accept`-header read path) feeding a new
`from_fhir_<resource>()` parser, plus routes that also answer on the canonical
`/{ResourceType}/{id}` shape (additive, alongside the existing ergonomic
routes — not a replacement, since other callers may depend on those) — then
fhir-server would satisfy both properties section 2 identified as sufficient
for genericity. Concretely, that buys two things, not one hypothetical:

1. `FhirServerConnector` stops being the exception. `16-connector-dynamism.md`
   already proposed a `GenericFhirConnector(base_url)` for any standards-
   compliant backend (Medplum included) — fhir-server could use that exact
   same class instead of its own bespoke one, collapsing two adapters into
   one.
2. It becomes literally pluggable into something like the reference
   project's `generic` provider with zero new Go code — the same kind of
   tool-server could point at fhir-server the same way it points at Epic or
   Cerner today. That's not speculative; it's the direct, demonstrated
   consequence of fhir-server satisfying the same two properties every
   provider in that project already satisfies.

## 5. Honest cost, and recommended sequencing

This is real, contract-level work on fhir-server, not a config flip — new
schemas, a new mapper direction, new routes, and (per `CLAUDE.md`'s "OpenAPI
Spec = MCP Contract") the same rigor as any other field/contract change,
verified at `/openapi.json`. It should be additive, not a rip-and-replace of
the existing ergonomic contract other callers already depend on.

Given that cost, the sequencing worth doing is:

1. **Now, cheap:** keep fhir-server's contract exactly as-is; do plain↔FHIR
   translation inside `FhirServerConnector` on the fhir-gql side (already
   recommended in the prior discussion this session). Zero fhir-server risk,
   zero MCP-contract change.
2. **Later, only if a real reason shows up** — e.g., wanting the reference
   project's tool-server pattern pointed at fhir-server directly, or a second
   FHIR-native caller besides fhir-gql ever needing to write real FHIR JSON
   straight into it — add the canonical path + FHIR-input surface to
   fhir-server, and only then retire `FhirServerConnector` in favor of the
   generic connector class `16-connector-dynamism.md` already designed for
   this exact situation.
