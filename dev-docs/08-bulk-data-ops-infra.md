# Bulk Data, Migrations, Job Queue & Ops Infrastructure — Medplum vs fhir-gql

This document inventories every feature found in Medplum's bulk-data, database-migration/seeding,
background-job-queue, and observability/ops subsystems, and evaluates each one against `fhir-gql`
(a Python/FastAPI middleware/orchestration layer that proxies to a separate downstream `fhir-server`
which owns PostgreSQL persistence).

**Framing note:** `fhir-gql` has no database of its own. Anything that requires direct SQL access
(schema migration, full-table reindexing, DuckDB-based warehouse export) is necessarily a
`fhir-server` concern. `fhir-gql`'s natural territory is: authenticating/authorizing the request,
orchestrating long-running operations exposed to REST/GraphQL clients (kicking off jobs on
`fhir-server` and polling/reporting status), and anything backed by its own Redis instance
(rate limiting, quotas, ephemeral key-value storage). Today `fhir-gql` only implements the `Patient`
resource, has no bulk-export, no migration tooling, and no tracing/metrics — only the structured
JSON logger in `app/core/logging.py` (a stdlib `logging.Formatter` subclass emitting one JSON object
per line, with a `get_logger(__name__)` helper).

---

## 1. Bulk Data Export & Async Jobs

### FHIR Bulk Data Export Status & Cancellation API
- **What it does:** Implements the polling/cancellation half of the HL7 [Bulk Data Access
  (`$export`)](https://hl7.org/fhir/uv/bulkdata/STU2/) spec: `GET /export/:id` returns 202 while the
  export job runs and a completed manifest (NDJSON output URLs, errors, deleted-resource list) once
  done; `DELETE /export/:id` cancels an in-flight export.
- **Source files:** `src/fhir/bulkdata.ts` — exports `bulkDataRouter` (Express `Router`); helper
  `getExportResource()` reads either an `AsyncJob` or legacy `BulkDataExport` resource;
  `extractOutputParameters()` normalizes both resource shapes into `output`/`error`/`deleted` arrays.
- **How it works:** The actual NDJSON generation (which requires scanning the resource tables) happens
  elsewhere (`operations/export.ts`, not in scope here) and is tracked via an `AsyncJob` FHIR resource.
  This router only reads/updates that resource and rewrites Binary attachment URLs to presigned S3
  URLs via `rewriteAttachments()` before returning the manifest to the client.
- **Belongs in:** Split — the export *execution* (querying Postgres, streaming NDJSON to storage) is a
  `fhir-server (data layer)` concern; the *status polling / cancellation endpoint* exposed to clients is
  naturally a `fhir-gql (middleware)` concern, mirroring how `fhir-gql` already fronts other REST/GraphQL
  operations.
- **Port notes for fhir-gql (FastAPI/Python):** If/when `fhir-gql` needs to expose `$export`, add a thin
  router (`app/routers/bulk_export.py`) that: (1) forwards the `$export` kick-off call to `fhir-server`,
  which returns a job/task identifier; (2) exposes `GET /export/{id}` and `DELETE /export/{id}` that
  proxy to the equivalent `fhir-server` endpoints, translating auth headers via the existing
  `app.auth.dependencies` JWT validation. No local job state needs to be kept in `fhir-gql` — it stays
  stateless and just relays.
- **Priority:** Low for now (single-resource project, no export use case yet). Re-evaluate to Medium once
  more resources are onboarded and a bulk-export requirement appears.

### Generic Async Job Status API
- **What it does:** A resource-agnostic long-running-operation status endpoint per the FHIR
  [async request pattern](https://hl7.org/fhir/async-bundle.html): `GET /:id/status` returns 202 with a
  `Content-Location` header while a job (`AsyncJob`) is `accepted`/`active`, or 200 with an `OK` outcome
  once it reaches a terminal state (`completed`/`error`/`cancelled`); `DELETE /:id/status` cancels it.
- **Source files:** `src/fhir/job.ts` — exports `jobRouter`; uses `AsyncJobExecutor` (defined elsewhere,
  `fhir/operations/utils/asyncjobexecutor.ts`) to compute the `Content-Location` polling URL, and
  `asyncJobCancelHandler` for cancellation.
- **How it works:** `AsyncJob` is the single FHIR resource type used to represent *any* Medplum
  background operation (export, reindex, post-deploy migration, lambda cleanup, set-accounts, etc.) —
  status transitions are written by whichever worker owns the job. This router is purely a read/cancel
  facade over that resource. Notably the status-read is explicitly exempted from rate limiting so
  clients can poll freely even after exhausting their FHIR quota.
- **Belongs in:** `fhir-gql (middleware)` for the client-facing polling facade (thin proxy, same
  reasoning as bulk export above); the `AsyncJob` resource itself and its state transitions are owned by
  `fhir-server (data layer)`.
- **Port notes for fhir-gql (FastAPI/Python):** This is the more valuable piece to copy conceptually:
  a single generic "async job" abstraction is far better than one-off polling endpoints per operation.
  If `fhir-gql` starts orchestrating multiple long-running operations (bulk export, batch patient
  imports, etc.), model a generic `GET /jobs/{id}` in FastAPI that proxies to whatever `fhir-server`
  returns for its `Task`/`AsyncJob`-equivalent resource, with a Pydantic response model
  (`app/schemas/job/response.py`) shared across operation types instead of one schema per feature.
- **Priority:** Low today, Medium once `fhir-gql` orchestrates more than one long-running operation
  (adopting a generic job-status endpoint now avoids duplicated polling code later).

### FHIR Interaction Quota (Rate Limiting by Operation Cost)
- **What it does:** A second, cost-weighted rate limiter layered on top of raw HTTP rate limiting:
  each FHIR interaction consumes "points" based on its cost (`READ=1`, `HISTORY=10`, `SEARCH=20`,
  `WRITE=100`), tracked per-user and per-project, with configurable limits pulled from
  `Project.systemSetting` / user preferences, falling back to a server default. Emits a `RateLimit`
  response header and logs when a request consumes >10% of the remaining quota.
- **Source files:** `src/fhir/fhirquota.ts` — exports `FhirQuotaConfig`, `FhirQuotaCost`,
  `getFhirQuotaConfig()`, `getActiveRateLimitKey()`, and the `FhirRateLimiter` class (`consume()`,
  `recordRead()`/`recordHistory()`/`recordSearch()`/`recordWrite()`, `attachRateLimitHeader()`,
  `block()`).
- **How it works:** Wraps `rate-limiter-flexible`'s `RateLimiterRedis` twice (once keyed by
  membership ID, once by project ID) and takes the more restrictive of the two results. An in-process
  `LRUCache` of already-blocked users (`blockedUsers`) short-circuits repeat requests during an active
  block window without round-tripping to Redis. A separate sliding-minute-bucket sorted set
  (`FHIR_RATE_LIMIT_ACTIVE_PREFIX`) tracks "active consumers" per project per minute for
  dashboards/ops visibility, written via a Redis pipeline so it doesn't block the request on failure.
- **Belongs in:** `fhir-gql (middleware)` — this is a direct extension of what `fhir-gql` already owns
  (`app/middleware/rate_limit.py`, `app/core/redis.py`). It classifies requests by HTTP verb today
  (`RATE_LIMIT_READ` vs `RATE_LIMIT_WRITE`); Medplum's model of *cost-weighted, per-operation-type*
  quotas (read/history/search/write have very different backend costs) is a natural next increment for
  the exact same middleware, and doesn't require any `fhir-server` DB access since it's driven purely
  by request classification + Redis counters.
- **Port notes for fhir-gql (FastAPI/Python):** Reuse `redis.asyncio` (already a dependency via
  `app/core/redis.py`). Port `rate-limiter-flexible`'s sliding-window algorithm using a Lua script or
  the `pyrate-limiter` / `limits` library's `RedisStorage` backend (both support atomic
  Redis-Lua windows equivalent to `RateLimiterRedis`). Add a `FHIR_QUOTA_*` block to
  `app/config.py`'s `Settings` (mirroring the existing `RATE_LIMIT_READ`/`WRITE`/`WINDOW` pattern) and a
  small `QuotaCost` enum (`READ=1, SEARCH=20, WRITE=100`, etc.) applied inside the existing
  `RateLimitMiddleware` based on the resolved route + HTTP method rather than method alone.
- **Priority:** Medium — genuinely useful defense-in-depth once more resources/write operations exist,
  and is cheap to add on top of the existing rate-limit middleware, but not urgent while only
  `Patient` reads are implemented.

---

## 2. Database Migrations & Schema Management

> Everything in this section requires direct PostgreSQL access that `fhir-gql` deliberately does not
> have. All entries below belong to `fhir-server (data layer)`; they're documented for completeness
> and because the *patterns* (phased migrations, idempotent DDL helpers) are worth knowing even if
> `fhir-gql` never owns a schema.

### Schema Diffing Migration Generator
- **What it does:** Instead of hand-written migration files, Medplum computes the *target* database
  schema programmatically from the FHIR StructureDefinitions/SearchParameters it has loaded, introspects
  the *actual* live schema via `information_schema`/`pg_catalog`, diffs the two, and emits the minimal
  set of DDL actions (`CREATE_TABLE`, `ADD_COLUMN`, `CREATE_INDEX`, `ADD_CONSTRAINT`, etc.) needed to
  reconcile them.
- **Source files:** `src/migrations/migrate.ts` — `buildTargetDefinition()`, `buildStartDefinition()`,
  `generateMigrationActions()`, `generateColumnsActions()`, `generateIndexesActions()`,
  `generateConstraintsActions()`, `getCreateTableQueries()`, `buildIndexSql()`,
  `indexDefinitionsEqual()`, `columnDefinitionsEqual()`, plus per-resource table builders
  (`buildCreateTables()`, `buildAddressTable()`, `buildHumanNameTable()`, `buildCodingTable()`, etc.).
  Type definitions in `src/migrations/types.ts` (`TableDefinition`, `ColumnDefinition`,
  `IndexDefinition`, `MigrationAction`, `PhasalMigration`). Introspection/formatting helpers in
  `src/migrations/migrate-utils.ts` (`getColumns()`, `parseIndexDefinition()`, `getFunctionDefinition()`,
  `escapeUnicode()`, `TableNameAbbreviations`/`ColumnNameAbbreviations` for index-name length limits).
- **How it works:** One resource type = up to 3 tables (`{Type}`, `{Type}_History`, `{Type}_References`)
  plus shared lookup tables (`Address`, `HumanName`, `Identifier`, `ContactPoint`, `Coding`, etc.) built
  from each resource's indexed `SearchParameter`s (`token-column`, `range-column`, `column`, or
  `lookup-table` "search strategies" each produce different column/index shapes). The diff walks target
  vs. introspected tables/columns/indexes/constraints and buckets each required change into either a
  fast **pre-deploy** action (safe to run before new app code is live, e.g. `ADD COLUMN`) or a
  **post-deploy** action (needs new code first, or is slow/blocking, e.g. `DROP COLUMN`,
  `CREATE INDEX CONCURRENTLY`).
- **Belongs in:** `fhir-server (data layer)` — entirely dependent on owning the Postgres schema, which
  `fhir-gql` explicitly does not.
- **Port notes for fhir-gql (FastAPI/Python):** N/A for `fhir-gql` itself. If `fhir-server` is ever
  reimplemented in Python, note that this pattern (introspect-and-diff rather than hand-written
  migrations) is unusual — most Python stacks would instead use `alembic` with `--autogenerate` against
  SQLAlchemy models, which solves a similar problem more conventionally at the cost of not deriving the
  target schema from FHIR definitions dynamically.
- **Priority:** N/A / Low — out of scope for `fhir-gql`'s architecture. Document only.

### Pre-Deploy vs Post-Deploy Migration Phasing
- **What it does:** Formalizes migrations as a two-phase rollout: `preDeploy` actions run automatically
  before/at server boot (must be fast and backward-compatible with the *previous* app version still
  running elsewhere in the cluster); `postDeploy` actions run afterward as an explicit, queued,
  resumable background job once all servers are confirmed to be on the new version.
- **Source files:** `src/migrations/types.ts` (`PhasalMigration` type: `{ preDeploy, postDeploy }`);
  `src/migrations/migrate.ts` (`combine()`, `writePreDeployActionsToBuilder()`,
  `writePostDeployActionsToBuilder()` — code-generates a `run(client)` function for pre-deploy and a
  `CustomPostDeployMigration` object for post-deploy); `src/migrations/migration-utils.ts`
  (`getPreDeployMigration()`, `getPostDeployMigration()`, `MigrationDefinitionNotFoundError`).
- **How it works:** Migration generation writes actual `.ts` files (`schema/vNNN.ts`,
  `data/vNNN.ts`) checked into the repo, not just SQL — each is compiled and versioned like any other
  code. `enforceStrictMigrationVersionChecks()` + `isClusterCompatible()` (via
  `getRegisteredServers()`) prevent a post-deploy migration from starting until every server instance
  in the cluster reports a version new enough to have the corresponding migration code, avoiding a
  worker from an old deploy trying (and failing) to run a migration it doesn't understand.
- **Belongs in:** `fhir-server (data layer)`.
- **Port notes for fhir-gql (FastAPI/Python):** N/A directly, but the *rollout safety pattern* — never
  run a blocking/backward-incompatible schema change synchronously at boot; always split into
  "safe-now" vs. "needs-new-code-everywhere-first" — is worth keeping in mind for `fhir-gql`'s own
  deploys even without a database (e.g. Redis key-schema changes, breaking changes to the GraphQL
  schema).
- **Priority:** N/A / Low — architecture pattern reference only.

### Migration CLI Runner & File Generation
- **What it does:** A CLI entry point (`bun run migrate`) that connects to Postgres, runs the schema
  diff, and either prints the generated SQL/TS (`--dryRun`) or writes new versioned migration files
  and updates their index/manifest. Also supports `--writeSchema` to emit a fresh `schema.sql` snapshot
  of the entire target schema (used to bootstrap a brand-new database quickly instead of replaying
  hundreds of incremental migrations).
- **Source files:** `src/migrations/migrate-main.ts` — `main()`, `getNextVersion()`,
  `rewriteMigrationExports()`, `addDataMigrationToManifest()`, `runFromCli()`.
- **How it works:** Scans `src/migrations/schema/v*.ts` / `data/v*.ts` for the highest existing version
  number, writes the next one, regenerates a barrel `index.ts` re-exporting every migration (with a
  load-bearing comment at `v9` to stop editors from "helpfully" re-sorting imports and breaking numeric
  ordering), and appends an entry to `data-version-manifest.json` recording which server release
  (`semver.inc(packageJson.version, 'patch')`) each post-deploy migration first shipped in.
- **Belongs in:** `fhir-server (data layer)`.
- **Port notes for fhir-gql (FastAPI/Python):** N/A — if `fhir-server` used Python/SQLAlchemy, this
  entire class of tooling is superseded by `alembic revision --autogenerate` + `alembic upgrade head`,
  which handles versioned migration file generation and a manifest (the `alembic_version` table)
  out of the box.
- **Priority:** N/A / Low.

### Migration Versioning & First-Boot Detection
- **What it does:** Tracks "which migration version is the database currently at" via a dedicated
  `DatabaseMigration` table (`version`, `dataVersion`, `firstBoot` columns), and defines sentinel values
  `FIRST_BOOT (-2)`, `UNKNOWN (-1)`, `NONE (0)` to special-case a brand-new database (skip strict
  version-gating so a fresh dev environment isn't blocked mid-bootstrap) versus a database whose state
  can't be determined (fail loudly rather than silently corrupt data).
- **Source files:** `src/migrations/migration-versions.ts` — `MigrationVersion` const,
  `getPreDeployMigrationVersions()`, `getPostDeployMigrationVersions()`,
  `getLatestPostDeployMigrationVersion()`; consumed by `src/migrations/migration-utils.ts`
  (`getPendingPostDeployMigration()`, `isFirstBootMode()`).
- **How it works:** `getMigrationVersions()` reflects over the generated migration modules'
  export keys (`v1`, `v2`, ...) rather than maintaining a separate list, so the set of "known versions"
  can never drift from the actual migration files on disk.
- **Belongs in:** `fhir-server (data layer)`.
- **Port notes for fhir-gql (FastAPI/Python):** N/A directly (Alembic's `alembic_version` table plus
  `alembic heads`/`alembic current` covers this need natively). Worth noting only if `fhir-gql` ever
  needs an analogous "is this a first-boot / cold environment" check for its own Redis-backed state
  (e.g. rate-limit counters), which it currently does not.
- **Priority:** N/A / Low.

### Post-Deploy Migration Execution Framework (Worker + Job Data Types)
- **What it does:** Runs data migrations (backfills, full-table rewrites, custom one-off scripts) as
  BullMQ jobs rather than blocking server startup, with resumability, deduplication (only one job per
  migration version), interruption handling (queue shutdown mid-migration re-delays rather than losing
  progress), and cluster-version compatibility gating.
- **Source files:** `src/workers/post-deploy-migration.ts` — `initPostDeployMigrationWorker()`,
  `jobProcessor()`, `runDynamicMigration()`, `runCustomMigration()`, `isClusterCompatible()`,
  `addPostDeployMigrationJobData()`, `prepareCustomMigrationJobData()`,
  `prepareDynamicMigrationJobData()`; orchestration entry points in `src/migrations/migration-utils.ts`
  (`maybeAutoRunPendingPostDeployMigration()`, `maybeStartPostDeployMigration()`,
  `queuePostDeployMigration()`, `preparePostDeployMigrationAsyncJob()`,
  `withLongRunningDatabaseClient()` — sets `statement_timeout` to 0 for migration-length queries).
- **How it works:** Each post-deploy migration is represented by an `AsyncJob` FHIR resource
  (`type: 'data-migration'`) plus a BullMQ job keyed by `deduplication: { id: 'v${dataVersion}' }` so
  re-triggering an already-queued/running migration is a no-op. `moveToDelayedAndThrow()` (from
  `workers/utils.ts`) is used both when a worker isn't running new-enough code yet
  (`isJobCompatible`/`isClusterCompatible`) and when the BullMQ queue itself is shutting down mid-job —
  in both cases the job is pushed 60s into the future and retried rather than failed outright.
- **Belongs in:** `fhir-server (data layer)`.
- **Port notes for fhir-gql (FastAPI/Python):** N/A for schema/data migrations (no DB), but the
  **resumable-job-via-delayed-requeue** pattern (`moveToDelayedAndThrow`) is a generically useful
  background-job idiom worth reusing if `fhir-gql` ever runs its own async jobs (see Job Queue section
  below) — e.g. Celery's `self.retry(countdown=60)` or arq's `Retry(defer=60)` achieve the same effect.
- **Priority:** N/A / Low for `fhir-gql`; the requeue-on-incompatible-worker pattern is worth a mention
  if `fhir-gql` ever adds background workers (Medium relevance to that future feature, not to bulk
  ops directly).

### Non-Blocking Schema Change Helpers
- **What it does:** A library of Postgres DDL helpers specifically designed to avoid long table locks on
  large production tables: adding `CHECK` constraints as `NOT VALID` then validating separately
  (`nonBlockingAddCheckConstraint`), setting a column `NOT NULL` via a temporary check constraint
  instead of a full-table rewrite (`nonBlockingAlterColumnNotNull`), idempotent
  `CREATE INDEX CONCURRENTLY` that self-heals from a previously-interrupted/invalid index
  (`idempotentCreateIndex`), and batched `UPDATE ... RETURNING` loops that cap total iterations
  (`batchedUpdate`).
- **Source files:** `src/migrations/migrate-functions.ts` — `query()`, `idempotentCreateIndex()`,
  `analyzeTable()`, `nonBlockingAddCheckConstraint()`, `nonBlockingAlterColumnNotNull()`,
  `addCheckConstraint()`, `batchedUpdate()`.
- **How it works:** Each helper records `{ name, durationMs }` into a shared `MigrationActionResult[]`
  accumulator so the outcome of every DDL statement in a migration run is visible in the `AsyncJob`
  output (surfaced back to operators as FHIR `Parameters`).
- **Belongs in:** `fhir-server (data layer)`.
- **Port notes for fhir-gql (FastAPI/Python):** N/A — this is standard "zero-downtime Postgres
  migration" wisdom (NOT VALID + VALIDATE CONSTRAINT, `CREATE INDEX CONCURRENTLY`) that any Python
  service owning a schema should apply via Alembic operations (`op.execute(...)` with the same SQL) —
  not something `fhir-gql` needs since it owns no schema.
- **Priority:** N/A / Low.

---

## 3. Reference Data Seeding

### Definitional Resource Seeding (SearchParameter / StructureDefinition / ValueSet)
- **What it does:** Loads the built-in FHIR R4 definitional resources — `SearchParameter`,
  `StructureDefinition`, `OperationDefinition`, `CodeSystem`, `ValueSet` — into the database at
  boot/deploy time, so the server has something to validate/search against before any user data exists.
- **Source files:** `src/seeds/searchparameters.ts` (`rebuildR4SearchParameters()`),
  `src/seeds/structuredefinitions.ts` (`rebuildR4StructureDefinitions()`),
  `src/seeds/valuesets.ts` (`rebuildR4ValueSets()`) — each is a one-line wrapper around the shared
  `rebuildBaseDefinitions(systemRepo, [...resourceTypes])` helper (defined in
  `fhir/operations/rebuild-base-definitions.ts`, out of scope here).
- **How it works:** Reads the packaged FHIR definition JSON bundles (from `@medplum/definitions`) and
  upserts each entry as a real FHIR resource via the system repository, making them queryable through
  the normal FHIR search API rather than being special-cased in application code.
- **Belongs in:** `fhir-server (data layer)` — this is exclusively about seeding rows into Postgres,
  which `fhir-gql` cannot do.
- **Port notes for fhir-gql (FastAPI/Python):** N/A for `fhir-gql`. If `fhir-server` needs an
  equivalent Python seeding step, a startup script that reads the HL7 FHIR R4 definition bundles
  (`fhir.resources` package or raw HL7 JSON) and bulk-upserts them via SQLAlchemy is the direct
  analog; keep it idempotent (upsert-by-canonical-URL) exactly as Medplum does.
- **Priority:** N/A / Low for `fhir-gql`.

---

## 4. Background Job Queue Infrastructure

### BullMQ Queue Registry & Worker Bootstrapping
- **What it does:** A central registry that owns the lifecycle of every named job queue+worker pair in
  the process (creation, tracking, graceful shutdown), plus per-worker enable/disable via config so a
  server pool can be split into "HTTP-only" and "worker-only" instances.
- **Source files:** `src/workers/index.ts` — `initWorkers()`, `closeWorkers()`, `addBackgroundJobs()`,
  the static `workerDefs` table mapping `WorkerName` → `WorkerInitializer`. `src/workers/utils.ts` —
  `DefaultQueueRegistry` class (`add()`, `get()`, `close()`, `closeAll()`, `isClosing()`),
  singleton `queueRegistry`, `defaultQueueOptions()`, `getBullmqRedisConnectionOptions()`,
  `getWorkerBullmqConfig()`.
- **How it works:** **Queue technology:** BullMQ (Redis-backed). **Concurrency:** global default of 20
  concurrent jobs per worker (`config.bullmq.concurrency`, set in `config/utils.ts` `addDefaults()`),
  overridable per-worker-type via `config.workers.bullmq[workerName]`. **Retry policy:** default
  `{ attempts: 3, backoff: { type: 'exponential', delay: 1000 } }` applied to every queue unless a
  specific worker overrides it (e.g. reindex and post-deploy-migration workers set `attempts: 1` — no
  automatic retries, because a partially-applied schema/data migration retried blindly could corrupt
  state; they instead use the explicit `moveToDelayedAndThrow` requeue pattern for controlled retry).
  Workers close in `worker → queue` order so in-flight jobs can finish and enqueue follow-up jobs before
  the queue itself is torn down. Redis connection can be a dedicated `backgroundJobsRedis` config,
  separate from the main cache/rate-limit Redis instances, to isolate load.
- **Belongs in:** `infra/ops (applies to both)` conceptually, but concretely: `fhir-server` needs this
  today for its many data workers; `fhir-gql` doesn't have background jobs yet, but if it ever needs
  one (e.g. async webhook delivery, scheduled cache warm-up, orchestrating multi-step bulk operations),
  the registry pattern applies equally well on the Python side.
- **Port notes for fhir-gql (FastAPI/Python):** If `fhir-gql` grows background jobs, prefer **arq**
  (Redis-backed, asyncio-native, pairs naturally with `redis.asyncio` already used in
  `app/core/redis.py`) over Celery for a lighter footprint; arq's `cron()` and retry/backoff settings
  map directly to BullMQ's `repeat`/`backoff` options. Mirror the registry pattern with a small
  `app/core/job_registry.py` that tracks active worker pools and exposes a `shutdown()` hook wired into
  FastAPI's lifespan context, analogous to `closeWorkers()`.
- **Priority:** Low today (no background-job requirement yet); Medium once `fhir-gql` needs any
  fire-and-forget or scheduled work (e.g. webhook retries, cache invalidation sweeps).

### Verbose Queue Event Logging
- **What it does:** Attaches structured log lines to every BullMQ lifecycle event (`active`, `closing`,
  `closed`, `completed`, `error`, `failed`, `stalled`) for a given queue/worker pair, including derived
  timing fields (`queuedDurationMs`, `executionDurationMs`, `totalDurationMs`) and job-specific context
  via a caller-supplied field extractor.
- **Source files:** `src/workers/utils.ts` — `addVerboseQueueLogging()`, `getFinishedJobFieldsForLogging()`.
- **How it works:** Wraps `globalLogger.info()`/`.warn()` calls around each BullMQ `worker.on(event, ...)`
  hook; every worker module (`reindex.ts`, `lambda-cleaner.ts`, `post-deploy-migration.ts`, etc.) calls
  this once at init with a small per-job "extra fields" callback (e.g. `{ asyncJob, jobType }`).
- **Belongs in:** `infra/ops (applies to both)`.
- **Port notes for fhir-gql (FastAPI/Python):** Directly portable pattern: wrap arq's `on_job_start`/
  `on_job_end`/`on_job_error` hooks (or Celery's `task_prerun`/`task_postrun`/`task_failure` signals)
  in a helper that emits through the existing `app.core.logging.get_logger()` JSON logger, computing the
  same queued/execution/total duration fields. Trivial to add once any job queue exists.
- **Priority:** Low — tightly coupled to a job queue that doesn't exist in `fhir-gql` yet.

### Job Compatibility & Version Gating
- **What it does:** Prevents a worker running older code from processing a job that requires newer
  logic (`isJobCompatible`, `isJobActive`), and provides a standard "delay and retry later" escape
  hatch (`moveToDelayedAndThrow`) for jobs that a given worker instance currently cannot or should not
  process (wrong version, queue shutting down).
- **Source files:** `src/workers/utils.ts` — `isJobActive()`, `isJobCompatible()`,
  `InProgressAsyncJobStatuses`, `moveToDelayedAndThrow()`, `updateAsyncJobOutput()` (optimistic
  concurrency via `ifMatch: asyncJob.meta?.versionId` to avoid clobbering concurrent updates).
- **How it works:** Compares `AsyncJob.minServerVersion` against the running server's own
  `getServerVersion()` (semver) before a worker accepts a job for processing; used across the reindex,
  post-deploy-migration, and set-accounts workers.
- **Belongs in:** `infra/ops (applies to both)`.
- **Port notes for fhir-gql (FastAPI/Python):** If `fhir-gql` runs multiple instances during rolling
  deploys and later adds background jobs, the same "job carries a minimum-version marker, worker
  checks its own version before accepting" pattern avoids the classic "old worker chokes on new job
  schema" bug during deploys. Low urgency until jobs exist.
- **Priority:** Low.

---

## 5. Data Maintenance Workers

### Full-Database Reindex Worker
- **What it does:** Rebuilds every resource's search-index columns/lookup-table rows across an entire
  resource type (or all types) — needed after adding a new `SearchParameter`, changing a search
  strategy, or fixing an indexing bug — without requiring downtime.
- **Source files:** `src/workers/reindex.ts` — `ReindexJob` class (`execute()`, `processIteration()`,
  `processIterationWithRetry()`, `nextIterationData()`), `initReindexWorker()`, `addReindexJob()`,
  `prepareReindexJobData()`, `REINDEX_WORKER_VERSION` (bumped when the worker's logic changes to
  invalidate in-flight jobs on old code), `ReindexJobData`/`ReindexResult`/`ReindexJobSettings` types.
- **How it works:** Paginates through a resource table via a cursor-based search ordered by
  `_lastUpdated` (bounded by a snapshot `endTimestamp` taken at job start, so newly-written rows during
  the reindex aren't endlessly chased), processing `batchSize` (default 500) rows per iteration inside a
  transaction with a bounded `statement_timeout` (1 hour default) to avoid runaway queries on huge
  tables. Each iteration re-enqueues itself as a new BullMQ job (rather than looping in-process) so
  progress survives worker restarts/deploys; progress and errors are periodically written back into the
  tracking `AsyncJob.output` (throttled via `progressLogThreshold` so it's not written on every single
  batch). Failed iterations retry up to `maxIterationAttempts` (default 3) before giving up and recording
  the error + a resumable `nextTimestamp` checkpoint.
- **Belongs in:** `fhir-server (data layer)` — requires direct table scans/updates against Postgres.
- **Port notes for fhir-gql (FastAPI/Python):** N/A for `fhir-gql`. If `fhir-server` needs an equivalent
  in Python, the key transferable ideas are: (1) cursor pagination bounded by a start-of-job timestamp
  snapshot, not open-ended `OFFSET`; (2) re-enqueue-per-batch rather than one long-running task, so a
  multi-hour reindex survives deploys/restarts; (3) a worker-code version guard so an in-flight
  multi-hour job doesn't get picked up by a worker running older, incompatible reindex logic.
- **Priority:** N/A / Low for `fhir-gql` directly — flagged as an important pattern for whoever owns
  `fhir-server`'s search-index maintenance.

### Account/Compartment Reassignment Worker
- **What it does:** Asynchronously updates the `Account`/compartment references across an entire
  resource's compartment (e.g. reassigning every resource linked to a `Patient` to a different billing
  `Account`), decoupled from the triggering HTTP request so large compartments don't time out a
  synchronous API call.
- **Source files:** `src/workers/set-accounts.ts` — `initSetAccountsWorker()`, `execSetAccountsJob()`,
  `addSetAccountsJobData()`, `SetAccountsJobData` type.
- **How it works:** Runs inside `runInAuthenticatedContext()` using the *original submitting user's*
  auth state (captured in the job data) rather than a system-level identity, so access-control checks
  during the bulk update are enforced exactly as if the user had made each change directly. Uses
  `AsyncJobExecutor.startAsync()` to track progress/failure via the standard `AsyncJob` resource, and a
  `worker.on('failed', ...)` handler to explicitly mark the job failed if BullMQ exhausts retries.
- **Belongs in:** `fhir-server (data layer)` — requires bulk resource writes across a compartment.
- **Port notes for fhir-gql (FastAPI/Python):** N/A directly. If `fhir-gql` ever proxies a
  bulk-reassignment-style operation, the transferable idea is capturing the *requesting user's* auth
  context into the job payload so a background worker enforces the same RBAC (`app/auth/rbac.py`) the
  synchronous request path would have — not a system/service-account bypass.
- **Priority:** N/A / Low for `fhir-gql`.

### AWS Lambda Version Cleanup Worker
- **What it does:** A scheduled/on-demand housekeeping job that scans all AWS Lambda functions matching
  a name pattern (Medplum Bots are deployed as Lambdas) and deletes old published versions beyond a
  configurable `keepLatest` retention count, with a dry-run mode and bounded delete concurrency.
- **Source files:** `src/workers/lambda-cleaner.ts` — `execLambdaCleanerJob()`,
  `initLambdaCleanerWorker()`, `addLambdaCleanerJobData()`, `LambdaCleanerOptions`/`LambdaCleanerSummary`
  types; delegates the actual per-function deletion to `deleteOldLambdaVersions()` in
  `cloud/aws/lambda.ts` (out of scope).
- **How it works:** Paginates AWS's `ListFunctionsCommand` via its `Marker` cursor, regex-matches
  function names, and reports a structured summary (functions scanned/matched, versions
  planned/deleted/not-found/aliased) back as FHIR `Parameters` on the tracking `AsyncJob`.
- **Belongs in:** `fhir-server (data layer)` / infra-specific to Medplum's AWS Lambda Bot runtime —
  `fhir-gql` has no Bot/Lambda execution model at all.
- **Port notes for fhir-gql (FastAPI/Python):** Not applicable — `fhir-gql` has no equivalent
  "user-authored serverless functions" feature. No action needed.
- **Priority:** N/A — not relevant to `fhir-gql`'s architecture.

---

## 6. Observability (OpenTelemetry)

### OpenTelemetry SDK Instrumentation (Traces + Metrics)
- **What it does:** Wires up a full OpenTelemetry `NodeSDK` — distributed tracing (OTLP over HTTP) and
  metrics export — auto-instrumenting HTTP, Express, GraphQL, PostgreSQL (`pg`), Redis (`ioredis`),
  BullMQ, DataLoader, and Node.js runtime internals (event loop lag, GC, heap), gated entirely behind
  presence of `OTLP_METRICS_ENDPOINT` / `OTLP_TRACE_ENDPOINT` env vars (no-op if unset).
- **Source files:** `src/otel/instrumentation.ts` — `initOpenTelemetry()`, `httpResponseHook()`,
  `pgResponseHook()`, `shutdownOpenTelemetry()`. Auto-runs at import time
  (`if (process.env.NODE_ENV !== 'test') initOpenTelemetry()`), meaning this module **must be
  imported before any other application code** (it's the top-level entry point / `--require` hook).
- **How it works:** Uses a `CompositePropagator` combining W3C Trace Context and AWS X-Ray propagation
  formats (so traces interop with both standards-based and AWS-native tooling). Custom span hooks record
  Postgres row counts and mark HTTP spans as errored for any 5xx response. Deliberately drops noisy
  Express middleware layers (`expressInit`, `corsMiddleware`, `compression`, etc.) from spans to reduce
  trace clutter, and `ignoreTrivialResolveSpans` on the GraphQL instrumentation skips spans for
  simple property-lookup resolvers. Histogram metrics default to exponential-bucket aggregation
  (better for latency distributions with wide dynamic range than fixed linear buckets).
- **Belongs in:** `infra/ops (applies to both)` — this is exactly the kind of tooling both `fhir-gql`
  and `fhir-server` should have, since `fhir-gql` currently has **no tracing/metrics at all**, only
  structured logs.
- **Port notes for fhir-gql (FastAPI/Python):** This is the single highest-value item in this whole
  report to port. Concretely:
  - `opentelemetry-distro` + `opentelemetry-exporter-otlp-proto-http` for the SDK/exporter, mirroring
    Medplum's OTLP-over-HTTP choice.
  - `opentelemetry-instrumentation-fastapi` (HTTP/route spans, equivalent to `HttpInstrumentation` +
    `ExpressInstrumentation`), `opentelemetry-instrumentation-httpx` (since `app/fhir_client/client.py`
    almost certainly uses `httpx` to call the downstream `fhir-server` — equivalent to instrumenting
    outbound requests), `opentelemetry-instrumentation-redis` (equivalent to `IORedisInstrumentation`,
    covers both `app/core/redis.py` and `app/middleware/rate_limit.py`), and
    `opentelemetry-instrumentation-strawberry` (or manual span wrapping in `app/gql/schema.py`) as the
    GraphQL equivalent of `GraphQLInstrumentation`.
  - Gate initialization behind env vars exactly as Medplum does (`OTLP_TRACES_ENDPOINT` /
    `OTLP_METRICS_ENDPOINT` unset ⇒ no-op) so local dev isn't forced to stand up a collector; wire this
    as new fields on `app/config.py`'s `Settings`.
  - Initialize in `app/main.py` before the FastAPI app is constructed (equivalent to Medplum's
    import-order requirement), and add a `httpResponseHook`-equivalent that marks spans errored on
    5xx and skips the `/healthcheck`-equivalent route from tracing noise
    (`ignoreIncomingRequestHook` in Medplum's `HttpInstrumentation` config).
- **Priority:** High — `fhir-gql` currently has zero tracing/metrics, which is a real operational gap
  for a middleware service that proxies to another network service (you cannot currently see latency
  breakdown between `fhir-gql`'s own logic, the `fhir-server` round-trip, JWKS fetches, and Redis calls
  without this).

### Custom Metrics Helpers & Heartbeat-Driven Gauges
- **What it does:** A thin wrapper over the OTel metrics API providing memoized counter/histogram/gauge
  accessors (`getCounter`, `getHistogram`, `getGauge` — created once per name, reused thereafter), plus
  a periodic heartbeat listener that samples and publishes system-level gauges every heartbeat tick:
  Postgres pool stats (total/idle/waiting connections, separately for writer and reader pools), Node
  heap statistics (used heap size, old/new space usage), and BullMQ queue depth (`waitingCount`,
  `delayedCount`) per queue.
- **Source files:** `src/otel/otel.ts` — `getCounter()`, `incrementCounter()`, `getHistogram()`,
  `recordHistogramValue()`, `getGauge()`, `setGauge()`, `initOtelHeartbeat()`, `cleanupOtelHeartbeat()`,
  `isOtelMetricsEnabled()`.
- **How it works:** All record functions no-op (return `false`) when `OTLP_METRICS_ENDPOINT` isn't set,
  so instrumentation call sites elsewhere in the codebase can unconditionally call
  `incrementCounter(...)`/`setGauge(...)` without every caller needing its own enabled-check. The
  heartbeat hooks into a shared app-wide `heartbeat` event emitter (defined elsewhere) rather than
  running its own `setInterval`, so metric sampling cadence stays in lockstep with the rest of the
  app's periodic housekeeping.
- **Belongs in:** `infra/ops (applies to both)`.
- **Port notes for fhir-gql (FastAPI/Python):** Mirror with a small `app/core/metrics.py` exposing
  `get_counter(name)`/`get_histogram(name)`/`get_gauge(name)` backed by `opentelemetry.metrics.get_meter()`,
  each a no-op-safe wrapper (check `if not settings.OTLP_METRICS_ENDPOINT: return` at the top, same as
  Medplum). Worth publishing at minimum: Redis connection pool stats, the downstream `httpx` client's
  connection pool stats (`fhir_client/client.py`), and rate-limit-middleware counters (requests
  allowed/blocked per window) as an initial gauge/counter set — these map directly onto what
  `fhir-gql` already owns.
- **Priority:** High alongside the base OTel instrumentation above — the specific gauges (connection
  pool health, queue-equivalent depth) are exactly the kind of "is the service healthy right now"
  signal a proxy/middleware layer needs, and it's a small amount of code once the SDK is wired up.

---

## 7. Configuration Management

### Multi-Source Config Loader (file / env / AWS / GCP / Azure)
- **What it does:** Loads server configuration from one or more comma-separated sources — a JSON file,
  environment variables (`MEDPLUM_*` prefix), AWS SSM Parameter Store, GCP, or Azure Key Vault — with
  later sources deep-merging on top of earlier ones (e.g. `"file:base.json,env"` lets env vars override
  a checked-in base config for per-environment secrets).
- **Source files:** `src/config/loader.ts` — `loadConfig()`, `loadSingleConfig()`, `loadEnvConfig()`,
  `loadFileConfig()`, `getConfig()`/`cachedConfig` singleton, `loadTestConfig()`, `deepMerge()`.
- **How it works:** `loadEnvConfig()` parses `MEDPLUM_DATABASE_HOST` → `config.database.host`,
  `MEDPLUM_REDIS_DB` → `config.redis.db`, etc., by prefix-stripping known section names
  (`DATABASE_`, `READONLY_DATABASE_`, `REDIS_`, `SMTP_`, `BULLMQ_`, `WORKERS_`, `DATA_WAREHOUSE_`, ...)
  before converting `SCREAMING_SNAKE` to `camelCase`, and type-coerces each value (int/float/bool/
  object/array) based on a static registry of known keys (see next entry). `getConfig()` throws if
  called before `loadConfig()` has run once — config is a lazily-initialized singleton, not
  re-read per call.
- **Belongs in:** `fhir-gql (middleware)` — `fhir-gql` already owns its own config
  (`app/config.py`, `pydantic-settings`); this doesn't require any `fhir-server`-side changes.
- **Port notes for fhir-gql (FastAPI/Python):** `app/config.py` already gets file(.env)+env-var loading
  "for free" via `pydantic-settings`' `SettingsConfigDict(env_file=".env")`, which covers the two most
  important sources here. The multi-cloud-secret-source layering (AWS SSM/GCP/Azure) is the part
  `pydantic-settings` doesn't give out of the box — if `fhir-gql` is deployed to AWS,
  `pydantic-settings` has an official `pydantic-settings[aws-secrets-manager]` /
  a custom `PydanticBaseSettingsSource` can be written wrapping `boto3` SSM `get_parameters_by_path`,
  mirroring Medplum's `aws:` prefix. Not urgent while the current `.env`-only setup is sufficient.
- **Priority:** Low — `fhir-gql`'s existing `pydantic-settings` config already covers the common cases;
  only add cloud-secret-source layering when an actual deployment target requires it.

### Typed Config Schema (MedplumServerConfig)
- **What it does:** A single large, heavily-commented TypeScript interface enumerating every
  configurable server setting — over 80 fields covering auth URLs, database/redis/smtp connection
  info, rate limits, feature flags, worker pool configuration, and data-warehouse settings — serving as
  both documentation and compile-time validation of config usage throughout the codebase.
- **Source files:** `src/config/types.ts` — `MedplumServerConfig` interface and its nested types
  (`MedplumDatabaseConfig`, `MedplumRedisConfig`, `MedplumSmtpConfig`, `MedplumBullmqConfig`,
  `MedplumWorkersConfig`, `MedplumDataWarehouseConfig`, `MedplumExternalAuthConfig`,
  `SubscriptionAutoDisableTrigger`, `ArrayColumnPaddingConfig`, `WorkerName` union type).
- **How it works:** Every config consumer imports this interface and destructures/reads from
  `getConfig()`'s return value, so adding a new setting is "add a field here + read it somewhere" with
  the compiler catching typos; JSDoc comments on each field double as inline reference docs (e.g.
  explaining exactly what `fhirSearchMinLimit` does and why it exists, referencing a specific GitHub
  issue for `arrayColumnPadding`).
- **Belongs in:** `fhir-gql (middleware)` (for `fhir-gql`'s own config) / `infra/ops (applies to both)`
  as a pattern.
- **Port notes for fhir-gql (FastAPI/Python):** `app/config.py`'s `Settings(BaseSettings)` class already
  *is* this pattern — a single typed, documented settings class. The main gap versus Medplum's version
  is comment density on non-obvious settings and the sheer breadth of what's configurable (currently
  ~10 fields vs. Medplum's ~80+), which will grow organically as `fhir-gql` adds features (this exact
  report's recommendations, if implemented, would each add a few fields). No structural change needed —
  keep extending `Settings` the same way.
- **Priority:** Low — already well-covered by the existing `app/config.py` pattern; this entry is
  purely a "keep doing what you're doing" note.

### Config Defaults & Type Coercion Utilities
- **What it does:** Applies default values to optional config fields after loading (`addDefaults()`),
  and maintains static sets of which config keys are integers/floats/booleans/objects/arrays so the
  env-var loader (and a `setValue()` helper used by other tooling) can correctly parse
  `process.env` string values into the right type instead of leaving everything as strings.
- **Source files:** `src/config/utils.ts` — `addDefaults()`, `ServerConfig` type (`MedplumServerConfig`
  with defaulted fields made required), `isIntegerConfig()`/`isFloatConfig()`/`isBooleanConfig()`/
  `isObjectConfig()`/`isArrayConfig()`, `setValue()`.
- **How it works:** Notably includes a runtime escape hatch: if no signing key is configured *and*
  storage is same-origin, it auto-generates a throwaway RSA keypair at boot with a loud warning log —
  convenient for local dev, explicitly documented as unsafe for clustered/persistent deployments (keys
  regenerate on every restart, breaking any URLs signed with the old key).
- **Belongs in:** `fhir-gql (middleware)`.
- **Port notes for fhir-gql (FastAPI/Python):** `pydantic-settings` handles type coercion automatically
  from field type annotations (no need for a parallel `isIntegerConfig()`-style registry — this is
  solving a problem Pydantic already solves natively). The one genuinely useful idea to borrow: an
  explicit, loud warning (`logger.warning(...)`) for any setting that silently falls back to an unsafe
  dev-only default (e.g. `IAM_JWKS_URL`/`IAM_ISSUER` defaulting to `localhost` in `app/config.py` today
  produce no such warning if accidentally left unset in a real deployment). Consider a small
  `Settings.model_post_init` hook that warns if `ENVIRONMENT == "production"` but any `localhost`-looking
  default is still in effect.
- **Priority:** Low — mostly superseded by `pydantic-settings`; the production-safety-warning idea is a
  cheap, worthwhile addition (Low/Medium effort, meaningful safety value).

### Data Warehouse Config Validation
- **What it does:** Validates `dataWarehouse.*` config (required fields per destination type, mutually
  exclusive include/exclude resource-type filters, ISO-8601 `startDate` format, unknown resource type
  names) and logs a warning — rather than crashing the server — if the feature is enabled but
  misconfigured, simply not starting the sync worker.
- **Source files:** `src/config/validate-config.ts` — `getDataWarehouseConfigErrors()`,
  `isDataWarehouseSyncOperational()`, `warnInvalidDataWarehouseConfig()`.
- **How it works:** Called once at the end of `loadConfig()`/`loadTestConfig()`; cross-references
  `config.dataWarehouse.includeResourceTypes`/`excludeResourceTypes` against the known set of
  Postgres history table names (`getWarehouseSyncPostgresTableNames()`) to catch typos'd resource type
  names early rather than failing deep inside a sync job.
- **Belongs in:** `fhir-server (data layer)` (tied specifically to the data-warehouse feature, which is
  a `fhir-server` concern — see Section 8).
- **Port notes for fhir-gql (FastAPI/Python):** N/A directly for `fhir-gql` (no data warehouse feature),
  but the general pattern — **fail soft with a loud warning for optional/advanced features that are
  enabled-but-misconfigured, rather than crashing server startup** — is a good default for any future
  optional `fhir-gql` feature flag (e.g. an optional webhook-dispatch feature with bad config shouldn't
  take down the whole API). Implement via a Pydantic `model_validator(mode="after")` that returns
  warnings rather than raising, logged through `app.core.logging`.
- **Priority:** Low for `fhir-gql` directly; Low/Medium as a general validation-pattern note for future
  optional features.

---

## 8. Key-Value Store

### Per-User Redis-Backed Key-Value Store
- **What it does:** A tiny, generic REST API (`GET`/`PUT`/`DELETE /keyvalue/:key`) letting an
  authenticated user store small opaque string values (bot/client-side app state, feature flags,
  UI preferences) scoped to their project membership, with hard caps (255-char keys,
  8KB values, 10 items per user) to keep it from becoming a general-purpose database substitute.
- **Source files:** `src/keyvalue/routes.ts` — `keyValueRouter` (mounted behind `authenticateRequest`).
  `src/keyvalue/store.ts` — `getValue()`, `setValue()`, `deleteValue()`, `validateKey()`, `getCacheKey()`,
  constants `MAX_KEY_LENGTH`/`MAX_VALUE_LENGTH`/`MAX_ITEMS`.
- **How it works:** Backed by a single Redis **hash** per user (`medplum:keyvalue:{membershipId}`) via
  `getCacheRedis()` (a dedicated cache-purpose Redis connection, separate from the rate-limit/BullMQ
  Redis instances) — `hget`/`hset`/`hdel`/`hexists`/`hlen`. Key format is restricted to
  `[a-zA-Z0-9_-]+` to prevent any injection-adjacent surprises. The item-count cap is enforced by
  checking `hlen` before allowing a *new* key (existing key updates are always allowed regardless of
  count).
- **Belongs in:** `fhir-gql (middleware)` — this is a clean, self-contained fit: it needs only
  authentication context (which `fhir-gql` already owns via `app/auth/dependencies.py`) and a Redis
  connection (`app/core/redis.py` already exists), with zero dependency on `fhir-server`/Postgres.
- **Port notes for fhir-gql (FastAPI/Python):** Very cheap, high-clarity port. Add
  `app/services/keyvalue_service.py` with `get_value`/`set_value`/`delete_value` using
  `redis.asyncio`'s `hget`/`hset`/`hdel`/`hexists`/`hlen` against a hash keyed by the authenticated
  user's identity (from the existing JWT-derived context, e.g. `sub` claim or membership ID once RBAC
  models expose one), and a small `app/routers/keyvalue.py` with the same three-route shape validated
  by a Pydantic model enforcing the same length/count caps. This is a good "cheap, self-contained
  feature to add early" candidate precisely because it exercises the existing auth+Redis
  infrastructure without needing any `fhir-server` involvement.
- **Priority:** Medium — low implementation cost, no `fhir-server` coupling, and a plausible near-term
  need (client apps/bots wanting to persist small bits of state) once `fhir-gql` has real API consumers
  beyond `Patient` reads.

---

## 9. Transactional Email

### Transactional Email Sending (SMTP / SES, Project-Level Override)
- **What it does:** Sends outbound email (invitations, notifications, verification codes, etc.) via
  either AWS SES or SMTP, with the sending transport and "from" address resolvable per-project (a
  project can configure its own SMTP relay + approved senders via `Project.secret` entries, falling back
  to server-wide defaults otherwise), and safe handling of FHIR `Binary` attachments (streamed from
  storage rather than trusting arbitrary file paths).
- **Source files:** `src/email/email.ts` — `sendEmail()`, `processAttachments()`,
  `processAttachment()`, `sendEmailViaSmtp()`. `src/email/routes.ts` — `emailRouter`
  (`POST /email/send`, gated on `project.features.includes('email')` + admin membership).
  `src/email/utils.ts` — `getProjectSmtpConfig()`, `getFromAddress()`, `buildAddresses()`,
  `addressToString()`, `extractEmailFromAddress()`, `buildRawMessage()`.
  `src/cloud/aws/email.ts` — `sendEmailViaSes()`.
- **How it works:** Uses `nodemailer`'s `MailComposer` to build a RFC822 raw message once, shared by
  both the SMTP and SES code paths (SES's `SendEmailCommand` accepts raw MIME via `Content.Raw.Data`).
  `disableFileAccess = true` is explicitly set on the nodemailer options to prevent nodemailer from
  ever reading arbitrary local files as attachments — any `Binary/...`-prefixed attachment path is
  intercepted and swapped for a stream read through the authenticated FHIR repository first (enforcing
  normal read-access checks on the attachment), then the original file-path-looking value is deleted
  before nodemailer ever sees it. The "from" address is only honored if it's in the approved-senders
  allowlist (server- or project-level); otherwise silently falls back to the configured default and
  logs a warning — never lets a caller spoof an arbitrary from-address.
- **Belongs in:** `fhir-gql (middleware)` — sending email is a stateless orchestration action (call an
  SMTP/SES API) that doesn't require Postgres. The only `fhir-server` dependency is resolving a
  `Binary` attachment, which `fhir-gql` can do through its existing `app/fhir_client` proxy layer
  exactly like it does for `Patient` reads today.
- **Port notes for fhir-gql (FastAPI/Python):** Use **`aiosmtplib`** for SMTP (async-native, avoids
  blocking the event loop the way the sync `smtplib` would) and **`boto3`/`aioboto3`**'s `sesv2` client
  for SES, both selected by config the same way (`EMAIL_PROVIDER: Literal["none","smtp","ses"]` on
  `Settings`). Reuse `email.message.EmailMessage` (stdlib) or `python-multipart`-adjacent tooling in
  place of nodemailer's `MailComposer` — stdlib `email` module builds equivalent raw MIME messages
  Python-natively, so no extra dependency is needed for message construction. For attachments, only
  accept `Binary/{id}`-style references and resolve them through `app/fhir_client/client.py`
  (never accept raw filesystem paths from request bodies) — this is the single most important security
  property to preserve when porting.
- **Priority:** Medium — a common near-term need (user invites, notifications) once `fhir-gql` grows
  beyond read-only `Patient` access, and the security-sensitive parts (approved-sender allowlist,
  attachment-path sanitization) are worth designing in from day one rather than retrofitting.

### Email API Endpoint
- **What it does:** The thin HTTP surface (`POST /email/send`) gating the above feature — requires
  authentication, requires the requesting project to have explicitly opted into the `email` feature
  flag, requires the caller to be a project admin, and validates the request body shape (`to`,
  `subject` required; `Content-Type: application/json`).
- **Source files:** `src/email/routes.ts` — `emailRouter`, `sendEmailValidator` (built via
  `makeValidationMiddleware` from `util/validator.ts`, see Misc Utilities below).
- **How it works:** Delegates entirely to `sendEmail()` after the feature-flag + admin gate; the
  underlying repository object (`ctx.repo`, not a system-level repo) is passed through so any Binary
  attachment reads still go through the requesting user's own access-control policy.
- **Belongs in:** `fhir-gql (middleware)`.
- **Port notes for fhir-gql (FastAPI/Python):** A FastAPI router with a `Depends()` chain: JWT auth
  (existing `app/auth/dependencies.py`) → RBAC admin check (existing `app/auth/rbac.py`) → a Pydantic
  request model (`to: list[EmailStr]`, `subject: str`, ...) using `pydantic`'s built-in `EmailStr`
  type for validation instead of hand-rolled regex/`express-validator` checks.
- **Priority:** Medium — bundled with the email-sending feature above; same priority rationale.

---

## 10. FHIR Patch

### JSON Patch Application
- **What it does:** Applies an [RFC 6902 JSON Patch](https://www.rfc-editor.org/rfc/rfc6902) document
  to a resource in-place, used to implement the FHIR `PATCH` HTTP verb (partial resource update)
  distinct from a full `PUT` replace.
- **Source files:** `src/util/patch.ts` — `patchObject()`.
- **How it works:** A thin wrapper around `@medplum/core`'s `applyPatch()` (with
  `implicitArrayCreation: true`, allowing a patch to append to an array path that doesn't exist yet
  rather than erroring), converting any patch operation errors into a FHIR `OperationOutcomeError`
  with a `400 Bad Request` outcome combining all individual error messages.
- **Belongs in:** Ambiguous — the *patch algorithm itself* is a pure, stateless JSON transformation with
  no database dependency (could run in `fhir-gql`), but correct FHIR PATCH semantics require applying
  the patch against the *current, latest, version-locked* copy of the resource to avoid a lost-update
  race — which means the read-modify-write needs to happen atomically against `fhir-server`'s storage.
  Net: `fhir-server (data layer)` should own the authoritative patch-and-persist operation;
  `fhir-gql` could still forward `PATCH` requests transparently (as it likely already does with other
  verbs) without needing this logic at all, since it has no state to protect.
- **Port notes for fhir-gql (FastAPI/Python):** No action needed in `fhir-gql` unless it starts doing
  request/response *transformation* independent of `fhir-server` (e.g. GraphQL mutations that need to
  translate a partial-update input into a JSON Patch document before forwarding as a REST PATCH to
  `fhir-server`). If that need arises, `jsonpatch` (PyPI) is the direct equivalent of `applyPatch()`,
  including RFC 6902 compliance; wrap it the same way (catch `jsonpatch.JsonPatchException`, convert to
  the existing `app.gql.errors`/`app.core.errors` outcome shape) only if `fhir-gql` needs to *validate*
  a patch document client-side before forwarding it, not to actually apply-and-persist it.
- **Priority:** Low — only relevant if/when `fhir-gql` adds a GraphQL mutation surface that needs to
  construct or pre-validate patch documents; pure pass-through PATCH proxying needs none of this.

---

## 11. Audit Events

### Audit Event Construction Helpers
- **What it does:** A structured, spec-aligned way to build FHIR `AuditEvent` resources for
  authentication events (login/logout) and RESTful interactions (read/create/update/delete/search/
  batch/transaction/etc.), using DICOM and HL7-standard code systems rather than ad-hoc strings, with
  consistent handling of the acting user, the authenticating client application (for delegated/
  on-behalf-of/SMART auth flows), network/remote-address capture, and optional PII redaction.
- **Source files:** `src/util/auditevent.ts` — `createAuditEvent()`, `logAuditEvent()`,
  `applyOptionalRedaction()`, plus a large set of exported constants (`DicomCodeSystem`,
  `ApplicationAgentType`, `AuditEventTypeCodeSystem`, `RestfulActionCodeSystem`,
  `UserAuthenticationEvent`, `RestfulOperationType`, `LoginEvent`/`LogoutEvent`,
  `ReadInteraction`/`VreadInteraction`/`UpdateInteraction`/.../`OperationInteraction`,
  `AuditEventAction`, `AuditEventOutcome`).
- **How it works:** `createAuditEvent()` assembles the full `AuditEvent` shape (type/subtype/action
  derived automatically from a lookup table keyed by interaction subtype, `agent[]` array including
  both the acting profile and, when different, the authenticating `ClientApplication`, a `source`
  identifying the server itself, and optional `durationMs`/tracing extensions). `logAuditEvent()`
  writes the event to the structured application log stream (gated behind `config.logAuditEvents`) as
  an *additional* sink alongside (or instead of) persisting it as a real FHIR resource.
  `applyOptionalRedaction()` strips the human-readable `display` text from references when
  redaction is enabled globally or per-project, keeping only the machine-resolvable reference.
- **Belongs in:** Split by *destination*: writing an `AuditEvent` as a persisted, queryable **FHIR
  resource** is `fhir-server (data layer)`. Emitting an audit event into the **structured log stream**
  (the `logAuditEvent()` path) is squarely `fhir-gql (middleware)` — it's the exact same shape of thing
  `app/core/logging.py` already does for every request, just with a well-defined event vocabulary
  instead of ad hoc `extra={}` fields.
- **Port notes for fhir-gql (FastAPI/Python):** This is a genuinely valuable, low-cost port. Add
  `app/core/audit.py` with a small `AuditEvent` dataclass/Pydantic model (`type`, `subtype`, `who`,
  `outcome`, `resource`, `duration_ms`) and constant enums mirroring
  `AuditEventAction`/`AuditEventOutcome`/the RESTful-interaction subtype codes (these are HL7-standard
  codes, not Medplum inventions — reusing them keeps `fhir-gql`'s logs FHIR-audit-compatible even
  though it doesn't persist `AuditEvent` resources itself). Emit via the existing
  `get_logger(__name__).info(..., extra={...})` — this slots directly into the JSON formatter already
  built in `app/core/logging.py`, adding a consistent, queryable `event_type`/`outcome`/`who` shape to
  every access-control decision `fhir-gql` makes (JWT validated, RBAC allowed/denied, rate-limited,
  proxied to `fhir-server`). This is a strong complement to the existing logging/RBAC modules with very
  little new infrastructure required.
- **Priority:** High — `fhir-gql` owns JWT auth and RBAC (the exact decisions an audit trail needs to
  capture) but currently has no standardized audit-event vocabulary, only free-form structured logs;
  adopting HL7's standard AuditEvent codes as the log *shape* (without necessarily persisting FHIR
  resources) is cheap and immediately useful for compliance/security review.

### Bot/Subscription Audit Event Recording
- **What it does:** Specialized `AuditEvent` builders for two Medplum-specific automation concepts:
  Bot (serverless function) execution outcomes, and Subscription (webhook) delivery attempts —
  including configurable output destinations (persist as a `resource`, emit to the `log` stream, or
  both) and truncation of potentially-large output text to a configurable max length.
- **Source files:** `src/util/auditevent.ts` — `createBotAuditEvent()`, `createSubscriptionAuditEvent()`,
  `createAuditEventEntities()`, `createAuditEventEntity()`, `getAuditEventEntityRole()`, `tail()`.
- **How it works:** Both respect a per-resource `auditEventTrigger` setting (`always`/`never`/
  `on-error`/`on-output`) so noisy successful executions can be suppressed while still capturing
  failures, and a per-resource `auditEventDestination` list controlling whether the event becomes a
  real persisted resource, a log line, both, or (implicitly) neither.
- **Belongs in:** `fhir-server (data layer)` — Bots and Subscriptions are `fhir-server`-owned automation
  primitives that `fhir-gql` has no equivalent of today.
- **Port notes for fhir-gql (FastAPI/Python):** Not directly applicable — `fhir-gql` has no Bot or
  Subscription execution model. The *destination-configurability* idea (resource vs. log vs. both,
  with a trigger condition to reduce noise) is worth remembering if `fhir-gql` ever adds its own
  automation feature (e.g. webhook dispatch on GraphQL mutations), but there's nothing to port today.
- **Priority:** N/A — no current `fhir-gql` equivalent feature to attach this to.

---

## 12. PDF Generation

### PDF Document Generation
- **What it does:** Generates a PDF file (e.g. clinical summary documents, forms) from a structured
  document-definition object, returning the result as an in-memory `Buffer`.
- **Source files:** `src/util/pdf.ts` — `createPdf()`.
- **How it works:** Thin Promise wrapper around `pdfmake`'s streaming PDF generation
  (`PdfPrinter.createPdfKitDocument()`), collecting emitted chunks and resolving with a single
  concatenated `Buffer` once the underlying `pdfkit` document stream ends. Defaults to a Helvetica-only
  font dictionary unless custom fonts are supplied.
- **Belongs in:** `fhir-gql (middleware)` — pure, stateless document rendering with no database
  dependency; a plausible orchestration-layer responsibility (e.g. "render this patient's data — already
  fetched via the existing `fhir_client` proxy — as a PDF for download") rather than something
  `fhir-server` needs to own.
- **Port notes for fhir-gql (FastAPI/Python):** Use **`reportlab`** (mature, actively maintained,
  widely used for exactly this "generate a PDF from structured content" use case) or **`weasyprint`**
  if HTML/CSS-based document templates are preferred over a fluent Python API. Wrap in a
  `app/services/pdf_service.py` function returning `bytes`, mirroring `createPdf()`'s signature and
  return type. No urgency until a concrete PDF-export requirement exists (e.g. patient summary
  download) — this is infrastructure to reach for opportunistically, not proactively.
- **Priority:** Low — no current requirement; note for when a document-export feature is requested.

---

## 13. Data Warehouse Sync

> All entries in this section require direct PostgreSQL access (DuckDB attaches to the same
> `MedplumDatabaseConfig` connection used by `fhir-server`'s own Postgres) and therefore belong
> entirely to `fhir-server (data layer)`. None of it is portable to `fhir-gql` as designed; documented
> for completeness.

### Data Warehouse Table/Config Mapping
- **What it does:** Maps each FHIR resource type to its corresponding Postgres history table
  (`{ResourceType}_History`) and the lowercased Iceberg/Parquet table name that data gets exported to,
  with include/exclude resource-type filtering, and builds the `postgresql://` connection URI (with SSL
  params and a `statement_timeout` GUC) that DuckDB uses to attach to the source database.
- **Source files:** `src/data-warehouse/config.ts` — `getWarehouseSyncPostgresTableNames()`,
  `toIcebergTableName()`, `buildPgConnectionURI()`, `appendMedplumDatabaseSslSearchParams()`,
  `WarehouseSourceTable` type, `DEFAULT_DW_DATABASE_STATEMENT_TIMEOUT` (5 minutes).
- **Belongs in:** `fhir-server (data layer)`.
- **Port notes for fhir-gql (FastAPI/Python):** N/A.
- **Priority:** N/A.

### Pluggable Warehouse Destination Abstraction (Local Parquet / S3 Tables Iceberg)
- **What it does:** A common `DataWarehouseDestination` interface with two implementations — write
  Parquet files to local disk (`LocalParquetWarehouseDestination`, useful for dev/testing or simple
  on-prem exports) or write directly into an AWS S3 Tables-managed Iceberg catalog
  (`S3TablesWarehouseDestination`, for production analytics pipelines) — so the sync engine (next entry)
  doesn't need to know which target it's writing to.
- **Source files:** `src/data-warehouse/destination.ts` — `DataWarehouseDestination` interface,
  `LocalParquetWarehouseDestination` class. `src/cloud/aws/data-warehouse-destination.ts` —
  `S3TablesWarehouseDestination` class. `src/cloud/aws/data-warehouse-client.ts` —
  `createS3TablesClient()`, `tableExists()`, `ensureNamespaceExists()`.
- **How it works:** The S3 Tables destination supports true incremental sync via a computed
  high-watermark predicate (`buildMaxLastUpdatedWatermarkPredicate` — only rows newer than
  `MAX(last_updated)` already present in the target, correctly handling the empty-table/NULL-watermark
  case via three-valued SQL logic); the local Parquet destination currently always does a full export
  (documented as a known TODO — no watermark tracking against existing Parquet output yet).
- **Belongs in:** `fhir-server (data layer)`.
- **Port notes for fhir-gql (FastAPI/Python):** N/A — no analog needed in `fhir-gql`.
- **Priority:** N/A.

### DuckDB-Based Incremental Sync Engine
- **What it does:** The actual sync execution: spins up an ephemeral local DuckDB instance per run,
  attaches the source Postgres database read-only via DuckDB's `postgres` extension, runs a
  per-table `SELECT ... INSERT INTO`/`COPY ... TO PARQUET` against each configured resource type's
  history table (applying the incremental watermark/start-date predicate), and reports per-table row
  counts and timing.
- **Source files:** `src/data-warehouse/sync.ts` — `syncData()`, `runWarehouseTableSync()`,
  `buildWarehouseSourcePredicate()`. `src/data-warehouse/warehouse-sql.ts` — SQL-builder helpers
  (`buildSelectFromHistoryTableQuery()`, `buildInsertIntoSelectQuery()`, `buildCopySelectToParquetQuery()`,
  `buildManagedIcebergSetupQueries()`, `buildDuckdbPostgresAttachQuery()`, etc.).
- **How it works:** Uses DuckDB purely as a zero-install ETL engine — it never persists data itself
  (each run gets a fresh temp directory, deleted afterward), just streams rows from the attached
  Postgres source, extracts `meta.project` out of the JSON `content` column via DuckDB's
  `json_extract_string`, and writes to whichever destination implementation is configured. This
  entirely avoids requiring `fhir-server` to run its own ETL/export code — DuckDB does the heavy lifting
  of reading+transforming+writing in one process.
- **Belongs in:** `fhir-server (data layer)`.
- **Port notes for fhir-gql (FastAPI/Python):** N/A — `fhir-gql` has no Postgres to sync from. If this
  capability is ever needed on the Python side (e.g. `fhir-server` is Python), `duckdb`'s Python
  bindings support the identical `ATTACH ... (TYPE postgres, READ_ONLY)` + `COPY ... TO PARQUET`
  pattern directly, so the approach ports cleanly language-wise even though it doesn't apply to
  `fhir-gql`'s own codebase.
- **Priority:** N/A.

### AWS S3 Tables Client Helpers
- **What it does:** Small idempotent AWS SDK wrappers for checking whether an Iceberg table/namespace
  already exists in S3 Tables before the sync engine attempts to write to it.
- **Source files:** `src/cloud/aws/data-warehouse-client.ts` — `createS3TablesClient()`,
  `tableExists()`, `ensureNamespaceExists()`.
- **Belongs in:** `fhir-server (data layer)`.
- **Port notes for fhir-gql (FastAPI/Python):** N/A.
- **Priority:** N/A.

---

## 14. Misc Utilities

### Outbound URL / SSRF Validation
- **What it does:** Validates a URL before the server makes an outbound HTTP request to it (webhook
  delivery, external auth provider metadata fetch, etc.), enforcing HTTPS-only by default and rejecting
  requests to `localhost`, loopback, private, link-local, multicast, and other non-globally-routable IP
  ranges — a standard SSRF (Server-Side Request Forgery) defense.
- **Source files:** `src/util/url.ts` — `validateOutboundUrl()`, `isUnsafeHostname()`,
  `isUnsafeIpAddress()`, `OutboundUrlValidationOptions` (`allowHttp`, `allowUnsafeHostname` escape
  hatches for trusted/dev contexts).
- **How it works:** Uses `ipaddr.js` to parse and classify IP addresses by range
  (`parsedAddress.range() !== 'unicast'` catches private/reserved/loopback/multicast in one check),
  plus an explicit check for the IPv4 benchmarking range `198.18.0.0/15` (used in test/lab networks,
  not caught by standard "unicast" classification) and IPv6-bracket stripping for hostname comparison.
- **Belongs in:** `fhir-gql (middleware)` — directly relevant the moment `fhir-gql` makes *any* outbound
  call driven by user/tenant-controlled input (webhook URLs, external auth issuer URLs, etc.); today
  `fhir-gql`'s only outbound call is to the fixed, operator-configured internal
  connector `base_url` (`configs/connectors/internal.yaml`) and
  `IAM_JWKS_URL`, which aren't attacker-controlled, so there's no active SSRF surface yet — but this
  becomes essential the moment any user-supplied URL is fetched server-side.
- **Port notes for fhir-gql (FastAPI/Python):** Use the stdlib `ipaddress` module
  (`ip.is_private`/`is_loopback`/`is_link_local`/`is_multicast`/`is_reserved` cover the same ranges
  `ipaddr.js`'s `range() !== 'unicast'` check does) plus a `urllib.parse.urlparse` HTTPS-scheme check.
  A ~20-line `app/core/url_validation.py` with a `validate_outbound_url(url: str, allow_http: bool =
  False) -> str` function directly mirrors this file. Add it *before* any feature that fetches a
  user-supplied URL is implemented, not after.
- **Priority:** Medium — no active need today, but cheap to write and important to have *ready* before
  the first feature that fetches a tenant-supplied URL ships (retrofitting SSRF protection after such a
  feature exists is a much easier security review finding to miss).

### Path-Tracking Utilities for Structured Validation Errors
- **What it does:** A family of small helpers that annotate in-memory FHIR objects with their original
  JSON-path location (`Patient.contact[1].telecom[0]`) as they're extracted/filtered/transformed, so
  validation error messages can point precisely at the offending element instead of a generic
  "invalid extension" message. `LayeredDict` is a related but distinct utility: an immutable,
  copy-on-write "stack of overlapping partial objects" (each layer optionally path-annotated) used to
  build up a merged configuration/context object from multiple sources while still being able to trace
  which layer contributed which key.
- **Source files:** `src/util/withpath.ts` — `withPath()`, `getPath()`, `withPaths()`,
  `filterWithPaths()`, `copyPaths()`, `WithPath<T>` type (path stored under a non-enumerable `Symbol`
  key so it doesn't leak into normal iteration/serialization). `src/util/layereddict.ts` —
  `LayeredDict<T>` class (`empty()`, `from()`, `addLayer()`, `prependLayer()`, `patchLayer()`, `get()`,
  `getPath()`, `refine()`, `flatten()`). `src/util/extension.ts` — `getExtensions()` (path-aware
  multi-match extension lookup, built on `withPath`), `assertExtensionBoolean()`/`assertExtensionCode()`/
  `assertExtensionDuration()`/`assertExtensionReference()`/`assertExtensionTime()` (TypeScript assertion
  functions that narrow an extension's type and throw a path-annotated `OperationOutcomeError` if the
  expected value field is missing/wrong-typed).
- **How it works:** The `Symbol`-keyed path annotation is the key trick: it lets a "traceable" object
  be passed through completely ordinary array/object operations (spread, `.filter()`, `.map()`) without
  any special-cased traversal API, while still being retrievable via `getPath()` wherever error
  reporting needs it.
- **Belongs in:** `fhir-gql (middleware)` — this class of utility is about producing precise, debuggable
  validation error messages for FHIR resource *content*, which is squarely something a middleware layer
  validating/transforming resources on the way through would want, independent of persistence.
- **Port notes for fhir-gql (FastAPI/Python):** Pydantic already provides equivalent (arguably better)
  machinery natively: validation errors from a Pydantic model automatically include a `loc` tuple
  (the exact field path) in `ValidationError.errors()`, without needing a hand-rolled `Symbol`-based
  path-tracking system. `app/schemas/patient/fhir_schemas.py` and friends should lean on Pydantic's
  built-in error `loc` reporting rather than porting this pattern — it's solving a problem the Python
  stack's chosen validation library already solves more idiomatically. The `LayeredDict` "traceable
  config-merge" idea has no direct Pydantic equivalent, but is only useful if `fhir-gql` starts merging
  configuration from multiple runtime sources (it currently doesn't beyond `pydantic-settings`' own
  env/`.env` layering, which already tracks provenance internally).
- **Priority:** Low — Pydantic's native validation-error `loc` reporting already covers the core need;
  no action required.

### General-Purpose Small Utilities
- **What it does:** A grab-bag of small, broadly-reusable helpers with no FHIR- or infra-specific
  behavior:
  - `flatMapMax()` (`src/util/array.ts`) — `flatMap` that stops early once a max result count is
    reached, useful for capped search-result assembly.
  - `MockConsole` (`src/util/console.ts`) — a `console.log`-compatible test double that captures
    messages to an array instead of printing, for asserting on log output in tests.
  - `addMinutes()`, `areIntervalsOverlapping()`, `clamp()`, `earliest()`, `latest()`
    (`src/util/date.ts`) — small `date-fns`-style interval/date arithmetic helpers (used e.g. for
    scheduling/slot-overlap logic).
  - `readStreamToString()` (`src/util/streams.ts`) — buffers a Node `Readable` stream fully into a
    UTF-8 string.
  - `formatDuration()` (`src/util/time.ts`) — formats a nanosecond duration into a human-readable
    string with the appropriate SI time-unit prefix (ns/µs/ms/s).
  - `toCodeableReferenceLike()`, `isCodeableReferenceLikeTo()`, `extractReferencesFromCodeableReferenceLike()`
    (`src/util/servicetype.ts`) — an R4-compatibility shim representing R5's
    `CodeableReference<HealthcareService>` as an R4 `CodeableConcept` + extension, specific to
    Medplum's `Schedule.serviceType` handling.
  - `getServerVersion()` (`src/util/version.ts`) — strips any pre-release suffix
    (`-beta`, `-rc1`, ...) off the running server's semver version string, used throughout the job
    queue for `minServerVersion` compatibility checks (see Job Queue section).
  - `makeValidationMiddleware()` (`src/util/validator.ts`) — wraps an array of `express-validator`
    chains into a single Express middleware that runs them all, then converts any validation failure
    into a standard FHIR `invalidRequest` OperationOutcome response.
- **Source files:** `src/util/array.ts`, `src/util/console.ts`, `src/util/date.ts`,
  `src/util/streams.ts`, `src/util/time.ts`, `src/util/servicetype.ts`, `src/util/version.ts`,
  `src/util/validator.ts`.
- **Belongs in:** Mostly `infra/ops (applies to both)` as generic-utility patterns; `servicetype.ts` is
  `fhir-server (data layer)`-specific (tied to Medplum's `Schedule`/`HealthcareService` R4-compat
  shim, not applicable since `fhir-gql` only implements `Patient` today).
- **Port notes for fhir-gql (FastAPI/Python):** None of these need direct porting — Python's standard
  library and existing ecosystem already cover each case natively and typically better: `itertools`
  for capped-iteration patterns, stdlib `unittest.mock`/`caplog` fixture for log capture in tests
  (pytest), `datetime`/`dateutil` for interval math, `humanize` (PyPI) for duration formatting if ever
  needed, `packaging.version.Version(...).base_version` for stripping pre-release suffixes off a
  version string (equivalent to `getServerVersion()`), and FastAPI/Pydantic's native request-body
  validation (already used throughout `app/schemas/`) in place of `makeValidationMiddleware()`'s
  `express-validator` wrapping. No gap here — this section is included for completeness of the file
  read, not because any action is warranted.
- **Priority:** Low — no porting need; Python's stdlib/ecosystem already covers each of these more
  idiomatically than a direct port would.

---

## Summary Table

| Feature | Priority | Belongs in |
|---|---|---|
| FHIR Bulk Data Export Status & Cancellation API | Low | fhir-gql (proxy) / fhir-server (execution) |
| Generic Async Job Status API | Low→Medium | fhir-gql (proxy) / fhir-server (state) |
| FHIR Interaction Quota (cost-weighted rate limiting) | Medium | fhir-gql (middleware) |
| Schema Diffing Migration Generator | N/A | fhir-server (data layer) |
| Pre-Deploy vs Post-Deploy Migration Phasing | N/A | fhir-server (data layer) |
| Migration CLI Runner & File Generation | N/A | fhir-server (data layer) |
| Migration Versioning & First-Boot Detection | N/A | fhir-server (data layer) |
| Post-Deploy Migration Execution Framework | N/A | fhir-server (data layer) |
| Non-Blocking Schema Change Helpers | N/A | fhir-server (data layer) |
| Definitional Resource Seeding | N/A | fhir-server (data layer) |
| BullMQ Queue Registry & Worker Bootstrapping | Low→Medium | infra/ops (both) |
| Verbose Queue Event Logging | Low | infra/ops (both) |
| Job Compatibility & Version Gating | Low | infra/ops (both) |
| Full-Database Reindex Worker | N/A | fhir-server (data layer) |
| Account/Compartment Reassignment Worker | N/A | fhir-server (data layer) |
| AWS Lambda Version Cleanup Worker | N/A | fhir-server (data layer) |
| OpenTelemetry SDK Instrumentation | **High** | infra/ops (both) |
| Custom Metrics Helpers & Heartbeat Gauges | **High** | infra/ops (both) |
| Multi-Source Config Loader | Low | fhir-gql (middleware) |
| Typed Config Schema | Low | fhir-gql (middleware) |
| Config Defaults & Type Coercion Utilities | Low | fhir-gql (middleware) |
| Data Warehouse Config Validation | Low | fhir-server (data layer) |
| Per-User Redis-Backed Key-Value Store | Medium | fhir-gql (middleware) |
| Transactional Email Sending | Medium | fhir-gql (middleware) |
| Email API Endpoint | Medium | fhir-gql (middleware) |
| JSON Patch Application | Low | fhir-server (data layer) |
| Audit Event Construction Helpers | **High** | fhir-gql (log stream) / fhir-server (persisted resource) |
| Bot/Subscription Audit Event Recording | N/A | fhir-server (data layer) |
| PDF Document Generation | Low | fhir-gql (middleware) |
| Data Warehouse Table/Config Mapping | N/A | fhir-server (data layer) |
| Pluggable Warehouse Destination Abstraction | N/A | fhir-server (data layer) |
| DuckDB-Based Incremental Sync Engine | N/A | fhir-server (data layer) |
| AWS S3 Tables Client Helpers | N/A | fhir-server (data layer) |
| Outbound URL / SSRF Validation | Medium | fhir-gql (middleware) |
| Path-Tracking Utilities for Validation Errors | Low | fhir-gql (superseded by Pydantic) |
| General-Purpose Small Utilities | Low | infra/ops (both, no porting needed) |

---

## Recommended Next Steps

The clearest, highest-leverage gap this survey surfaces is **observability**: `fhir-gql` sits between
clients and `fhir-server` with zero tracing and zero metrics today, only structured logs — meaning
there is currently no way to see request latency broken down across JWT validation, RBAC checks, the
downstream `fhir-server` round-trip, and Redis rate-limit calls. Standing up
`opentelemetry-instrumentation-fastapi` + `-httpx` + `-redis` with an OTLP exporter (gated behind an
optional env var exactly as Medplum does, so local dev is unaffected) should be the first concrete
follow-up from this report, paired with a small `app/core/metrics.py` publishing connection-pool and
rate-limit gauges. Close behind that, **standardizing an audit-event vocabulary** on top of the
existing JSON logger (reusing HL7's own AuditEvent action/outcome codes rather than inventing new ones)
is a cheap, high-value addition given `fhir-gql` already owns every access-control decision worth
auditing. Everything in the migrations/seeding/reindex/data-warehouse space is correctly out of scope
for `fhir-gql`'s architecture and requires no action — those responsibilities belong entirely to
whatever owns `fhir-server`'s PostgreSQL schema. The remaining items (key-value store, cost-weighted
FHIR quota, transactional email, SSRF-safe URL validation) are all self-contained, low-risk features
that extend infrastructure `fhir-gql` already owns (Redis, auth context) and can be picked up
opportunistically as real product requirements for them appear — none are blocking today given the
project's current single-resource, read-only scope.
