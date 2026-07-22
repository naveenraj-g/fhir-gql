# Medplum → fhir-gql Feature Gap Analysis

This folder is a systematic feature inventory of [Medplum](https://github.com/medplum/medplum)'s
server (`packages/server`) and GraphQL engine (`packages/fhir-router/src/graphql`), read in full and
compared feature-by-feature against what `fhir-gql` has today, to decide what's worth building next.

**Start here:** [`11-implementation-roadmap.md`](11-implementation-roadmap.md) is the master, phased
build plan synthesizing everything below into a concrete order — read that first. It leans on
[`10-resource-rollout-plan.md`](10-resource-rollout-plan.md) for which FHIR resources to add next, and
on the `01`–`09` reports below for platform-feature depth on each phase.

## Why Medplum, and why this shape of report

Medplum is a mature, production open-source FHIR platform. It is a **monolith**: one Node.js/TypeScript
service owns the HTTP API, the FHIR business logic, *and* PostgreSQL persistence. `fhir-gql` is
architected differently on purpose — a **split** design:

```
Client → fhir-gql (this service: auth, RBAC, rate limiting, orchestration, REST + GraphQL)
              → fhir-server (separate service: owns Postgres, actual FHIR CRUD/search/SQL)
```

Because of that split, "does Medplum have feature X" is never a complete question — the real question
for every feature catalogued here is **which side of the split it belongs on**: `fhir-gql`
(middleware/orchestration), `fhir-server` (data layer), a **shared IAM service** (fhir-gql already
delegates JWT issuance to a separate BetterAuth-based identity provider, so a large share of Medplum's
"auth" surface belongs there, not here), or genuinely **out of scope**. Every entry in every report
below makes that call explicitly, with reasoning — this is a planning document, not a Medplum feature
list.

## Method

Nine parallel deep-dives, each covering a disjoint slice of Medplum's `src/` tree, every non-test file
read in full (not skimmed) by a dedicated research pass, cross-checked against fhir-gql's actual current
code (`app/auth/`, `app/gql/`, `app/fhir_client/`, `app/middleware/`, `app/main.py`, etc. — read first,
so nothing here misdescribes something as missing that already exists). Two independent passes
(`02` and `06`) converged on the same live authorization gap from different angles — see below.

## Reports

| # | File | Scope |
|---|---|---|
| 01 | [identity-and-access.md](01-identity-and-access.md) | Password/MFA/OAuth2/OIDC auth, SCIM provisioning, external IdP federation — `src/auth/`, `src/oauth/`, `src/scim/` |
| 02 | [fhir-core-engine.md](02-fhir-core-engine.md) | Resource CRUD, search/SQL generation, access policies, transactions, validation — `src/fhir/*`, `fhir-router/src/{repo,batch,fhirrouter,urlrouter}.ts` |
| 03 | [graphql-api.md](03-graphql-api.md) | The GraphQL engine — dynamic schema, reverse-reference traversal, DataLoader batching — `fhir-router/src/graphql/*` |
| 04 | [realtime-events.md](04-realtime-events.md) | FHIR Subscriptions, WebSockets, FHIRcast, webhooks — `src/workers/subscription*`, `src/ws/*`, `src/fhircast/*`, `src/webhook/*` |
| 05 | [automation-and-bots.md](05-automation-and-bots.md) | Bot execution (Lambda/Fission/VM sandboxes), CDS Hooks, cron/batch jobs — `src/bots/`, `src/cds/`, `src/cloud/{aws,fission}/*` |
| 06 | [admin-and-multitenancy.md](06-admin-and-multitenancy.md) | Projects, membership, invites, super-admin ops — `src/admin/*` |
| 07 | [integrations-and-media.md](07-integrations-and-media.md) | Binary/S3/DICOM/HL7v2/Agent/**MCP server**/Textract — `src/storage/`, `src/dicom/`, `src/hl7/`, `src/agent/`, `src/mcp/` |
| 08 | [bulk-data-ops-infra.md](08-bulk-data-ops-infra.md) | Bulk export, migrations/seeding, job queues, OpenTelemetry, config, utils — `src/fhir/bulkdata.ts`, `src/migrations/`, `src/workers/`, `src/otel/`, `src/util/` |
| 09 | [server-bootstrap-and-cross-cutting.md](09-server-bootstrap-and-cross-cutting.md) | App bootstrap, CORS, security headers, context propagation, health checks — root `src/*.ts` |
| 10 | [resource-rollout-plan.md](10-resource-rollout-plan.md) | Which FHIR resources to add next, in what order, and how much REST vs. GraphQL work each needs |
| 11 | [implementation-roadmap.md](11-implementation-roadmap.md) | **Master roadmap** — phased build order synthesizing all reports above, with explicit fhir-gql / fhir-server / shared-IAM ownership per item |
| 12 | [search-and-filter-standards.md](12-search-and-filter-standards.md) | Every filter every resource's list/search endpoint should support — universal FHIR params, per-resource matrix, value-type behavior, build order |

Each report uses one consistent per-feature template: **What it does / Source files / How it works /
Belongs in / Port notes / Priority**, closing with a summary table and a "Recommended next steps"
section.

---

## Cross-cutting finding: live tenant-isolation gap

Two independent passes (`02-fhir-core-engine.md` and `06-admin-and-multitenancy.md`), analyzing
completely different Medplum subsystems (access policies vs. project membership), converged on the same
issue in fhir-gql's **current** code, not Medplum's:

> `PatientService.list()` and `get_me()` filter by `actor.org_id`, but `get_by_id`, `update`, `delete`,
> and every sub-resource endpoint in `app/routers/patient.py` (names, identifiers, telecom, addresses,
> photos, contacts, communications, general-practitioners, links) operate on a bare integer `id` with no
> `org_id` sent to or enforced by `fhir-server`. `GET /api/v1/patients/{id}` has no visible ownership
> check today.

This should be confirmed with whoever owns `fhir-server` first — if `org_id` is independently re-derived
and enforced server-side on every by-id call, the gap is cosmetic; if fhir-gql is the only layer that
ever sees `org_id` on these paths, this is a **live cross-tenant data leak**, not a hypothetical one. See
`02-fhir-core-engine.md` §"Compartment-based, criteria-driven Access Policies" and
`06-admin-and-multitenancy.md` §"Recommended next steps" for the concrete fix (thread `actor.org_id`
through `PatientClient.get_by_id/patch/delete` exactly as it's already threaded through `list()`).

---

## Consolidated priority list

### High priority — do soon

| Feature | Report | Why |
|---|---|---|
| Fix `org_id` enforcement on by-id Patient routes | 02, 06 | Live tenant-isolation gap, see above |
| Compartment/criteria-based access policies | 02 | Flat RBAC can't express "this user may only see *this* Patient" |
| CORS policy | 09 | Missing entirely — no browser frontend can call this API today |
| Standard security response headers (CSP/HSTS/X-Frame-Options) | 09 | Zero-cost hardening, currently absent |
| `/health` should check Redis + downstream fhir-server | 09 | Liveness-only today; meaningless for orchestrator readiness probes |
| OpenTelemetry instrumentation | 08 | Zero tracing/metrics today across JWT→RBAC→fhir-server→Redis hops |
| Audit event vocabulary (HL7 AuditEvent shape over existing JSON logger) | 08 | fhir-gql owns every auth/RBAC decision worth auditing, no standard shape yet |
| New Patient self-registration flow | 01 | Only auth feature that directly extends the shipped Patient slice; needs a new BetterAuth contract |
| Reverse-reference GraphQL fields + DataLoader | 03 | **The** reason to prefer GraphQL over REST; entirely absent — becomes urgent the moment a 2nd cross-referencing resource ships |
| Bot execution dispatch + AWS Lambda runtime | 05 | Nothing else in the automation domain works without this landing first |
| FHIR Subscription delivery + WebSocket infra + Redis fan-out | 04 | Entire real-time domain is currently a greenfield gap; needs a small cross-repo fhir-server hook first (see report §0) |
| MCP server | 07 | Uniquely low-cost given existing FastAPI/JWT/RBAC/`fhir_client` — plugs straight into this project's AI-tooling context |

### Explicitly correct to leave out (don't build these in fhir-gql)

| Area | Belongs to | Why |
|---|---|---|
| Full OAuth2/OIDC authorization server (authorize/token/introspect/register) | Shared BetterAuth IAM service | fhir-gql is a stateless JWT verifier by design, not an auth server |
| MFA, SCIM, external IdP federation | Shared BetterAuth IAM service | Same reasoning |
| `Project`/membership/multi-tenancy admin model | Shared IAM service (org plugin) + fhir-server (`org_id` column) | Building a parallel tenancy model would create a second, competing source of truth |
| Search-parameter → SQL compilation, token/range indexing, chained search | fhir-server | Fundamentally a Postgres/SQL concern fhir-gql has no access to |
| Transaction/batch bundle atomicity, pre-commit bot hooks | fhir-server | True cross-resource atomicity needs a shared DB transaction fhir-gql cannot have over HTTP |
| DB migrations, seeding, reindexing, data-warehouse sync | fhir-server | fhir-gql never owns Postgres, by construction |
| In-process VM bot sandbox | N/A | Even Medplum documents this as *not* a real security boundary — skip straight to Lambda/containers |
| Binary/S3/Azure/GCS storage backends, DICOMweb, HL7v2 ingestion | fhir-server / storage backend | Gated behind FHIR resources (`Binary`, `Media`, `DocumentReference`) that don't exist in this stack yet |

---

## Suggested sequencing

1. **Fix now, cheap and urgent:** `org_id` enforcement gap, CORS, security headers, `/health` dependency
   checks — all small, additive, no architectural risk.
2. **Since GraphQL is explicitly next:** per `03-graphql-api.md`, port the 2nd and 3rd FHIR resources
   using the existing hand-written `app/gql/types|resolvers/<resource>.py` pattern first — don't
   generalize on one data point — then build the *first* reverse-reference field together with a
   `strawberry.dataloader.DataLoader` the moment two resources actually reference each other. Add
   query-depth/cost guarding in the same iteration, since that's exactly when unbounded traversal stops
   being theoretical.
3. **Observability pass:** OpenTelemetry + audit-event vocabulary (`08`) — both reuse infrastructure
   that already exists (structured logger, Redis) and pay off immediately once more resources/domains
   land.
4. **Real-time:** raise the fhir-server event-hook requirement (`04`, step 0) with whoever owns that
   repo in parallel with the above — it's the longest-lead item in this whole report and gates the
   entire Subscriptions/WebSocket domain.
5. **Automation:** bot execution dispatch + CDS Hooks (`05`) once a concrete product need for
   server-side custom logic appears — CDS Hooks is nearly free once the execution contract exists.
6. **Opportunistic:** MCP server (`07`) whenever AI-tooling access to FHIR data becomes a priority — it
   has no dependency on anything else in this list.
