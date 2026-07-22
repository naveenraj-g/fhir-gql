# FHIR Core Engine — Medplum vs fhir-gql

Scope: the FHIR REST engine — resource CRUD, search, transactions/batches, validation, access control, and routing.

Medplum source analyzed: `packages/server/src/fhir/{accesspolicy,jsonschema,metadata,outcomes,precommit,range-column,references,repo,resource-cap,response,rewrite,routes,search,searchparameter,sharding,smart,sql,structure,token-column,tokens}.ts` and `packages/fhir-router/src/{batch,fhirrouter,repo,urlrouter}.ts`.

fhir-gql baseline (what already exists today, read in full before this analysis):
- `app/fhir_client/client.py` — shared `FhirClient` wrapping `httpx.AsyncClient`. Handles: audit-field injection (`created_by`/`updated_by` stamped from `actor.sub` on POST/PATCH, opt-out via `inject_audit=False`), `Accept` header pass-through for content negotiation (`application/json` vs `application/fhir+json`), and error normalization (`_handle()` converts any 4xx/5xx into `HTTPException(status_code, detail)`, pulling `detail` from the downstream JSON body or falling back to raw text; 204 → `None`).
- `app/fhir_client/patient.py` — domain client enumerating every Patient + sub-resource path (`/patients`, `/patients/{id}/names`, `/identifiers`, `/telecom`, `/addresses`, `/photos`, `/contacts`, `/communications`, `/general-practitioners`, `/links`), all delegating to `FhirClient`.
- `app/services/patient_service.py` — `PatientService` sits between routers and the client. Owns: empty-PATCH rejection (422) for the top-level Patient and every sub-resource, and JWT-scoped `/me` resolution (`get_me()` restricts lookups to `actor.sub`/`actor.org_id`). Does **not** do search-parameter parsing, does **not** build SQL, does **not** enforce row-level/compartment access — it forwards filters as plain kwargs to the client.
- `app/auth/rbac.py` — single `check_permission(user, resource, action)` function checking a flat `"{resource}:{action}"` string against the JWT's `permissions` claim; shared by REST (`require_permission()` FastAPI dependency) and GraphQL. No compartments, no per-resource-instance rules, no FHIRPath.
- `app/routers/patient.py` — 42 REST endpoints, RBAC-gated per route, content-negotiation-aware. No `/Bundle`, no `$operations`, no `_history`, no `/metadata`.

Only `Patient` is implemented; sub-resources (names, identifiers, telecom, etc.) are child-table CRUD, not independent FHIR resources with their own compartments/search params. fhir-gql has **no SQL layer at all** — everything below that would touch Postgres is downstream's job by construction. The interesting question for every feature is therefore: does fhir-gql need to *understand* the concept (to shape its REST/GraphQL surface correctly) even though it never *implements* the mechanism.

---

## 1. Repository pattern — resource read/write

### Create with server-assigned ID
- **What it does:** Creates a new resource, normally with a server-generated UUID; optionally accepts a client-assigned ID (`assignedId`) reserved for super-admins/batch imports, checking first that the ID isn't already in use.
- **Source files:** `packages/server/src/fhir/repo.ts` — `Repository.createResource()`, `Repository.generateId()` (lines ~448-492).
- **How it works:** Calls `recordFhirQuota(WRITE)` and `resourceCap().created()` for rate/quota accounting, then delegates to the shared `updateResourceImpl(resource, create=true)` pipeline (see next entry) so create and update share one code path. ID collision check (`assignedId` branch) round-trips through `SystemRepository.readResourceImpl` to detect an existing row before insert.
- **Belongs in:** `fhir-server (data layer/persistence)`. Assigning primary keys and enforcing uniqueness is fundamentally a database concern.
- **Port notes:** fhir-server already returns a server-generated integer PK for Patient (per `PatientClient.create()`); no gap. If fhir-server later wants client-assigned IDs (rare, mostly for bulk import), it should follow Medplum's "existence probe before insert" pattern rather than relying on a DB unique-constraint race.
- **Priority:** Low — fhir-gql has nothing to add here; fhir-server's existing create flow is sufficient for Patient today.

### Read with cache-then-DB fallback
- **What it does:** Reads a resource by ID, first checking an in-process/Redis cache, then falling back to Postgres, applying access-policy field hiding on the way out.
- **Source files:** `repo.ts` — `Repository.readResource()`, `readResourceImpl()`, `readResourceFromDatabase()`, `repository/resource-cache.ts` (cache entry get/set/delete, referenced not read in full but used extensively).
- **How it works:** `readResourceImpl` checks a `CacheEntry` keyed by `resourceType/id`; if present and the access policy permits `READ` on the cached copy, it's returned without touching Postgres. Otherwise it queries `SelectQuery(resourceType).column('content').column('deleted').where('id','=',id)`, applies `addSecurityFilters()` (project + access-policy predicates), throws `notFound`/`gone` appropriately, and re-populates the cache (skipped mid-transaction).
- **Belongs in:** `fhir-server (data layer/persistence)` for the actual cache+DB mechanics. fhir-gql already gets equivalent behavior for free since it's a pure proxy (`PatientClient.get_by_id()` → `GET /patients/{id}`) — whatever caching fhir-server does is transparent to it.
- **Port notes:** If fhir-server is slow on hot Patient reads, a read-through cache (Redis, keyed by resource+id, invalidated on write) is the standard pattern; fhir-gql itself should **not** cache resource bodies (it has no invalidation signal across requests/instances) but could safely cache short-lived, per-request data (e.g. the `/me` lookup already does a list-then-refetch round trip that could be optimized if fhir-server added a `?user_id=&include=self` shortcut).
- **Priority:** Low for fhir-gql directly; Medium for fhir-server if Patient read volume grows.

### Batch reference resolution (`readReferences`)
- **What it does:** Resolves a list of FHIR `Reference`s to resources in one call, mixing cache hits and DB reads, returning `(Resource | Error)[]` aligned to the input order.
- **Source files:** `repo.ts` — `Repository.readReferences()`, `processReadReferenceEntry()`.
- **How it works:** Bulk-fetches cache entries (`getCacheEntries`), then for each reference either serves from cache (after a per-item access check) or does an individual `readResourceFromDatabase`. Errors are captured per-slot rather than throwing, so partial failures don't abort the batch — this is the primitive that both `_include`/`_revinclude` and GraphQL nested-reference resolution build on.
- **Belongs in:** `fhir-server` for the DB/cache half; `fhir-gql` for the *GraphQL resolver batching* half, since fhir-gql's GraphQL layer will face the exact same N+1 problem Medplum's GraphQL resolvers solve with this method.
- **Port notes:** When fhir-gql's GraphQL schema grows beyond Patient (e.g. resolving `Patient.generalPractitioner` references, or a future `Observation.subject`), implement a per-request **DataLoader** (batch + cache within one GraphQL execution) that groups references by type and calls the downstream `list`/batch-get endpoint once instead of N times. `strawberry` has first-class DataLoader support (`strawberry.dataloader.DataLoader`) — this is the direct Python analogue of `readReferences`.
- **Priority:** Medium — becomes High as soon as a second resource type with cross-references (e.g. Practitioner, Organization) is added to the GraphQL schema.

### Resource history (`_history`)
- **What it does:** Returns every version of a resource, newest first, each wrapped in a `Bundle` entry with its own `response.status`/`outcome` (so deleted versions show up as "gone").
- **Source files:** `repo.ts` — `Repository.readHistory()`.
- **How it works:** Queries a parallel `{ResourceType}_History` table (`SelectQuery(resourceType + '_History')`) ordered by `lastUpdated DESC`, paginated via `limit`/`offset` clamped to `DEFAULT_MAX_SEARCH_COUNT`; a separate `COUNT(*)` query gets the total. Deleted versions have no `content` and are represented with a synthetic `gone` `OperationOutcome`.
- **Belongs in:** `fhir-server (data layer/persistence)` — requires a full version-history table design.
- **Port notes:** fhir-gql has no `_history`/versioning concept today (no `versionId`/`ETag` anywhere in `client.py` or `patient.py`). If audit/compliance requirements demand it later, fhir-server should add a shadow history table per resource (or a single `resource_history(resource_type, resource_id, version, content, changed_at, changed_by)` table) and expose `GET /patients/{id}/_history`; fhir-gql would then add a thin passthrough client method exactly like its other list/get calls — no new logic needed on the middleware side beyond exposing the route.
- **Priority:** Low today (no product requirement seen), Medium if HIPAA/audit trail requirements formalize.

### Optimistic concurrency (`If-Match` / `versionId`)
- **What it does:** Rejects an update if the caller's `If-Match` ETag doesn't match the resource's current `versionId`, preventing lost updates from concurrent writers.
- **Source files:** `repo.ts` — `updateResource()` (`options.ifMatch` branch, forces a transaction), `updateResourceImpl()` (`preconditionFailed` check against `existing.meta?.versionId`); `fhir-router/src/fhirrouter.ts` — `updateResource()` parses `If-Match` header into `ifMatch` option; `response.ts` — `sendResponseHeaders()` sets the `ETag` response header from `meta.versionId`.
- **How it works:** `versionId` is a fresh UUID generated on every write (`this.generateId()`), stored in `meta.versionId`, and returned as a weak `ETag`. A conditional update wraps the read-check-write in `withTransaction` so the compare-and-swap is atomic under Postgres MVCC.
- **Belongs in:** `both`. The actual compare-and-swap must happen at fhir-server (it owns the row and the transaction). fhir-gql's job is to **surface** the `If-Match`/`ETag` HTTP contract at the edge and pass it through untouched.
- **Port notes:** fhir-gql's `FhirClient.patch()`/`post()` currently don't forward `If-Match`/`ETag` headers at all — there's no `versionId` concept in the Patient schemas. If fhir-server adds optimistic concurrency (e.g. an `updated_at`-based `If-Unmodified-Since`, or a real `version` column), add an optional `etag: str | None` parameter threaded through `FhirClient.patch()` → `extra_headers["If-Match"]`, and forward the resulting `409`/`412` as-is through the existing `_handle()` error path (already generic). Minimal effort since the plumbing (`extra_headers` dict) already exists.
- **Priority:** Medium — cheap to add once fhir-server supports it, and it closes a real correctness gap (concurrent PATCHes to the same Patient can silently clobber each other today).

### "Not modified" short-circuit
- **What it does:** If an update payload is deep-equal to the existing resource, skips the write entirely (no new version, no audit event, no background jobs) and returns the existing resource.
- **Source files:** `repo.ts` — `isNotModified()` (uses `stringify` + `deepEquals` after round-tripping through JSON to normalize `undefined`/empty values).
- **Belongs in:** `fhir-server (data layer/persistence)`.
- **Port notes:** Cheap correctness/efficiency win: fhir-server's PATCH handlers could compare the incoming diff against current row values and return `200` without bumping `updated_at`/emitting change events when nothing actually changed. Not currently visible from fhir-gql's side (it always forwards the PATCH), so no fhir-gql action needed — this is purely a downstream optimization.
- **Priority:** Low.

### Meta computation on write (versionId, lastUpdated, author, project, account, compartment)
- **What it does:** Server-computes several `meta.*` fields on every write instead of trusting client input, subject to specific override rules (e.g. only super-admins can backdate `lastUpdated`).
- **Source files:** `repo.ts` — `updateResourceImpl()` body constructing `resultMeta`; helpers `getLastUpdated()`, `getProjectId()`, `getAuthor()`, `getAccounts()`, `getCompartments()`.
- **How it works:** `meta.author` always comes from `RepositoryContext.author` (the authenticated actor), never the request body — this is the direct analogue of fhir-gql's `created_by`/`updated_by` injection. `meta.project` resolution has special cases per resource type (Project, ProjectMembership, User, protected types). `meta.compartment` is recomputed from patient/account/project references so search-time compartment filtering and `_compartment` stay correct even if the resource moved compartments.
- **Belongs in:** `fhir-server (data layer/persistence)`, but the *pattern* fhir-gql already follows (server-controlled author field, never trusting client input) is exactly this principle applied at the middleware layer.
- **Port notes:** fhir-gql's `created_by`/`updated_by` injection in `client.py` is the right shape but single-field; if richer provenance is ever needed (who created vs. who last touched vs. on-behalf-of), extend the injected dict rather than rearchitecting — the existing `inject_audit` opt-out flag generalizes fine.
- **Priority:** Low — current fhir-gql behavior already matches the "server, not client, controls audit identity" principle.

### FHIR quota / rate-limited writes (`recordFhirQuota`)
- **What it does:** Charges a per-operation "point cost" (read=1, write=N, search=N, history=N) against a per-project rate limiter before allowing the operation, with softened enforcement (delay instead of reject) for async/background contexts.
- **Source files:** `repo.ts` — `recordFhirQuota()`, `FhirQuotaCost` (imported from `./fhirquota`, not read in full but referenced).
- **Belongs in:** `fhir-gql (middleware/orchestration)` — directly relevant, since fhir-gql explicitly owns rate limiting.
- **Correction:** fhir-gql already has a generic request-level rate limiter — `app/middleware/rate_limit.py` (`RateLimitMiddleware`, wired in `app/main.py`), a Redis-backed sliding-window limiter (sorted-set timestamps, O(log N) per request) with an in-process fallback if Redis is unreachable, keyed per-user (JWT `sub`) or per-IP, with separate `RATE_LIMIT_READ`/`RATE_LIMIT_WRITE` thresholds per `RATE_LIMIT_WINDOW` seconds (`app/config.py`). This is a flat two-tier (read vs. write) limiter, not cost-weighted — the real gap versus Medplum's `recordFhirQuota` is (1) no *per-operation point cost* (a `_history` or wide search costs the same as a single `GET`), and (2) no *per-tenant* (`org_id`) key — today's limiter buckets by user/IP only, not by organization, so one heavy org can't be isolated from another sharing infrastructure.
- **Port notes:** Don't build a new rate limiter — extend the existing `RateLimitMiddleware`. Two incremental improvements, each independent: (a) add an `org_id`-keyed bucket alongside the existing per-user bucket for tenant-level isolation, sourced from `AuthUser.org_id` (already resolved by `get_current_user`); (b) replace the flat read/write split with a per-route "cost" (e.g. a small dict of `path → point cost` or a decorator on router functions) consumed from the same Redis sorted set, mirroring Medplum's cost differentiation without changing the underlying algorithm.
- **Priority:** Medium — the "fhir-gql owns rate limiting" responsibility is already discharged; what remains (cost-weighting, per-tenant keys) is a refinement, not a missing capability.

### Per-project resource cap
- **What it does:** Enforces a hard ceiling on total resource count per project/tenant (e.g. "free tier: 10,000 resources"), backed by a Redis counter seeded from an actual DB count on first use, with graceful "give back the point" handling when a create fails after the point was pre-consumed.
- **Source files:** `packages/server/src/fhir/resource-cap.ts` — `ResourceCap` class (`consume()`, `created()`, `deleted()`, lazy `init()` via `RateLimiterRedis`).
- **How it works:** Uses `rate-limiter-flexible`'s `RateLimiterRedis` with a 24h "duration" window but the semantics are actually a persistent quota, not a rolling rate — `points` is the hard cap, and `consume`/`reward` move a running counter up/down as resources are created/deleted. On first use, seeds the counter with `SELECT COUNT(*)` unioned across every countable resource table.
- **Belongs in:** `fhir-gql (middleware/orchestration)` in spirit (tenant/plan enforcement is an orchestration concern), but the counter must ultimately be seeded from fhir-server's actual row counts (fhir-gql doesn't own Postgres).
- **Port notes:** If/when fhir-gql needs multi-tenant plan limits (e.g. cap Patients per `org_id`), mirror this shape: a Redis-backed counter, seeded once via a `GET /patients?org_id=X&limit=0` (count-only) call to fhir-server, incremented on successful `create`, decremented on `delete`, checked before every create. Needs a downstream "count" endpoint if one doesn't exist yet.
- **Priority:** Low today (no evidence of tenant plan limits in scope), Medium if multi-tenant billing/plans are on the roadmap.

### Transaction management (`withTransaction`, pre/post-commit hooks)
- **What it does:** Wraps a sequence of repository operations in a single Postgres transaction (optionally `SERIALIZABLE`), with `preCommit`/`postCommit` hooks for side effects that must happen exactly-once relative to the commit (audit logging, cache writes, background jobs, sleeps for quota smoothing).
- **Source files:** `repo.ts` — `withTransaction()`, `ensureInTransaction()`, `preCommit()`/`postCommit()`; `repository/repository-connection.ts` (referenced, not read in full).
- **How it works:** `postCommit` callbacks are queued and only fire after the DB transaction actually commits (critical for not sending "resource created" audit events / webhooks for a transaction that later rolls back). `preCommit` runs inside the transaction, before commit (used by `checkReferencesOnWrite`). Nested repository operations reuse the same `PoolClient` via `ConnectionScope` so writes within one HTTP request/transaction are atomic.
- **Belongs in:** `fhir-server (data layer/persistence)` exclusively — this requires an actual DB transaction, which fhir-gql cannot participate in (it talks to fhir-server over HTTP, not a shared DB connection).
- **Port notes:** fhir-server's existing `POST /patients/full` (atomic create of Patient + all sub-resources per `patient.py`'s docstring: "wraps every insert in a single DB transaction") already implements exactly this pattern at the endpoint fhir-gql needs it for. If fhir-gql ever needs a *cross-resource-type* atomic operation (e.g. create Patient + linked Coverage in one transaction), the transaction must live entirely inside fhir-server as a new composite endpoint — fhir-gql cannot fake atomicity across two separate HTTP calls.
- **Priority:** Low for fhir-gql (nothing to do); note for fhir-server if/when new atomic composite endpoints are needed.

### System repository / privilege elevation
- **What it does:** Provides an internal, fully-privileged "system" identity (`author: {reference: 'system'}`, `superAdmin: true`) for operations that must bypass the current user's access policy (e.g. resolving a `Project.owner` reference the user wouldn't otherwise be able to see).
- **Source files:** `repo.ts` — `Repository.getSystemRepo()`, `SystemRepository` class, `getGlobalSystemRepo()`, `getShardSystemRepo()`, `getProjectSystemRepo()`.
- **How it works:** A `SystemRepository` is a `Repository` constructed with a fixed, non-configurable context (`superAdmin: true`, no `accessPolicy`). Reuses the caller's DB connection/transaction scope when one exists, so elevation doesn't require a second connection or break transactional consistency. Explicitly documented preference order for *which* system-repo getter to use, to avoid accidentally using the wrong shard/project scope.
- **Belongs in:** `fhir-server (data layer/persistence)` — access-policy bypass only makes sense where access policies are enforced, i.e. at the data layer.
- **Port notes:** fhir-gql has no analogous concept today because it has no per-resource access policy to bypass (RBAC is a flat permission-string check, not compartment-based). If fhir-gql later needs a "service account" identity for internal orchestration calls (e.g. a background job that needs to read across all orgs), model it as a distinct `AuthUser` with an elevated `permissions` list rather than inventing a parallel bypass mechanism — keep the single `check_permission()` gate as the only authority.
- **Priority:** Low — not applicable until fhir-gql grows a richer authorization model.

---

## 2. Delete, expunge, purge, reindex

### Soft delete
- **What it does:** Marks a resource as deleted (tombstone row + history entry) without physically removing it, so `GET` returns `410 Gone` and history is preserved.
- **Source files:** `repo.ts` — `Repository.deleteResource()`, `buildDeletedResourceRow()` (from `./repository/row-builder`, referenced).
- **How it works:** Checks `canPerformInteraction(DELETE, ...)`, runs `preCommitValidation(..., 'delete')` (bot hooks can veto), then inside a transaction: upserts a tombstone row (`InsertQuery(...).mergeOnConflict()`) with `deleted=true` and no `content`, appends a corresponding history row, and purges lookup-table entries (`deleteFromLookupTables`) so the deleted resource no longer matches any search. Also cleans up WebSocket subscription bookkeeping when deleting a `Subscription`.
- **Belongs in:** `fhir-server (data layer/persistence)`.
- **Port notes:** fhir-gql's `PatientClient.delete()` calls a plain `DELETE /patients/{id}` and treats a `204` as final — the docstring says it "permanently removes" the Patient (hard delete, cascading to children). If soft-delete / undelete / `410 Gone` semantics are wanted later (e.g. for compliance "right to be forgotten" vs. "recoverable delete" distinctions), that's entirely a fhir-server schema change (add a `deleted_at`/`deleted` column, filter it out of default queries) — fhir-gql's client code wouldn't need to change at all since it already just forwards the DELETE and 204/404 responses.
- **Priority:** Low — current hard-delete behavior is a reasonable, simpler default; only revisit if compliance/audit requirements demand recoverability.

### Permanent expunge
- **What it does:** Truly, irreversibly deletes a resource and all of its history — a super-admin-only "hard delete after soft delete" operation, batched for up to 10,000 IDs at once, executed inside a `SERIALIZABLE` transaction.
- **Source files:** `repo.ts` — `expungeResource()`, `expungeResources()`.
- **Belongs in:** `fhir-server (data layer/persistence)`.
- **Port notes:** Not applicable to fhir-gql — it has no soft-delete tier to expunge from. If fhir-server ever adds soft delete, expunge should be a superadmin-only downstream operation gated by an fhir-gql RBAC permission like `patient:expunge`, forwarded exactly like `delete()` is today.
- **Priority:** Low.

### Time-based purge
- **What it does:** Bulk-deletes all resources (and lookup-table entries) of a given type last updated before a cutoff date — a retention/compliance sweep, not a per-request operation.
- **Source files:** `repo.ts` — `purgeResources()`.
- **Belongs in:** `fhir-server (data layer/persistence)`, run as an offline/admin job, not a request-path feature.
- **Port notes:** If a retention policy is ever required (e.g. "delete Patients inactive for 7 years"), this is a downstream batch job/cron, not something fhir-gql should orchestrate per-request. fhir-gql could expose an admin-only trigger endpoint that calls a downstream `/admin/purge` operation, mirroring how it forwards everything else.
- **Priority:** Low.

### Reindex
- **What it does:** Rebuilds a resource's derived search-index columns/lookup-table rows and `meta.compartment` without changing its content or creating a new version — used after search-parameter definitions change or after a bug in indexing is fixed.
- **Source files:** `repo.ts` — `reindexResource()`, `reindexResources()` (batched form, used by bulk reindex jobs).
- **Belongs in:** `fhir-server (data layer/persistence)` exclusively — this is entirely about search-index bookkeeping, which fhir-gql has no visibility into.
- **Port notes:** Not applicable to fhir-gql. Worth knowing about only as prior art if fhir-server ever needs a "rebuild derived Patient search columns after a migration" maintenance operation.
- **Priority:** Low.

---

## 3. Search engine

This is the largest cluster and the one fhir-gql needs the most *conceptual* familiarity with, even though it implements none of the SQL. fhir-gql's Patient `list()` (`app/routers/patient.py` / `patient_service.py`) already exposes a small, hand-built subset of this surface (`family_name`, `given_name`, `gender`, `active`, `user_id`, `org_id`, `limit`, `offset`) as fixed keyword filters — Medplum's model is a generic, spec-driven search-parameter framework that could inform how fhir-gql's filter surface (and GraphQL args) scale as more resources are added.

### Search parameter → SQL storage strategy selection
- **What it does:** For every `(resourceType, searchParameter)` pair, decides *how* that parameter is indexed/queried: a plain column, a dedicated array-of-hashed-tokens column, a Postgres range-type column, or a separate join/lookup table — and caches the decision in a process-global registry.
- **Source files:** `searchparameter.ts` — `getSearchParameterImplementation()`, `buildSearchParameterImplementation()`, `SearchStrategies` (`COLUMN`, `LOOKUP_TABLE`, `TOKEN_COLUMN`, `RANGE_COLUMN`).
- **How it works:** `date`/`number`/`quantity` params always go to `range-column` (Postgres `tstzrange`/`numrange`/`daterange`); `token`-typed params go to `token-column` unless the element type doesn't need `system|value` semantics (then plain `column`); certain element types (`HumanName`, `Address`, references, codings) go to dedicated `lookup-table`s (`AddressTable`, `HumanNameTable`, `ReferenceTable`, `CodingTable`, `ConceptMappingTable`). An explicit allow/deny-list (`DedicatedTokenColumnsOverridesByResourceTypeAndCode`) hand-tunes which rarely-used token params get dedicated columns vs. share one big array column, trading index size against query specificity.
- **Belongs in:** `fhir-server (data layer/persistence)` entirely.
- **Port notes:** No SQL to port, but the *taxonomy* (column vs. token vs. range vs. join-table) is a useful mental model if fhir-gql's team ever needs to reason about which Patient filters are cheap (indexed equality) vs. expensive (LIKE scans) when deciding what to expose as GraphQL filter args.
- **Priority:** Low (informational only).

### Core search execution pipeline
- **What it does:** Turns a parsed `SearchRequest` into a `Bundle` of matching resources plus pagination links and (optionally) a total count.
- **Source files:** `search.ts` — `searchImpl()`, `getSelectQueryForSearch()`, `getSearchEntries()`.
- **How it works:** Validates resource type + access (`validateSearchResourceTypes`), clamps `count`/`offset` to server maximums, builds a `SelectQuery` (`getBaseSelectQuery` → per-type `getBaseSelectQueryForResourceType`) with `id`/`lastUpdated`/`content` columns, applies the soft-delete filter unless `_deleted` was explicitly searched, applies security filters (project + access policy), applies the parsed search filters, requests `count + 1` rows (to detect "has more" without a second query), executes against a **read replica** (`DatabaseMode.READER`), and only pops the extra row into `nextResource` if it was actually returned.
- **Belongs in:** `fhir-server (data layer/persistence)`.
- **Port notes:** fhir-gql's `list()` already does the equivalent at a much coarser level — it forwards `limit`/`offset` and gets back `{data: [...], total: N}` per `patient_service.list()`. The "request one extra row to detect has-more without COUNT(*)" trick (`limitModifier`, default 1) is a good pattern if fhir-server's pagination is ever a perf bottleneck; not urgent.
- **Priority:** Low for fhir-gql; this is squarely fhir-server's implementation detail.

### Search-by-reference batch optimization
- **What it does:** Given N reference values, returns all matching resources for all N in a single SQL round-trip via `UNION ALL`, instead of N separate queries — purpose-built to make GraphQL nested-list resolution efficient.
- **Source files:** `search.ts` — `searchByReferenceImpl()`; `sql.ts` — `UnionAllBuilder`.
- **How it works:** Builds one parameterized `SelectQuery` template with a placeholder reference-equality condition and a literal `ref` column, then re-executes the *same* query object N times with the parameter/column swapped in place (`cond.parameter = refValue`), wrapping all N in `UNION ALL` and running exactly one Postgres round trip. Results are then bucketed back into a `Record<string, Resource[]>` keyed by the original reference string.
- **Belongs in:** `fhir-server (data layer/persistence)` for the SQL; `fhir-gql (middleware/orchestration)` for the *pattern* — this is precisely the N+1 problem fhir-gql's GraphQL layer will hit resolving e.g. "all Observations for these 50 Patients."
- **Port notes:** fhir-gql cannot do a SQL `UNION ALL` (no DB access), but it can and should do the HTTP equivalent: batch multiple reference lookups into a single downstream call if/when fhir-server exposes a bulk-fetch endpoint (`POST /patients/batch-get {ids: [...]}` or `GET /patients?id=IN(...)`), wired through a Strawberry `DataLoader`. Without a downstream bulk endpoint, the best fhir-gql can do today is `asyncio.gather()` over parallel single-item requests — much cheaper to build, worth doing as an interim step.
- **Priority:** Medium — becomes important as soon as GraphQL resolvers fan out across resources (e.g. resolving Patient → Organization, or a list of Patients each resolving their own `generalPractitioner`).

### Pagination: offset vs. cursor
- **What it does:** Supports classic `offset`-based pagination (simple but O(n) under the hood and unstable under concurrent writes) and a more efficient `_lastUpdated`-based cursor for the common "always sort by newest, page size ≥ 20" case, including v1 (legacy) and v2 cursor string formats and exclusion of duplicate-timestamp rows across page boundaries.
- **Source files:** `search.ts` — `canUseCursorLinks()`, `buildSearchLinksWithCursor()`, `buildSearchLinksWithOffset()`, `parseCursor()`/`parseV1Cursor()`/`parseV2Cursor()`/`formatCursor()`, `minCursorBasedSearchPageSize`.
- **How it works:** Cursor mode requires: no `offset`, `count >= 20`, exactly one sort rule on ascending `_lastUpdated`. The cursor encodes `{version, nextInstant, excludedIds}`; `excludedIds` handles resources sharing the exact same `lastUpdated` timestamp across a page boundary (otherwise they'd be silently skipped or duplicated). A `serverError` is thrown if the cursor would fail to make forward progress (all remaining resources share one timestamp).
- **Belongs in:** `fhir-server (data layer/persistence)`.
- **Port notes:** fhir-gql's `list()` is pure `limit`/`offset` today (`ListPatientsSchema`). That's fine for a Patient table of modest size; if pagination stability under concurrent writes or deep-page performance becomes an issue, fhir-server should adopt an equivalent `updated_at`-based cursor and fhir-gql just needs to pass an opaque `cursor` string through instead of `offset` — no change to the orchestration logic, since `list()` already just forwards whatever kwargs it's given.
- **Priority:** Low today; revisit if Patient table grows large enough for deep-offset queries to matter.

### Total count strategies (estimate vs. accurate)
- **What it does:** Avoids paying for an expensive `COUNT(*)` on every search by defaulting to Postgres's query-planner row estimate (via `EXPLAIN`), only falling back to a real `COUNT(*)` when the estimate is below a configurable threshold (default: cheap enough to be worth confirming) or the caller explicitly asked for `_total=accurate`.
- **Source files:** `search.ts` — `getCount()`, `getEstimateCount()` (parses `rows=(\d+)` out of the `EXPLAIN` plan text), `getAccurateCount()`, `clampEstimateCount()`.
- **How it works:** A clever short-circuit: if the actual page of results came back with fewer rows than requested (and no cursor is in play), the exact total is trivially `offset + rowCount` — no extra query needed at all. `clampEstimateCount` bounds the planner's estimate between the observed minimum and maximum possible true count given the returned row count, so the estimate is never wildly inconsistent with what the user actually saw.
- **Belongs in:** `fhir-server (data layer/persistence)`.
- **Port notes:** fhir-gql's `{data, total}` response shape (per `patient_service.list()`) implies fhir-server already computes a total per request; whether it's exact or estimated is invisible to fhir-gql and doesn't need to be — this is worth flagging to the fhir-server team only if `COUNT(*)` on the Patient table ever becomes a measured bottleneck.
- **Priority:** Low (fhir-server implementation detail, invisible to fhir-gql's contract).

### `_include` / `_revinclude` with `:iterate`
- **What it does:** Fetches related resources referenced by (or referencing) the primary search results and folds them into the same `Bundle`, optionally following chains of relationships (`:iterate`) up to a depth/result-count circuit breaker.
- **Source files:** `search.ts` — `getExtraEntries()`, `getSearchIncludeEntries()`, `getSearchRevIncludeEntries()`.
- **How it works:** BFS-style loop: starts with the primary result set as `base`, on each iteration evaluates every `_include`/`_revinclude` param's FHIRPath expression against `base` to collect reference targets, batch-resolves them, adds newly-seen resources to the bundle (deduped via a `Set<string>` of `"Type/id"`), and sets `base` to the newly-fetched resources for the next iteration — but only continues past the first pass for params explicitly marked `:iterate`. Hard caps: `depth >= 5` or `entries.length > maxSearchResults` throws rather than looping forever.
- **Belongs in:** `fhir-server (data layer/persistence)` for the SQL side; `fhir-gql (middleware/orchestration)` conceptually, because GraphQL's whole value proposition is letting clients ask for related resources in one query — this is the REST-Bundle equivalent of what a GraphQL resolver graph does natively.
- **Port notes:** fhir-gql's GraphQL layer (Strawberry) achieves the *same end result* structurally via field resolvers rather than a flat `_include` list — that's actually a nicer model for a GraphQL API and doesn't need porting. Where the Medplum pattern *is* relevant: the circuit breakers (depth limit, result-count limit) are a good safety pattern to replicate in Strawberry via `graphqlMaxDepth` / query-complexity limits (Strawberry supports a `QueryDepthLimiter`/complexity extension) so a malicious or naive deeply-nested Patient→Organization→Patient... query can't blow up the downstream fhir-server with fan-out calls.
- **Priority:** Medium — add GraphQL depth/complexity limiting before adding a second cross-referencing resource type.

### `_elements` / `_summary`
- **What it does:** Lets the client ask for a subset of a resource's fields (`_elements=name,birthDate`) or a predefined summary view (`_summary=true|text|data`), server-side, to reduce payload size.
- **Source files:** `search.ts` — `removeResourceFields()` → `subsetResource()` (from `@medplum/core`, not read in full).
- **How it works:** `_elements` always keeps `schema.mandatoryProperties` plus the requested fields. `_summary=true` keeps only `schema.summaryProperties` (spec-flagged summary elements); `_summary=text` keeps only the narrative `text` plus mandatory fields; `_summary=data` strips only `text`, keeping everything else.
- **Belongs in:** `fhir-server (data layer/persistence)` for FHIR REST; `fhir-gql (middleware/orchestration)` — **GraphQL already does this natively and better**, since a GraphQL query only ever requests the fields the client asks for.
- **Port notes:** No work needed for fhir-gql's GraphQL surface — field selection is inherent to GraphQL. If fhir-gql's *REST* surface wants an equivalent (e.g. a lightweight `?fields=` query param on `GET /patients/{id}` to avoid over-fetching all sub-resource arrays), that's a small, self-contained addition to `patient_service.get_by_id()`/`PatientClient.get_by_id()` — filter the response dict server-side after fetching (or forward the param downstream if fhir-server supports it).
- **Priority:** Low — GraphQL's native field selection already covers the main use case.

### Chained search parameters (`subject.name=Smith`, `_has:Observation:patient:code=...`)
- **What it does:** Lets a search on resource A filter by a property of a *related* resource B, either forward (`Observation?subject.name=Smith` — find Observations whose subject Patient is named Smith) or reverse (`Patient?_has:Observation:patient:code=1234-5` — find Patients that have an Observation with a given code).
- **Source files:** `search.ts` — `parseChainedParameter()`, `buildChainedSearch()`, `buildChainedSearchUsingReferenceTable()`, `parseChainLink()`, `parseReverseChainLink()`, `splitChainedSearch()`.
- **How it works:** Parses the dotted/`_has:`-prefixed chain into a list of `ChainedSearchLink`s (each with origin type, target type, code, direction). Builds a correlated `EXISTS(...)` subquery that joins through a `{ResourceType}_References` lookup table (populated at write time by the `ReferenceTable` lookup table) for each hop, or through the target's `url` column for canonical (profile/ValueSet) references. Limited to 3 chain links max to bound query complexity. A special case rewrites single-link `param._id=X` into a simple `param=Type/X` equality to skip the join entirely.
- **Belongs in:** `fhir-server (data layer/persistence)` exclusively — needs a reference-lookup table and correlated subqueries.
- **Port notes:** Not portable to fhir-gql (no SQL). Structurally, this *is* what a GraphQL nested-field query naturally expresses (`patient { observations(code: "1234-5") { ... } }`) — again, GraphQL's native shape supersedes the REST chained-search workaround. No fhir-gql action needed unless a REST client explicitly needs chained-search query params, which is unlikely given fhir-gql's proxy role.
- **Priority:** Low.

### Advanced `_filter` parameter (boolean expression grammar)
- **What it does:** Implements the FHIR `_filter` search parameter — a mini boolean-expression language (`and`/`or`/`not`, comparisons) layered on top of ordinary search parameters, for queries that can't be expressed as a flat list of ANDed filters.
- **Source files:** `search.ts` — `buildFilterParameterExpression()`, `buildFilterParameterConnective()`, `buildFilterParameterComparison()`; parsing delegated to `parseFilterParameter` from `@medplum/core` (not read in full).
- **Belongs in:** `fhir-server (data layer/persistence)`.
- **Port notes:** Not relevant to fhir-gql's current filter surface (`family_name`, `given_name`, `gender`, `active`, etc. are simple ANDed equality/contains filters). If arbitrary boolean filter combinations are ever needed, GraphQL's typed input objects (e.g. a `PatientFilter` input with `AND`/`OR`/`NOT` fields) are the idiomatic way to expose this — don't try to reproduce FHIR's `_filter` string grammar in fhir-gql.
- **Priority:** Low.

### Special (underscore-prefixed) search parameters
- **What it does:** Handles the FHIR spec's reserved search parameters that aren't ordinary `SearchParameter` resources: `_id`, `_lastUpdated`, `_deleted`, `_project` (Medplum extension), `_compartment`.
- **Source files:** `search.ts` — `trySpecialSearchParameter()`.
- **Belongs in:** `fhir-server (data layer/persistence)`.
- **Port notes:** fhir-gql's Patient filters already have informal equivalents worth being consistent with as more resources are added: `active` ≈ a domain field (fine as-is), and `org_id`/`user_id` filters are fhir-gql's bespoke version of `_compartment`/tenant scoping. No immediate action, but when a second resource is added, standardize on consistent filter-naming conventions (e.g. always `updated_after`/`updated_before` rather than ad hoc names) so the GraphQL schema stays coherent.
- **Priority:** Low.

### String, token, reference, date, and quantity filter compilation
- **What it does:** Type-specific translation of a FHIR search filter (operator + value) into a SQL condition — e.g. `string` → case-insensitive `LIKE` with `contains`/`exact`/`starts-with` modifiers; `token` → exact match against `system`/`value` pairs with an `:identifier` derived-parameter mode; `reference` → equality/array-overlap against a `Type/id` string, with single-target-type inference to accept bare IDs; `date`/`quantity` → range/comparison operators including a fuzzy `:approximately` (±10%).
- **Source files:** `search.ts` — `buildStringSearchFilter()`/`buildStringFilterExpression()`, `buildTokenSearchFilter()`, `buildReferenceSearchFilter()`, `buildDateSearchFilter()`, `buildQuantitySearchFilter()`, `escapeLikeString()`.
- **How it works:** String search escapes user-controlled `%`/`_`/`\` before building a `LOWER(column) LIKE 'pattern'` condition — a SQL-injection-safe pattern worth noting generally. Reference search has a subtle backward-compatibility rule: bare (slash-less) values on the historically-overloaded `subject`/`patient` columns default to `Patient/`, while all other single-target reference params infer their type from the search parameter's element definition (`impl.singleTargetType`).
- **Belongs in:** `fhir-server (data layer/persistence)` entirely.
- **Port notes:** No SQL to port. The one transferable idea: fhir-gql's `family_name`/`given_name` filters are documented as "partial, case-insensitive matches" (per `patient_service.list()` docstring) — worth double-checking fhir-server actually escapes LIKE metacharacters in the user's input the way Medplum's `escapeLikeString()` does, since an unescaped `%`/`_` in a name filter is a (minor) correctness bug, not a security one, but still worth a quick downstream check.
- **Priority:** Low (informational — flag to fhir-server team to verify LIKE-escaping).

### Sort (`_sort`) across storage strategies
- **What it does:** Adds `ORDER BY` clauses that correctly target whichever physical column backs a given search parameter, whether it's a plain column, a token-column's precomputed sort column, a range-column's precomputed sort column, or a lookup table's own ordering logic.
- **Source files:** `search.ts` — `addSortRules()`, `addOrderByClause()`; `token-column.ts` — `addTokenColumnsOrderBy()`; `range-column.ts` — `addRangeColumnsOrderBy()`.
- **How it works:** Token/range columns store arrays (a resource can have multiple names/dates for one search param), so sorting can't just `ORDER BY` the array column — instead a separate scalar `__xSort` column is precomputed at write time holding the "alphabetically/numerically first" value, and sort targets that instead.
- **Belongs in:** `fhir-server (data layer/persistence)`.
- **Port notes:** Not applicable to fhir-gql directly. If fhir-gql exposes `sort` as a GraphQL/REST param, it should be a closed enum of known-sortable fields (not arbitrary passthrough) so it can validate before forwarding — this is a general API-design point, not something specific to port from Medplum.
- **Priority:** Low.

### Token indexing model (hashed system\|value arrays)
- **What it does:** Encodes every FHIR token-typed value (`Identifier`, `CodeableConcept`, `Coding`, `ContactPoint`, `code`) into a UUIDv5-hashed array column supporting exact match on `code`, `system|`, and `system|code` forms simultaneously, plus a separate free-text array for `:contains`/`:text` substring search — all searchable via GIN-indexable array operators instead of per-value join tables.
- **Source files:** `tokens.ts` — `buildTokensForSearchParameter()`, `getTokenIndexType()`; `token-column.ts` — `buildTokenColumns()`, `hashTokenColumnValue()` (UUIDv5 over a `NIL` namespace — deterministic, not for security, purely to make big string keys compact and indexable), `buildTokenColumnsSearchFilter()`, `buildTokenColumnsWhereConditionTextAndContains()` (regex over a delimiter-joined string via a custom immutable `token_array_to_text` SQL function so the expression is index-expression-eligible).
- **How it works:** For each token value, up to four hashed variants are added to the array: `code` alone, `system|`, `system|code`, and `|code` (explicit-no-system) — so an equality search on any of those forms is a single `ARRAY_OVERLAPS` check. Search parameters can share one big `__sharedTokens` column (cheaper index, less selective) or get a `hasDedicatedColumns` per-parameter column (pricier index, more selective), tuned per-resource-type via an explicit allow/deny list based on real-world usage frequency.
- **Belongs in:** `fhir-server (data layer/persistence)` exclusively.
- **Port notes:** Pure database-indexing strategy; nothing to port. Worth flagging as *prior art* if fhir-server's Patient identifier/name search ever needs to scale past simple `LIKE`/equality — this hashed-array-column technique is a proven pattern for token search without a full join-table-per-search-parameter design.
- **Priority:** Low (informational).

### Range-column indexing model (dates, numbers, quantities)
- **What it does:** Stores date/number/quantity search parameters as native Postgres range types (`tstzrange`, `numrange`, `daterange`) so overlap/containment queries use GiST-indexable range operators instead of separate `low`/`high` column pairs.
- **Source files:** `range-column.ts` — `buildRangeColumns()`, `extractDateTimeParameter()`, `parseDateTimeToRange()` (implements FHIR's date-precision-implies-range semantics — a bare `"2024"` means the range `[2024-01-01, 2025-01-01)`), `buildRangeColumnsSearchFilter()`.
- **Belongs in:** `fhir-server (data layer/persistence)` exclusively.
- **Port notes:** Nothing to port; the one conceptually useful bit for fhir-gql is the **date-precision-as-range** rule itself (a date search value's precision determines the implicit range it matches) — worth knowing if fhir-gql ever validates/normalizes date filter inputs before forwarding them, so a `birthdate=2024` filter behaves predictably rather than being silently treated as exact-string-match by whatever's downstream.
- **Priority:** Low (informational).

---

## 4. Access control

### Compartment-based, criteria-driven Access Policies
- **What it does:** A per-user, per-resource-type authorization model far richer than a flat permission string: for each resource type, a policy can restrict access to a `compartment` (e.g. "only resources in Patient/123's compartment"), a FHIR search `criteria` string (e.g. `Patient?active=true`), specific `interaction`s (read/write/search/etc.), `readonlyFields`, and `hiddenFields` — all with `%variable` substitution (`%patient`, `%profile`) so one policy template can be parameterized per user via `ProjectMembership.access[].parameter`.
- **Source files:** `accesspolicy.ts` — `getRepoForLogin()`, `getAccessPolicyForLogin()`, `buildAccessPolicy()`, `buildAccessPolicyResources()` (variable substitution via string `replaceAll`), `applyProjectAdminAccessPolicy()`, `addDefaultResourceTypes()`; enforced at query time in `repo.ts` — `addAccessPolicyFilters()`, `canPerformInteraction()`, `supportsInteraction()`, `removeHiddenFields()`, `restoreReadonlyFields()`, `isResourceWriteable()` (FHIRPath `writeConstraint` invariants evaluated against `%before`/`%after`).
- **How it works:** Access policies compose as a **disjunction** (`OR`) of per-resource-type rules — if any applicable policy resource entry's `criteria` matches, access is granted; the criteria itself is compiled into a search-query `Expression` and added as a `WHERE` predicate (via `buildSearchExpression`), so authorization is enforced *inside the same SQL query* as the data fetch, not as a separate check-then-fetch (avoiding TOCTOU gaps and extra round trips). Field-level restriction (`hiddenFields`/`readonlyFields`) is applied after fetch (strip on read) and before write (restore server-controlled values, discarding client attempts to change them).
- **Belongs in:** `fhir-server (data layer/persistence)` for enforcement (it must be baked into the SQL `WHERE` clause to be trustworthy); **fhir-gql should still care** because its current model — a flat `"resource:action"` JWT-claim check with no compartment/criteria/field-level concept — is qualitatively simpler and can't express "user can only see Patients in their own org" as anything other than a service-layer manual filter (which `get_me()` does today, by hand, for exactly one case).
- **Port notes:** This is the single biggest conceptual gap between Medplum's model and fhir-gql's current RBAC (`app/auth/rbac.py`). Concretely: fhir-gql's `check_permission()` can express "can this user call `patient:read` at all" but not "can this user read *this specific* Patient" or "can this user only see Patients where `org_id == their org`" beyond the one-off `get_me()` case. If fine-grained/compartment access control is needed beyond org-scoping already baked into `list()`'s `org_id` filter, two options: (a) have fhir-server enforce it (pass `org_id`/`user_id` on every downstream call — already partially done), or (b) if fhir-server can't enforce arbitrary criteria, fhir-gql would need to inject filter parameters into every outbound request based on the caller's scope — a much weaker, request-shaping-only version of Medplum's model (never a substitute for real DB-level enforcement, since a bug in the injection logic would be a data leak).
- **Priority:** High — this is a real, present-day architectural gap (not a hypothetical future feature): today, any user with `patient:read` can fetch **any** Patient by ID via `GET /patients/{id}` — there's no compartment check tying the resource to the caller unless the caller happens to use `/patients/me`. Recommend fhir-server enforce `org_id` (and if applicable, per-user) scoping on every Patient read/write, not just `list()`, with fhir-gql passing the caller's `org_id`/`sub` through on every call (not just `list`/`get_me`) so it can't be bypassed.

### SMART-on-FHIR scope intersection
- **What it does:** When a login carries SMART-on-FHIR OAuth scopes (`patient/*.rs`, `user/Observation.read`, etc.), narrows the user's already-computed Access Policy down to the intersection of what the scopes allow — e.g. a `patient/*.rs` scope forces every resource-type policy to be read-only and compartment-scoped to the launch-context Patient.
- **Source files:** `smart.ts` — `parseSmartScopes()`, `parseSmartScopeString()` (regex `^(patient|user|system)/(\w+|\*)\.(read|write|c?r?u?d?s?|\*)$`), `applySmartScopes()`, `intersectSmartScopes()`, `mergeAccessPolicyWithScope()`.
- **Belongs in:** `fhir-server (data layer/persistence)` / `fhir-server`'s auth layer — SMART-on-FHIR is an OAuth/launch-context protocol layered on top of the same access-policy enforcement engine described above.
- **Port notes:** Not applicable unless fhir-gql needs to support third-party SMART apps launching against it (a distinct product decision, not a refactor). fhir-gql's current JWT `permissions` claim model is a simpler, closed-ecosystem equivalent; if third-party app support is ever needed, this whole feature (SMART scope parsing + policy intersection) would need to be built fresh, likely at the fhir-gql layer since it owns auth.
- **Priority:** Low (no evidence this is in scope).

---

## 5. Transactions and batch bundles

### Batch bundle processing (`Bundle.type = batch`)
- **What it does:** Processes a list of independent REST operations (create/read/update/delete/etc.) submitted as one `Bundle`, executing each and collecting per-entry results — failures in one entry do **not** abort the others.
- **Source files:** `packages/fhir-router/src/batch.ts` — `BatchProcessor.run()`/`processBatch()`/`processBatchEntry()`.
- **How it works:** Entries are bucketed and reordered by interaction type (deletes first, then creates, updates, patches, etc. — `bucketedEntries`) rather than processed in submitted order, so that e.g. a `delete` doesn't get blocked behind an unrelated `create` that happens to appear first in the array. Errors are caught per-entry and converted into an `OperationOutcome` bundle-entry response; a `429` from any entry immediately short-circuits the remaining entries (rate-limit backpressure).
- **Belongs in:** `fhir-server (data layer/persistence)` — requires calling into the repository layer directly per entry.
- **Port notes:** fhir-gql has **no batch endpoint at all** today — every operation is a discrete REST/GraphQL call. If a client needs to do "create 5 Patients, don't fail all 5 if one fails," that's currently only achievable client-side (issue 5 separate requests). Not a high-priority gap given fhir-gql only exposes Patient today, but worth flagging as a known limitation before a second resource type with real interdependencies is added.
- **Priority:** Low today; revisit once multiple resource types make "do these N things, tolerate partial failure" a real use case.

### Transaction bundle processing (`Bundle.type = transaction`) with reference rewriting
- **What it does:** Like batch, but all-or-nothing (wrapped in a real DB transaction, rolled back on any failure) and supports `urn:uuid:` placeholder references between entries in the same bundle (e.g. create a Patient and an Observation referencing that not-yet-persisted Patient in one call), resolving and rewriting those placeholders to real `Type/id` references before each entry executes.
- **Source files:** `batch.ts` — `preprocessBundle()`, `resolveIdentity()`/`resolveCreateIdentity()`/`resolveModificationIdentity()`, `rewriteIdsInObject()`/`rewriteIdsInString()`, `isTransaction()`.
- **How it works:** Two-phase: (1) pre-scan every entry to resolve what its "identity" will be (assign a new ID for creates, resolve conditional-update/delete search criteria to a concrete ID) *before* anything is written, tracking a `placeholder → real reference` map; duplicate identities within one transaction are rejected. (2) execute entries in dependency-safe order, rewriting any `urn:uuid:...` string found anywhere in each entry's body/URL via the resolved-identity map just before that entry runs. Complexity guards: max 50 update operations per transaction, max 8 entries if the transaction requires `SERIALIZABLE` isolation (conditional create/update/delete all force serializable, since they read-then-write on a search match).
- **Belongs in:** `fhir-server (data layer/persistence)` exclusively — true cross-resource atomicity requires a shared DB transaction, which fhir-gql fundamentally cannot provide over HTTP.
- **Port notes:** This is the most significant "cannot be replicated at the middleware layer" feature in the whole review — flagging explicitly so the team doesn't try to fake it in fhir-gql. fhir-server's existing `/patients/full` atomic composite-create endpoint is the right pattern for the cases that matter today (one logical resource + its children); if a future need arises for atomic operations spanning genuinely separate top-level resource types (e.g. Patient + Coverage + Practitioner all created together, referencing each other), that must be a new fhir-server transactional endpoint, not something bolted onto fhir-gql.
- **Priority:** Low today (no cross-resource-type atomicity requirement yet); High if/when such a requirement appears — flag early since it changes fhir-server's API shape, not fhir-gql's.

### Conditional create / update / delete / patch
- **What it does:** "Create this resource unless one matching `search` already exists" (`If-None-Exist`), "update the resource matching `search`, or create it if none exists" (`If-Exist`-style upsert), and the delete/patch equivalents — all with defined behavior for zero/one/multiple matches (multiple matches → `412 Precondition Failed`).
- **Source files:** `packages/fhir-router/src/repo.ts` — `FhirRepository.conditionalCreate()`, `conditionalUpdate()`, `conditionalDelete()`, `conditionalPatch()` (all wrap their logic in `withTransaction({serializable: true})` since they read-then-write based on a search match, which needs strict isolation to avoid a race between the existence check and the write).
- **Belongs in:** `fhir-server (data layer/persistence)`.
- **Port notes:** fhir-gql's `patient_service.list()` already has a hand-rolled analogue in spirit — `get_me()` does "search for the Patient matching `user_id`/`org_id`, 404 if none" — but there's no general conditional-create ("upsert Patient by external identifier") capability. If idempotent-create-by-external-ID is ever needed (common for integrations replaying webhooks), that logic belongs downstream in fhir-server (it needs the same `SERIALIZABLE`-transaction guarantee to avoid duplicate-create races); fhir-gql would just add a thin `if_none_exist` param passthrough.
- **Priority:** Low today; Medium if an external-system integration needs idempotent upsert semantics.

---

## 6. Reference validation and rewriting

### Reference-integrity validation on write
- **What it does:** When enabled per-project (`checkReferencesOnWrite`), crawls a resource being written for every `Reference.reference` value and verifies each target actually exists (and is readable) before/after commit, collecting all broken references into one `OperationOutcome` rather than failing on the first.
- **Source files:** `references.ts` — `collectReferences()` (FHIRPath-schema-driven crawl via `crawlTypedValue`, skips `%`-prefixed contained/parameter references and `#`-prefixed internal fragment references), `validateResourceReferences()`, `ReferenceCollector`.
- **How it works:** Runs as a `preCommit` hook (inside the transaction, before commit — see Transaction management above) so a broken reference can still abort the write. A small allow-list of paths (`Project.owner`, `Project.link.project`, `ProjectMembership.user`) are validated via the system repo instead of the user's repo, since those legitimately point to resources outside the user's normal visibility.
- **Belongs in:** `fhir-server (data layer/persistence)` — needs both the schema-driven crawl and transactional guarantees.
- **Port notes:** fhir-gql has **no reference-integrity checking at all** for Patient's own internal references (e.g. `generalPractitioner` reference to a Practitioner, `link.other` reference to a related Patient/RelatedPerson) — `patient_service.add_general_practitioner()`/`add_link()` just forward whatever reference dict the client supplies. If fhir-server doesn't already validate that a `generalPractitioner`/`link` reference actually resolves, invalid references can be silently stored. Flag to fhir-server team; not something fhir-gql should try to validate itself (it would need to make an extra downstream call per reference field, and could get out of sync with what fhir-server actually persists).
- **Priority:** Medium — a real (if currently invisible) data-integrity gap once Patient's reference-typed sub-resources (`generalPractitioner`, `link`) see real usage.

### Conditional reference resolution at write time
- **What it does:** Lets a `Reference.reference` value be a *search query* instead of a literal ID (e.g. `{"reference": "Patient?identifier=12345"}`), resolved to a concrete `Type/id` at write time — useful for imports where the caller knows a natural key but not the internal UUID.
- **Source files:** `references.ts` — `replaceConditionalReferences()`, `resolveReplacementReference()`.
- **How it works:** Runs a FHIRPath crawl similar to the validation pass above; for any reference containing `?`, executes it as a search (`count: 2`, to distinguish "one match" from "multiple matches" cheaply) and replaces the reference string with the resolved resource's canonical reference, or throws `badRequest` if zero or multiple matches.
- **Belongs in:** `fhir-server (data layer/persistence)`.
- **Port notes:** Not present in fhir-gql, and not obviously needed given Patient sub-resource references (`generalPractitioner`, `link.other`) are currently plain object dicts the client is expected to supply pre-resolved. Worth revisiting only if a bulk-import use case emerges where callers only know natural keys, not internal IDs.
- **Priority:** Low.

### Attachment/Binary URL rewriting
- **What it does:** On read, rewrites any `url`/`path` property pointing at a `Binary` resource into a short-lived presigned storage URL (checking the caller can actually read that Binary first); on write, normalizes any such URL down to a canonical `Binary/{id}` reference string. Recurses through the whole resource tree, with a cache to avoid rewriting the same URL twice, and explicitly refuses to touch URLs *inside* a `Binary` resource itself (to avoid rewriting a Binary's own non-standard `url` extension into an infinite loop).
- **Source files:** `rewrite.ts` — `rewriteAttachments()`, `Rewriter` class, `normalizeBinaryUrl()` (handles three URL shapes: FHIR reference, full FHIR API URL, presigned storage URL); `response.ts` — `sendFhirResponse()` calls this on every authenticated response.
- **Belongs in:** `fhir-server (data layer/persistence)` for the storage/presigning half; `fhir-gql (middleware/orchestration)` doesn't need to reimplement rewriting, but **does** need to know this exists if/when Patient `photos` (`Attachment`) are backed by real blob storage rather than inline base64.
- **Port notes:** `patient.py`'s `photos` sub-resource (`add_photo`/`list_photos`/etc.) currently forwards whatever `PhotoCreateSchema` payload the client sends — if photos are (or become) stored as blob references rather than inline base64, whichever side owns blob storage (almost certainly fhir-server, or a dedicated storage service) needs exactly this rewrite-on-read / normalize-on-write pattern, and fhir-gql's `_handle()`/response passthrough already transparently forwards whatever URL shape comes back, so no fhir-gql change is needed unless it starts generating/signing URLs itself.
- **Priority:** Low today (unclear if Patient photos use blob storage yet); revisit if/when they do.

---

## 7. Validation

### Pre-commit bot hooks (business-rule enforcement before write)
- **What it does:** Lets a project register `Bot`-backed `Subscription`s that run *synchronously, before* a create/update/delete commits, and can veto the write (throw) or transform the resource being written (return a modified resource) — e.g. custom cross-field validation, computed-field derivation, or business rules too complex/dynamic for static schema validation.
- **Source files:** `precommit.ts` — `preCommitValidation()`, `isPreCommitSubscription()` (flagged via a specific `Subscription.extension` URL).
- **How it works:** Gated by both a server-wide config flag and a per-project setting (defense in depth against accidentally enabling arbitrary code execution on every write). Finds active `Subscription`s in the project matching the resource via `resourceMatchesSubscriptionCriteria` (the same criteria-matching engine used for async event subscriptions), executes the first matching pre-commit `Bot`, and if it returns a resource, re-runs the *access-policy permission check* against the bot's output (since the bot can change the resource in ways that would/wouldn't be permitted) before continuing.
- **Belongs in:** `fhir-server (data layer/persistence)` (needs transactional integration — the veto must be able to abort the write) — but conceptually, this is the same *kind* of hook fhir-gql's service layer already implements in a hardcoded form (the empty-PATCH-body 422 check in `_require_patch_payload()`).
- **Port notes:** fhir-gql's current validation is static, hardcoded Pydantic-schema + one custom "reject empty PATCH" rule in `patient_service.py` — there's no extensibility point for adding new business rules without a code change/deploy. That's likely fine for the current scale (single team, single resource type) and is *simpler and more auditable* than Medplum's dynamic bot-hook system, which trades flexibility for security surface (arbitrary code execution on every write is a meaningful attack surface). Not recommended to replicate the dynamic-bot mechanism; if more validation rules are needed, keep adding them as explicit Python functions in the service layer.
- **Priority:** Low — current static-validation approach is appropriate for fhir-gql's scale; do not add dynamic/pluggable validation without a clear need.

### Critical-reference delete protection
- **What it does:** Before deleting a resource, checks whether it's referenced by a `ProjectMembership`'s `profile`/`user`/`access-policy` fields (i.e. would deleting it break someone's login), and blocks the delete with a clear error if so.
- **Source files:** `precommit.ts` — `checkReferencesForDelete()`, `getCriticalReferenceTargets()`.
- **How it works:** Queries a dedicated `ProjectMembership_References` reverse-index table (populated by the general reference lookup-table indexing described earlier) filtered to just those specific reference paths, rather than a generic reference-count check across all resource types — a targeted, cheap guard against a specific class of "this delete would corrupt an unrelated but load-bearing resource" bug.
- **Belongs in:** `fhir-server (data layer/persistence)`.
- **Port notes:** The general *pattern* — "before deleting X, check whether anything load-bearing points at it" — is directly applicable to Patient: deleting a Patient should presumably be blocked (or explicitly cascade-warned) if other resources reference it (e.g. a `link.other` from another Patient, or a downstream Observation/Encounter once those exist). `patient_service.delete()`'s docstring says the fhir-server "cascades the delete to all child tables" for *Patient's own* sub-resources, which is fine for owned children — but it's unclear whether fhir-server checks for *inbound* references from other top-level resources before a hard delete. Worth confirming with the fhir-server team once a second resource type that can reference Patient exists.
- **Priority:** Low today (single resource type, no inbound cross-resource references possible yet); Medium once a second resource type can reference Patient.

### Dual-mode structural validation (JSON Schema vs. StructureDefinition/strict)
- **What it does:** Two validation tiers: a lightweight, generic JSON-Schema-based check (required properties, array-typedness, no unrecognized properties) used as the default "non-strict" mode, and a much stricter StructureDefinition/FHIRPath-invariant-based validation (`validateRepositoryResource`, in a file not in this review's scope) used when a project opts into `strictMode`.
- **Source files:** `jsonschema.ts` — `validateResourceWithJsonSchema()`, `checkProperties()`, `checkAdditionalProperties()`, `checkRequiredProperties()`; `repo.ts` references `validateRepositoryResource` (strict path) unconditionally in `updateResourceImpl` — JSON-Schema mode appears to be the legacy/fallback path, explicitly called out in the file's own comment as something Medplum wants to "eventually eliminate."
- **Belongs in:** `fhir-server (data layer/persistence)`.
- **Port notes:** fhir-gql's Pydantic schemas (`PatientCreateSchema`, `PatientPatchSchema`, etc., with `extra="forbid"` on sub-resources per `patient.py`'s docstring) already provide a validation tier that's arguably *stricter and more precise* than Medplum's JSON-Schema fallback mode (Pydantic gives per-field type validation, not just "is this an array"). No gap here — fhir-gql's request-shape validation is already solid; whatever additional FHIR-semantic validation (cardinality against a StructureDefinition, code-system membership, etc.) is desired belongs entirely to fhir-server, since that's where FHIR-spec conformance is meaningful (fhir-gql's payloads are intentionally plain snake_case JSON, not FHIR resources, until content-negotiated into `application/fhir+json`).
- **Priority:** Low — current Pydantic-based validation is already appropriate and arguably ahead of Medplum's fallback tier.

---

## 8. Capability statement, response shaping, and error format

### CapabilityStatement (`$metadata`) generation
- **What it does:** Serves a spec-required `GET /metadata` endpoint describing exactly what the server supports: every resource type, which interactions (read/search/create/etc.) each supports, which search parameters are registered per type, supported profiles, and security/auth endpoint URLs — generated dynamically from the server's own internal schema/search-parameter registry rather than hand-maintained.
- **Source files:** `metadata.ts` — `getCapabilityStatement()`, `buildCapabilityStatement()`, `buildRest()`, `buildSecurity()`, `buildResourceTypes()`, `buildSearchParameters()`.
- **Belongs in:** `fhir-server (data layer/persistence)` if strict FHIR REST conformance is a goal for the downstream server; `fhir-gql (middleware/orchestration)` if fhir-gql itself ever needs to advertise its own (much smaller) capability surface — e.g. for FHIR-aware client tooling or for internal service-discovery ("what does this gateway currently expose").
- **Port notes:** fhir-gql has no `/metadata`/`/openapi`-equivalent FHIR-conformance endpoint today (FastAPI's auto-generated OpenAPI spec at `/docs` covers the REST shape but says nothing about FHIR-interaction semantics). Given fhir-gql only exposes Patient (and only a hand-picked subset of standard interactions — no `_history`, no conditional create), a full dynamic CapabilityStatement generator is overkill; if FHIR-client interoperability is ever a goal, a small **static** hand-maintained CapabilityStatement listing just what fhir-gql actually implements would be far cheaper than replicating Medplum's dynamic generation machinery, and easy to keep in sync at fhir-gql's current, deliberately small scope.
- **Priority:** Low — not needed unless third-party FHIR-client interoperability becomes a requirement.

### FHIR-spec `OperationOutcome` construction
- **What it does:** Standardizes every error/validation response into a FHIR `OperationOutcome` resource — a structured `issue[]` array with `severity`, `code`, `expression` (JSON-pointer-ish path to the offending field), and human-readable `details.text` — rather than an ad hoc error shape, so FHIR-aware clients can programmatically parse *which* field(s) failed and why.
- **Source files:** `outcomes.ts` — `invalidRequest()` (converts `express-validator` errors, including its `alternative`/nested-error shapes, into `issue[]` entries), `sendOutcome()` (also injects a distributed-tracing extension and sets the FHIR `Content-Location`/`Location` headers for accepted/redirect outcomes).
- **Belongs in:** `fhir-server (data layer/persistence)` for FHIR-conformant responses; `fhir-gql (middleware/orchestration)` — **this is a real gap**: fhir-gql's error handling (`FhirClient._handle()`) collapses every downstream error down to a single `HTTPException(status_code, detail: str)`. When a caller sets `Accept: application/fhir+json` expecting FHIR-shaped responses, they still get a plain FastAPI error body on failure, not an `OperationOutcome` — an inconsistency in the content-negotiation contract (success responses are content-negotiated; error responses currently are not).
- **Port notes:** Two options, in order of effort: (1) minimal — if fhir-server already returns a FHIR-shaped `OperationOutcome` body on error, change `_handle()` to detect `Accept: application/fhir+json` and forward the downstream body as-is (currently it only extracts `.detail` and discards the rest); (2) fuller — if fhir-server does *not* return `OperationOutcome`-shaped errors, fhir-gql's `_handle()` could synthesize a minimal one (`{resourceType: "OperationOutcome", issue: [{severity: "error", code: "invalid", details: {text: detail}}]}`) when the negotiated response format is `application/fhir+json`, using a FastAPI custom exception handler keyed on the request's `Accept` header so the shape is consistent across all resources without duplicating logic per-router.
- **Priority:** Medium — a real content-negotiation contract gap for any FHIR-aware client using the `application/fhir+json` mode, worth fixing before advertising real FHIR conformance.

### FHIR response headers (`ETag`, `Last-Modified`, `Location`, `Prefer`)
- **What it does:** Sets standard FHIR/HTTP response headers derived from the resource's meta (`ETag` from `versionId`, `Last-Modified` from `lastUpdated`, `Location` on `201 Created`), and honors the client's `Prefer` header (`return=minimal` sends no body, `return=OperationOutcome` sends just the outcome, default sends the full resource representation).
- **Source files:** `response.ts` — `sendResponseHeaders()`, `sendFhirResponse()`; `routes.ts` — the `res.json`/`res.send` interceptor implementing `Prefer` handling and pretty-printing (`_pretty=true`).
- **Belongs in:** `fhir-server (data layer/persistence)` / `fhir-gql (middleware/orchestration)` — **both**, since `Prefer` is a generically useful HTTP-transport concern fhir-gql's REST layer could adopt regardless of FHIR conformance (e.g. "don't send back the full Patient body after a PATCH if the client doesn't need it," saving bandwidth).
- **Port notes:** fhir-gql doesn't currently honor `Prefer` (every mutation returns the full updated resource per the service-layer docstrings — "Returns the full updated Patient"). Given the sub-resource endpoints already return the *entire* Patient (with all children) on every single sub-resource mutation (per `patient.py`'s docstrings for `add_name`/`patch_telecom`/etc.), this is a real, current over-fetching cost — a `Prefer: return=minimal` opt-in (skip the body, return `204`) would be a cheap, high-value addition to `FhirClient.post()`/`patch()` for callers that don't need the echoed resource.
- **Priority:** Medium — concrete, low-effort bandwidth/latency win given the current "every sub-resource write re-fetches the whole Patient" pattern.

---

## 9. Routing layer

### Path-based URL router (framework-independent)
- **What it does:** A minimal, dependency-free HTTP-method + path-segment router (not tied to Express) that scores candidate routes by how many literal (non-parameter) segments matched, so the most specific matching route wins over a more generic one — the routing primitive `FhirRouter` is built on.
- **Source files:** `packages/fhir-router/src/urlrouter.ts` — `Router<Handler, Metadata>.add()`/`.find()`, `tryMatch()` (scoring), `buildParams()`, `parseQueryString()`.
- **Belongs in:** Neither, structurally — this exists in Medplum because it needs a routing layer independent of any specific HTTP framework (it's used both inside Express and inside Medplum's Lambda/edge deployments). fhir-gql is committed to FastAPI, whose native `APIRouter` already provides equivalent (and more mature/battle-tested) path-matching, so there's no reason to build or port a parallel router.
- **Port notes:** Not applicable. fhir-gql's actual routing concern — "make sure `/patients/me` is registered before `/patients/{id}` so FastAPI doesn't try to parse `"me"` as an int" (explicitly called out in `patient.py`'s docstring) — is FastAPI's own well-known ordering rule, unrelated to this file.
- **Priority:** Low — not applicable; use FastAPI's router as-is.

### FHIR interaction-type registry and dispatch
- **What it does:** Maps each registered route to a canonical FHIR "interaction" code (`read`, `vread`, `create`, `update`, `patch`, `delete`, `search-type`, `history-instance`, `batch`, `operation`, etc.), which is then used both for CapabilityStatement generation and for batch-bundle ordering (see above).
- **Source files:** `packages/fhir-router/src/fhirrouter.ts` — `FhirRouter` constructor (registers the 14 standard REST routes with their interaction metadata), `RestInteraction` type, `handleRequest()`.
- **Belongs in:** `fhir-server (data layer/persistence)` structurally, since it's the layer that needs to distinguish e.g. "is this a conditional update (search + write) or a plain update (ID + write)" to route to the right repository method.
- **Port notes:** fhir-gql's routing is already interaction-typed *implicitly* via its RBAC actions (`patient:read`, `patient:create`, `patient:update`, `patient:delete` — see `patient.py`'s docstring: "Mutation sub-resource endpoints... use the 'update' action... Only the top-level DELETE uses 'delete'"). That's a reasonable, simpler analogue and doesn't need Medplum's more elaborate interaction-code taxonomy (which exists mainly to drive CapabilityStatement generation and batch-ordering, neither of which fhir-gql currently needs).
- **Priority:** Low.

### `FhirRepository` abstract interface + convenience methods
- **What it does:** Defines the storage-agnostic contract (`createResource`, `readResource`, `updateResource`, `search`, `withTransaction`, etc.) that any backing store must implement, plus reusable higher-level convenience methods built purely in terms of that contract (`searchOne`, `searchResources`, the four conditional-CRUD methods) — meaning conditional-create/update/delete/patch are implemented **once**, generically, and work identically whether the underlying store is Postgres (`Repository`) or an in-memory test double (`MemoryRepository`).
- **Source files:** `packages/fhir-router/src/repo.ts` — `FhirRepository` abstract class, `MemoryRepository`.
- **Belongs in:** `fhir-server (data layer/persistence)` if fhir-server's own internal architecture benefits from separating "what a repository must do" from "how Postgres does it" (useful for testability); not applicable to fhir-gql, which has no repository/storage abstraction of its own — `FhirClient` is already the single, sufficient abstraction over "how to talk to the downstream server."
- **Port notes:** The one idea worth stealing regardless of layer: `MemoryRepository` (a fully in-memory implementation of the same interface, used for fast unit tests without a real Postgres instance) is a very effective testing pattern. fhir-gql's equivalent would be a fake/mock `FhirClient` (or a `respx`/`httpx.MockTransport`-based fake HTTP layer) implementing the same interface as the real one for fast, DB-free service-layer tests — worth confirming this pattern is already in use in fhir-gql's test suite (not reviewed here) and adopting it if not.
- **Priority:** Low for production code; Medium if fhir-gql's test suite doesn't already have an equivalent fast, dependency-free test double for `FhirClient`.

---

## Summary table

| Feature | Priority | Belongs in |
|---|---|---|
| Create with server-assigned ID | Low | fhir-server |
| Read with cache-then-DB fallback | Low | fhir-server |
| Batch reference resolution (`readReferences`) | Medium | both |
| Resource history (`_history`) | Low | fhir-server |
| Optimistic concurrency (`If-Match`/`versionId`) | Medium | both |
| "Not modified" short-circuit | Low | fhir-server |
| Meta computation on write | Low | fhir-server |
| FHIR quota / rate-limited writes | **High** | fhir-gql |
| Per-project resource cap | Low | fhir-gql |
| Transaction management | Low | fhir-server |
| System repository / privilege elevation | Low | fhir-server |
| Soft delete | Low | fhir-server |
| Permanent expunge | Low | fhir-server |
| Time-based purge | Low | fhir-server |
| Reindex | Low | fhir-server |
| Search parameter storage-strategy selection | Low | fhir-server |
| Core search execution pipeline | Low | fhir-server |
| Search-by-reference batch optimization | Medium | both |
| Pagination: offset vs. cursor | Low | fhir-server |
| Total count strategies | Low | fhir-server |
| `_include`/`_revinclude` with `:iterate` | Medium | both |
| `_elements`/`_summary` | Low | both |
| Chained search parameters | Low | fhir-server |
| Advanced `_filter` parameter | Low | fhir-server |
| Special (`_id`, `_lastUpdated`, etc.) search params | Low | fhir-server |
| String/token/reference/date/quantity filter compilation | Low | fhir-server |
| Sort across storage strategies | Low | fhir-server |
| Token indexing model | Low | fhir-server |
| Range-column indexing model | Low | fhir-server |
| Compartment-based, criteria-driven Access Policies | **High** | both |
| SMART-on-FHIR scope intersection | Low | fhir-server |
| Batch bundle processing | Low | fhir-server |
| Transaction bundle processing + reference rewriting | Low (High if needed) | fhir-server |
| Conditional create/update/delete/patch | Low (Medium if upsert needed) | fhir-server |
| Reference-integrity validation on write | Medium | fhir-server |
| Conditional reference resolution at write time | Low | fhir-server |
| Attachment/Binary URL rewriting | Low | fhir-server |
| Pre-commit bot hooks | Low (do not replicate) | fhir-server |
| Critical-reference delete protection | Low (Medium later) | fhir-server |
| Dual-mode structural validation | Low | fhir-server |
| CapabilityStatement (`$metadata`) generation | Low | either |
| FHIR-spec `OperationOutcome` construction | **Medium** | fhir-gql |
| FHIR response headers (`ETag`, `Prefer`, etc.) | **Medium** | fhir-gql |
| Path-based URL router | Low | n/a (use FastAPI) |
| FHIR interaction-type registry and dispatch | Low | fhir-server |
| `FhirRepository` abstract interface + `MemoryRepository` | Low (Medium for test tooling) | n/a |

## Recommended next steps

**fhir-gql needs direct, working knowledge of** (not necessarily to implement in SQL, but to shape its own contract correctly): the search-parameter storage-strategy taxonomy and filter-compilation rules (so its GraphQL filter args and REST query params stay predictable as more resources are added), the `_include`/`_revinclude` batching problem (because GraphQL resolvers hit the identical N+1 pattern and should adopt DataLoader-style batching), the FHIR response-header/`Prefer` contract and `OperationOutcome` error shape (both are real, present-day gaps in fhir-gql's `application/fhir+json` content-negotiation mode), and — most importantly — the compartment/criteria access-policy model, because fhir-gql's current flat RBAC genuinely cannot express "this user may only see *this* Patient," which is a live authorization gap, not a hypothetical one (`GET /patients/{id}` has no ownership check today).

**Purely the downstream fhir-server's concern**, requiring no fhir-gql awareness beyond "the response shape/error code might change": everything SQL-shaped — the search-parameter → column/token/range/lookup-table compilation, chained search, `_filter`, cursor pagination internals, the token/range indexing schemes, transaction/batch-bundle mechanics, conditional CRUD, pre-commit bot hooks, soft-delete/expunge/purge/reindex, and reference-integrity validation. These can evolve freely downstream without fhir-gql's proxy layer (`FhirClient`, `PatientClient`, `PatientService`) needing structural changes, since it already treats the response as an opaque, content-negotiated payload.

**Immediate, concrete recommendations, roughly in priority order:**
1. Close the authorization gap: ensure `org_id` (and any applicable user-level) scoping is enforced on *every* Patient read/write path, not just `list()`/`get_me()` — verify this is actually enforced downstream today, since `GET /patients/{id}` currently has no visible ownership check in the reviewed code.
2. Add request-level rate limiting in fhir-gql (a Redis-backed token bucket per `org_id`/operation-cost), matching the project's stated ownership of "rate limiting" — currently unimplemented in the reviewed files.
3. Make error responses content-negotiation-aware: return `OperationOutcome`-shaped JSON when `Accept: application/fhir+json` was requested, not just a generic `{detail}` body.
4. Add a `Prefer: return=minimal` fast path to `FhirClient.post()`/`patch()` to avoid re-fetching/re-serializing the entire Patient (with all sub-resource arrays) on every single sub-resource mutation.
5. Confirm with the fhir-server team whether `If-Match`/optimistic concurrency and reference-integrity validation (for `generalPractitioner`/`link` references) already exist downstream; if not, they're worth scheduling before Patient data volume/usage grows.
