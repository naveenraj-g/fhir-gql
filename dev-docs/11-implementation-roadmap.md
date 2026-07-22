# Implementation Roadmap

This is the **master, sequenced plan** for fhir-gql — what to build, in what order, and on which side of the architecture. It synthesizes:

- `01`–`09`: the Medplum feature-gap analyses (auth, FHIR core engine, GraphQL, real-time, bots, admin/tenancy, integrations/media, bulk-data/ops, server bootstrap)
- `10-resource-rollout-plan.md`: which FHIR resources to add and in what order
- Additional cross-checking against Medplum's own feature/operations catalogs (`$graphql`, `$everything`, `$export`, and the other ~58 `$operations` Medplum registers) to make sure nothing FHIR-standard was missed

**How to read this:** every item below carries an ownership tag. This project (fhir-gql) is a REST + GraphQL API layer for the client — the orchestration/auth/RBAC/rate-limiting middleware. The **fhir-server** is the separate, core FHIR data-layer service that owns PostgreSQL and actual resource persistence/search. A third party, the **shared IAM service** (BetterAuth), already issues and validates identity. Tags:

- **[fhir-gql]** — build it here, in this codebase
- **[fhir-server]** — belongs on the other service; fhir-gql either doesn't need it at all, or only needs a thin proxy/pass-through once fhir-server has it
- **[shared IAM]** — belongs to the BetterAuth identity service, not either FHIR service
- **[out of scope]** — deliberately not building this anywhere in this stack right now, with reasoning

---

## Already done

These came out of earlier passes through this same roadmap and are complete, listed here for continuity:

- **[fhir-gql]** CORS policy (`app/main.py`, `CORS_ORIGINS` setting) — was flagged **High** in `09-server-bootstrap-and-cross-cutting.md`.
- **[fhir-gql]** Security response headers (`app/core/security_headers.py`) — CSP, HSTS, X-Content-Type-Options, X-Frame-Options — also **High** in `09`.
- **[fhir-gql]** GraphQL lazy-resolver example (`app/gql/examples/patient_lazy_types.py`, `app/gql/examples/patient_lazy_resolvers.py` — moved out of `app/gql/types/`/`app/gql/resolvers/` into a dedicated `app/gql/examples/` directory so reference-only code never mixes with the production resolver/type files as more resources are added) — demonstrates the field-level lazy resolution + independent/parallel concurrency pattern GraphQL gets "for free"; the dependent/hierarchical half of that pattern (`resolvedOrganization`) is stubbed out until Organization lands (see Phase 2 below).

---

## Phase 1 — Foundation hardening

Do these before scaling out to more resources — retrofitting them across sixteen resources later is much more expensive than baking them into the pattern now.

1. **[fhir-gql]** Fix the `org_id`/tenant-scoping gap. `get_by_id`, `update`, `delete`, and every sub-resource endpoint in `app/routers/patient.py` operate on a bare integer id with no `org_id` enforced — only `list()`/`get_me()` filter by it. Flagged independently by two different analyses (`02-fhir-core-engine.md`, `06-admin-and-multitenancy.md`). **Confirm with the fhir-server team first** whether this is already enforced server-side; if not, it's a live cross-tenant data leak, not a style issue.
2. **[both, coordinated]** Design a compartment/criteria-based access-policy model. Today's RBAC (`app/auth/rbac.py`) is a flat `"resource:action"` check — it cannot express "this user may only see *this* Patient." Medplum's `AccessPolicy` (per-resource-type CRUD rules + FHIRPath `writeConstraint` + patient-compartment scoping) is the reference shape; see `02-fhir-core-engine.md` §"Compartment-based, criteria-driven Access Policies." The enforcement point is mostly fhir-server (it owns the rows), but fhir-gql needs the concept to shape its own permission checks and error messages correctly.
3. **[fhir-gql]** Extend `/health` to check Redis and the downstream fhir-server, not just process liveness — flagged **High** in `09-server-bootstrap-and-cross-cutting.md`. A middleware service's health check that doesn't check its one real dependency is close to meaningless for orchestrator readiness probes.
4. **[fhir-gql]** Refine rate limiting: add an `org_id`-keyed bucket alongside the existing per-user bucket, and per-operation cost weighting (a `_history`/wide search shouldn't cost the same as one `GET`) — see the corrected entry in `02-fhir-core-engine.md` §"FHIR quota / rate-limited writes." The existing `RateLimitMiddleware` is the right foundation; this is a refinement, not new infrastructure.

---

## Phase 2 — Resource expansion, Group 1 (Organization / Practitioner / PractitionerRole / Location)

Full detail in `10-resource-rollout-plan.md`. This group specifically unblocks:

- **[fhir-gql]** The reverse-reference + `strawberry.dataloader.DataLoader` GraphQL pattern flagged **High** in `03-graphql-api.md` — "the moment two resources have a real reference relationship, build the first reverse-reference field together with a DataLoader." Organization is that first relationship, and `Patient.managingOrganization`/`Patient.generalPractitioner` already have the reference fields waiting for it.
- **[fhir-gql]** Completing the dependent/hierarchical GraphQL example dropped when porting `patient_lazy_example.py` — a real `resolvedOrganization` field becomes possible the moment `app/gql/types/organization.py` exists.

REST for all four resources is a mechanical port (source already exists in the sibling project); GraphQL is new work for three of the four (only Organization has GraphQL precedent to port from).

---

## Phase 3 — FHIR feature depth

Once there's more than one resource to exercise these against, close the feature gaps in `02-fhir-core-engine.md` that apply across all resources, not just Patient:

1. **[fhir-gql]** Content-negotiation-aware error responses — return `OperationOutcome`-shaped JSON when `Accept: application/fhir+json` was requested, not a generic `{detail}` body.
2. **[fhir-gql]** `Prefer: return=minimal` fast path on writes, to avoid re-serializing an entire parent resource (with all sub-resource arrays) on every single sub-resource mutation.
3. **[both]** Optimistic concurrency (`If-Match`/`versionId`) — fhir-server would own the actual compare-and-swap; fhir-gql's job is surfacing the `ETag`/`If-Match` HTTP contract at the edge once fhir-server supports it (the `extra_headers` plumbing in `FhirClient` already generalizes to this cheaply).
4. **[fhir-server]** Everything SQL-shaped: search-parameter → column/token/range compilation, chained search, `_filter`, transaction-bundle atomicity, conditional CRUD, soft-delete/expunge/purge/reindex — all correctly out of fhir-gql's hands; see `02-fhir-core-engine.md`'s summary table for the full list. For the full target filter contract (universal params + per-resource matrix + build order), see `12-search-and-filter-standards.md`.
5. **[fhir-gql, thin proxy once fhir-server has it]** A small set of FHIR `$operations` worth exposing as pass-throughs rather than reimplementing:
   - **`$everything`** (`Patient/:id/$everything`) — return everything in a patient's compartment. Natural fit once Group 1–3 resources exist; fhir-gql would proxy to a fhir-server-side implementation rather than fan out N separate calls itself.
   - **`$validate`** — validate a resource without creating it; useful to expose to clients building forms, thin proxy once fhir-server implements FHIR StructureDefinition validation.
   - Bulk `$export` status polling (see Phase 7) — the async-job/202-Accepted pattern.
   - Everything else in Medplum's ~58-operation catalog (`$match`, `$summary`, terminology operations `$expand`/`$lookup`/`$subsumes`/`$translate`, measure/plan operations, CCDA/DICOM/SMART-Health-Card operations, DB-internal super-admin operations) is **out of scope** — either fhir-server's concern entirely, or not relevant to this platform's actual product needs. Don't build these speculatively.

---

## Phase 4 — Resource expansion, Groups 2–4

Scheduling cluster (Schedule, Slot, Appointment, Encounter), clinical-data cluster (Observation, Condition, MedicationRequest, ServiceRequest, DiagnosticReport, DocumentReference), supporting data (HealthcareService, Terminology). Full detail and per-resource checklist in `10-resource-rollout-plan.md`. Apply the Phase 1 fixes (tenant scoping, access-policy awareness) to every new resource from day one rather than retrofitting later.

---

## Phase 5 — Real-time (FHIR Subscriptions, WebSockets)

Entirely greenfield today — see `04-realtime-events.md` for full detail. Summary:

1. **[fhir-server, cross-repo blocker]** A minimal event-emission hook on fhir-server's write path — on every committed create/update/delete, publish a compact event (`resourceType`, `id`, `versionId`, `interaction`, `tenantId`, `timestamp`) to a Redis Stream. This is the longest-lead item in the whole roadmap and should be raised with whoever owns fhir-server **now**, in parallel with everything else, since Phases 5 can't complete without it.
2. **[fhir-gql]** WebSocket infrastructure (FastAPI native WebSocket routes, connection lifecycle, wired into `app/main.py`'s `lifespan()`).
3. **[fhir-gql]** `Subscription` resource CRUD (REST + GraphQL, following the Phase 2/4 per-resource pattern), persisted through `FhirClient` to fhir-server like any other resource.
4. **[fhir-gql]** An `arq`-based worker pool consuming the fhir-server event stream: criteria matching, fan-out to rest-hook delivery (retry/backoff) and WebSocket delivery.
5. **[fhir-gql]** Subscription auto-disable on repeated delivery failure, reusing the `RateLimitMiddleware` Redis idiom.
6. **[fhir-gql, if needed]** FHIRcast, only if imaging/multi-app context-sync becomes an actual product requirement — independent module, minimal coupling to the rest.

---

## Phase 6 — Automation (Bots, CDS Hooks)

See `05-automation-and-bots.md` for full detail. Summary:

1. **[separate execution service]** Bot execution dispatch + a real sandboxed runtime (AWS Lambda via `boto3`, or one-off Docker containers per invocation — skip in-process sandboxing entirely, even Medplum documents its `vm`-based approach as not a real security boundary).
2. **[fhir-gql]** CDS Hooks (discovery + invocation) — nearly free once the execution contract from (1) exists, since it's a thin router with no logic of its own in Medplum's own implementation.
3. **[fhir-gql]** Cron-scheduled bot automation and async batch/bundle processing, both consumers of the same `arq`-based job queue introduced in Phase 5.

---

## Phase 7 — Platform / ops maturity

See `08-bulk-data-ops-infra.md` and `06-admin-and-multitenancy.md`. Summary:

1. **[infra/ops, both services]** OpenTelemetry instrumentation (`opentelemetry-instrumentation-fastapi`/`-httpx`/`-redis`) — flagged **High**: fhir-gql currently has zero tracing/metrics, only structured logs, so there's no visibility into where latency actually goes across JWT validation → RBAC → fhir-server round-trip → Redis.
2. **[fhir-gql]** Standardized audit-event vocabulary (HL7 AuditEvent action/outcome codes) layered over the existing JSON logger — cheap, since fhir-gql already owns every access-control decision worth auditing.
3. **[fhir-gql, self-contained]** Per-user Redis-backed key-value store, transactional email sending, outbound URL/SSRF validation — all low-risk, reuse infrastructure (Redis, auth context) already in place; pick up opportunistically as real needs appear.
4. **[decision, not a build]** Multi-tenancy/Project model: **do not build a Medplum-style `Project`/admin/membership layer in fhir-gql.** It would duplicate what BetterAuth's organization plugin already owns (or should own) and what fhir-server's `org_id` column enforces physically. See `06-admin-and-multitenancy.md`'s "Recommended next steps" for the full reasoning — this is a considered non-decision, not a gap.

---

## Explicitly out of scope right now

| Item | Where it actually belongs | Why not here |
|---|---|---|
| MCP server | Separate application (per prior decision) | Deliberately built as its own app rather than inside fhir-gql |
| Full OAuth2/OIDC authorization server (authorize/token/introspect/register), MFA, SCIM, external IdP federation | **[shared IAM]** BetterAuth | fhir-gql is a stateless JWT verifier by design, not an auth server — see `01-identity-and-access.md` |
| Binary/S3/Azure/GCS storage backends, presigned URLs | **[FileNest]** — a separate, already-existing file-processing/storage service | Not a future build item at all: FileNest already uploads/stores files and hands the frontend back metadata (URL, content type, size, hash); fhir-gql only ever accepts that metadata into an Attachment field (already working for `Patient.photo` today) — see the correction note at the top of `07-integrations-and-media.md` |
| DICOMweb, HL7v2 ingestion, on-prem Agent | **[fhir-server]** | Gated behind resources (`Media`, `Agent`) that don't exist in this stack yet — see `07-integrations-and-media.md` |
| DB migrations, seeding, reindexing, data-warehouse sync | **[fhir-server]** | fhir-gql never owns Postgres, by construction — see `08-bulk-data-ops-infra.md` |
| Search-parameter → SQL compilation, token/range indexing, transaction-bundle atomicity, pre-commit bot hooks | **[fhir-server]** | Fundamentally a Postgres/SQL concern fhir-gql has no access to — see `02-fhir-core-engine.md` |
| DB-internal super-admin operations (`$db-stats`, `$db-schema-diff`, `$explain`, etc.) | **[fhir-server]** | Direct database introspection, not an API-layer concern at all |
| CCDA export, SMART Health Cards/Links, AWS Textract OCR, terminology `$expand`/`$translate`/measure-evaluation operations | **[fhir-server]**, or not needed | Speculative — build only if a concrete product requirement emerges; not implied by anything already in this stack |

---

## Cross-reference index

| Roadmap phase | Detail document(s) |
|---|---|
| Phase 1 (foundation) | `02-fhir-core-engine.md`, `06-admin-and-multitenancy.md`, `09-server-bootstrap-and-cross-cutting.md` |
| Phase 2 & 4 (resources) | `10-resource-rollout-plan.md` |
| Phase 3 (FHIR depth) | `02-fhir-core-engine.md`, `03-graphql-api.md` |
| Phase 5 (real-time) | `04-realtime-events.md` |
| Phase 6 (automation) | `05-automation-and-bots.md` |
| Phase 7 (platform/ops) | `08-bulk-data-ops-infra.md`, `06-admin-and-multitenancy.md` |
| Out of scope | `01-identity-and-access.md`, `07-integrations-and-media.md` |
