# 09 — Server Bootstrap & Cross-Cutting Infrastructure

Comparison scope: Medplum's Express.js server bootstrap layer
(`packages/server/src/{app,async-batch,constants,context,cors,database,healthcheck,heartbeat,index,logger,migration-sql,openapi,ratelimit,redis,request-context-store,server-registry,traceparent,wellknown,seed}.ts`)
against fhir-gql's FastAPI bootstrap layer (`app/main.py`, `app/core/*`, `app/middleware/*`).

**Framing reminder:** fhir-gql is a middleware/orchestration layer in front of a separate
downstream "fhir-server" that owns PostgreSQL persistence. Medplum's server *is* the FHIR
server and owns Postgres directly — so several Medplum concerns (`database.ts`,
`migration-sql.ts`, `seed.ts`) are structurally out of scope for fhir-gql and are documented
below as explicit non-gaps, not missing features.

---

### Application Bootstrap / Composition Root
- **What it does:** Assembles the HTTP application: registers middleware in order, mounts
  sub-routers, wires startup/shutdown of every subsystem (database, Redis, workers, binary
  storage, heartbeat, keys), and returns a ready-to-listen server object.
- **Source files:** `app.ts` — `initApp()` (assembles the Express app and middleware
  pipeline, returns an `http.Server`), `initAppServices()` (starts every backing subsystem:
  structure definitions, Redis, database + migrations, workers, seed, JWT keys, binary
  storage, heartbeat, OTel heartbeat, server registry, post-deploy migrations),
  `shutdownApp()` (reverse-order teardown).
- **How it works:** `initApp` is called once from `index.ts` with an `Express` instance and
  parsed config. It layers ~15 pieces of middleware (security headers, CORS, compression,
  request logging, request-context attachment, rate limiting, body parsers) before mounting
  ~18 domain sub-routers under `/api/` and `/`. `initAppServices` is a flat sequential
  `await` chain — each subsystem must finish initializing before the next starts (e.g.
  Redis before database, since migrations may depend on advisory locks; workers before seed,
  since seeding disables background jobs explicitly instead).
- **Gap vs fhir-gql today:** **Has an equivalent.** `app/main.py` is the direct analog:
  module-level `FastAPI()` construction, `setup_logging()` called first (mirrors
  Medplum calling `globalLogger`/log-level setup before `initAppServices`), an
  `asynccontextmanager` `lifespan()` for startup/shutdown (Redis ping, FhirClient/Redis
  close), exception handlers, two middleware layers, and router mounting — all in one file,
  same as `app.ts`+`index.ts` combined. fhir-gql's version is proportionally simpler because
  it owns far fewer subsystems (no DB pool, no worker queue, no binary storage, no WebSocket
  server, no key management — those live in the downstream fhir-server).
- **Port notes for fhir-gql (FastAPI/Python):** No action needed structurally. As fhir-gql
  grows beyond the patient-only slice, keep startup/shutdown ordering explicit in `lifespan()`
  the way Medplum does in `initAppServices`/`shutdownApp` (sequential `await`, reverse-order
  teardown) rather than letting it sprawl into scattered `@app.on_event` calls (which are
  deprecated in modern FastAPI anyway — `lifespan` is already the correct idiom in use).
- **Priority:** Low — already covered structurally; revisit only as new subsystems are added.

---

### Process Entrypoint, Signal Handling & Graceful Shutdown
- **What it does:** The actual OS process entrypoint: starts the HTTP listener, installs
  global crash handlers so one bad promise/exception doesn't necessarily kill the process,
  and drains in-flight requests on SIGTERM/SIGINT before exiting.
- **Source files:** `index.ts` — `main()` (creates the Express app, starts `server.listen`,
  installs `process.on('unhandledRejection', ...)` / `process.on('uncaughtException', ...)`,
  wires `http-graceful-shutdown`), `runFromCli()` (CLI entry with fatal-error handling).
- **How it works:** `gracefulShutdown(server, {...})` from the `http-graceful-shutdown`
  package intercepts SIGTERM/SIGINT, stops accepting new connections, waits up to
  `shutdownTimeoutMilliseconds` for in-flight requests to complete, then calls
  `shutdownApp()`. The `uncaughtException` handler special-cases two known-benign Postgres/
  OTel errors (connection-lost, malformed X-Forwarded-For) to avoid killing the process on
  transient noise, and otherwise exits only after `exitAfterStdoutDrain()` flushes the log
  buffer (`logger.ts`'s `drainStdout`) so the fatal log line isn't lost to buffering.
- **Gap vs fhir-gql today:** **Lacks an equivalent — but largely by design.** fhir-gql relies
  on `uvicorn` for the process entrypoint (`uvicorn app.main:app`), which already handles
  SIGTERM/SIGINT-triggered graceful shutdown of the ASGI server and invokes the `lifespan`
  shutdown block (Redis/FhirClient close) — so the *connection-draining* half of this feature
  is covered. What's missing: (1) no global handler for unhandled exceptions in fire-and-forget
  asyncio tasks (Python's analog of `unhandledRejection` is a loop exception handler via
  `asyncio.get_event_loop().set_exception_handler(...)`, which fhir-gql does not set); (2) no
  explicit stdout-flush-before-exit guarantee (less critical for Python's line-buffered
  `StreamHandler`, but still a real gap under `multiprocessing`/`gunicorn` worker kills); (3) no
  special-casing of known-benign errors that would otherwise crash a worker.
- **Port notes for fhir-gql (FastAPI/Python):** If/when background tasks (not just request
  handlers) are introduced, set a custom asyncio exception handler in the `lifespan` startup
  block: `asyncio.get_event_loop().set_exception_handler(handler)` that logs via
  `get_logger(__name__).error(...)` instead of letting the default handler silently print to
  stderr outside the JSON log format. Uvicorn's `--timeout-graceful-shutdown` flag (or
  `Config(timeout_graceful_shutdown=...)`) is the direct analog of Medplum's
  `shutdownTimeoutMilliseconds`.
- **Priority:** Low — uvicorn already covers the load-bearing part (drain + shutdown hook);
  the remaining gap (asyncio exception handler) only matters once background tasks exist.

---

### Standard Security Response Headers
- **What it does:** Sets a fixed set of hardening headers (Cache-Control, HSTS, CSP,
  Permissions-Policy, Referrer-Policy, X-Content-Type-Options, X-Frame-Options,
  X-XSS-Protection) on every response, unconditionally.
- **Source files:** `app.ts` — `standardHeaders()` middleware, registered first via
  `app.use(standardHeaders)` before CORS or anything else.
- **How it works:** A plain Express middleware that calls `res.set(...)` for each header and
  calls `next()`. CSP is maximally restrictive (`default-src 'none'`) since this is a pure API
  server with no HTML views to allow. HSTS is only set when `config.baseUrl` is `https://`
  (avoids breaking local HTTP dev).
- **Gap vs fhir-gql today:** **Lacks an equivalent entirely.** Neither `app/main.py` nor
  `app/core/middleware.py` sets any hardening headers — no CSP, no HSTS, no
  X-Content-Type-Options, no X-Frame-Options, no Referrer-Policy, no cache-control
  suppression. Every response currently relies on client/browser defaults.
- **Port notes for fhir-gql (FastAPI/Python):** Add a small `SecurityHeadersMiddleware`
  (same `BaseHTTPMiddleware` pattern as `RequestIdMiddleware` in
  `app/core/middleware.py`) that sets the same header set on `response.headers` before
  returning. Gate HSTS on `settings.ENVIRONMENT == "production"` (mirrors Medplum's
  `https://` check) since local dev likely runs plain HTTP. This is cheap, has no
  dependencies, and directly closes a real security gap — note GraphiQL's browser UI
  (mounted at `/graphql`, see `app/gql/context.py`) needs `frame-ancestors`/CSP kept loose
  enough not to break its own asset loading; scope the strictest CSP to `/api/v1/*` if
  GraphiQL needs inline scripts.
- **Priority:** High — zero-cost, well-understood hardening that is currently entirely absent;
  the kind of gap a security review would flag immediately.

---

### CORS Policy
- **What it does:** Determines, per-request, whether a browser-origin cross-origin request
  is allowed, and if so, which headers/credentials/cache duration to advertise back.
- **Source files:** `cors.ts` — `corsOptions` (a `cors.CorsOptionsDelegate` consumed by the
  `cors` npm package in `app.ts`'s `app.use(cors(corsOptions))`), `isOriginAllowed()`,
  `isPathAllowed()`.
- **How it works:** For every request, checks the `Origin` header against
  `config.appBaseUrl` prefix match or a comma-separated `config.allowedOrigins` allowlist
  (or `*` for allow-all). Separately, only a fixed set of path prefixes (`/fhir/`, `/auth/`,
  `/oauth2/`, etc.) are CORS-eligible at all — this prevents CORS from being enabled on
  internal/admin paths not meant for browser access. When allowed, it echoes the exact
  origin back (required for `credentials: true` to work — `*` cannot be combined with
  credentialed requests), exposes response headers clients need to read
  (`Content-Location`, `ETag`, `Location`, `RateLimit`), and caches the preflight for 600s.
- **Gap vs fhir-gql today:** **Lacks an equivalent entirely.** No CORS middleware is
  registered anywhere in `app/main.py`, `app/core/*`, or `app/middleware/*` (confirmed via
  search — no `CORSMiddleware` import, no `cors` reference in the codebase). Any browser
  client on a different origin than the API (which will be true for essentially any real
  frontend deployment) currently cannot call this API from JavaScript at all — or, if a
  proxy/gateway in front of it happens to inject permissive CORS headers, that would be an
  unreviewed, uncontrolled hole rather than an intentional policy.
- **Port notes for fhir-gql (FastAPI/Python):** Add `starlette.middleware.cors.CORSMiddleware`
  via `app.add_middleware(CORSMiddleware, allow_origins=[...], allow_credentials=True,
  allow_methods=[...], allow_headers=[...], expose_headers=["X-Request-ID", "X-RateLimit-Limit",
  "X-RateLimit-Remaining", "X-RateLimit-Window"])`. Source the origin allowlist from
  `app/config.py` (add `ALLOWED_ORIGINS: list[str]` to `Settings`, mirroring
  `IAM_JWKS_URL`/`IAM_ISSUER`'s pattern of env-driven config) rather than hardcoding.
  `CORSMiddleware` does not support Medplum's path-prefix restriction natively — if
  fhir-gql wants CORS scoped away from certain paths, wrap it in a small dispatcher or
  simply accept origin-only scoping (simpler and usually sufficient, since `/api/v1/*` and
  `/graphql` are the only browser-facing surfaces here). Must be registered before
  `RateLimitMiddleware`/`RequestIdMiddleware` in `add_middleware` order — Starlette applies
  middleware in reverse-registration order, and CORS preflight (`OPTIONS`) requests should
  be answered without hitting rate-limit or request-id logic that expects a real request.
- **Priority:** High — this blocks basic browser-based frontend integration entirely; not a
  hardening nice-to-have but a functional blocker once any web client exists.

---

### Response Compression
- **What it does:** Gzip/deflate-compresses response bodies for clients that advertise
  `Accept-Encoding` support, reducing payload size for large FHIR Bundles.
- **Source files:** `app.ts` — `app.use(compression())` (the `compression` npm package,
  registered right after CORS).
- **How it works:** Standard Express compression middleware — transparently wraps
  `res.write`/`res.end`, negotiates encoding via the request's `Accept-Encoding` header.
- **Gap vs fhir-gql today:** **Lacks an equivalent.** No `GZipMiddleware` or equivalent is
  registered in `app/main.py`.
- **Port notes for fhir-gql (FastAPI/Python):** Add
  `from starlette.middleware.gzip import GZipMiddleware; app.add_middleware(GZipMiddleware, minimum_size=1000)`
  — a one-line, dependency-free addition (`GZipMiddleware` ships with Starlette). Particularly
  valuable here since GraphQL responses and Patient Bundles can be large.
- **Priority:** Medium — low implementation cost, real bandwidth/latency benefit for large
  FHIR payloads, but not a correctness or security issue like the two items above.

---

### Global/Central Error Handling
- **What it does:** Converts every kind of error (domain `OperationOutcome`s, malformed
  request bodies, oversized payloads, client aborts, unsupported media types, unexpected
  bugs) into a consistent HTTP response shape, in one place, so route handlers don't need
  their own try/catch boilerplate.
- **Source files:** `app.ts` — `errorHandler()` (registered last via `app.use(errorHandler)`,
  Express's convention for a 4-arg function to be treated as an error handler).
- **How it works:** A cascade of `if` checks matches on error shape: `err.outcome` /
  `err.resourceType === 'OperationOutcome'` (domain errors, mirrors fhir-gql's `AppError`
  pattern) get serialized via `sendOutcome`; specific `body-parser` error `.type` values
  (`entity.parse.failed`, `entity.too.large`, `stream.not.readable`) get mapped to specific
  FHIR `OperationOutcome`s; client-disconnect errors (`request.aborted`, `ECONNRESET`) are
  silently swallowed rather than logged as failures; everything else falls through to a
  generic 500 with no internal detail leaked. It also calls `closeRequestContext()` first to
  dispose the `AsyncLocalStorage`-scoped `Repository`/DB client tied to this request.
- **Gap vs fhir-gql today:** **Has an equivalent, functionally close.** `app/core/errors.py`
  registers four handlers exactly matching this cascade's structure:
  `app_error_handler` (for `AppError`, the same role as `err.outcome` domain errors),
  `http_exception_handler` (for FastAPI's `HTTPException`), `validation_exception_handler`
  (for `RequestValidationError` — this is the Pydantic/422 case, which Express doesn't have
  a direct analog for since it isn't schema-validating bodies the same way), and
  `unhandled_exception_handler` (catch-all 500, same "no internal detail leaked" contract as
  Medplum's fallback). The one behavioral difference: Medplum explicitly detects and
  no-ops on client-disconnect errors (`request.aborted`/`ECONNRESET`) so they don't pollute
  error logs/alerting as false-positive 500s; fhir-gql's `unhandled_exception_handler` would
  currently log a client-disconnect the same as a real bug (Starlette/uvicorn typically
  raises `anyio.ClosedResourceError` / cancels the task rather than routing through
  exception handlers on disconnect, so this may be a non-issue in practice, but it's worth
  verifying under load).
- **Port notes for fhir-gql (FastAPI/Python):** No structural change needed. If client
  disconnects are observed polluting logs/alerts, special-case
  `starlette.requests.ClientDisconnect` in `unhandled_exception_handler` the same way
  Medplum special-cases `err.type === 'request.aborted'`.
- **Priority:** Low — already well covered; the disconnect-handling nuance is a "verify, don't
  assume" item rather than a known gap.

---

### Request-Scoped Context Propagation (AsyncLocalStorage vs contextvars)
- **What it does:** Makes a per-request bundle of state (request ID, trace ID, a
  structured logger pre-bound with those IDs, and — when authenticated — the caller's auth
  state and DB repository) implicitly available to *any* function in the call stack for that
  request, without threading it through every function signature as an explicit parameter.
- **Source files:** `request-context-store.ts` — `requestContextStore` (a Node
  `AsyncLocalStorage<IRequestContext>` singleton), `IRequestContext` interface. `context.ts`
  — `RequestContext` / `AuthenticatedRequestContext` classes (the concrete values stored),
  `attachRequestContext()` (Express middleware that authenticates the request and calls
  `requestContextStore.run(ctx, next)` to scope everything downstream), `getRequestContext()`
  / `tryGetRequestContext()` / `getAuthenticatedContext()` (accessors used from arbitrarily
  deep call sites — e.g. `logger.ts`'s `getLogger()` and `ratelimit.ts`'s
  `getRateLimitForRequest()` both read the ambient context this way).
- **How it works:** `AsyncLocalStorage` is Node's mechanism for context that survives across
  `await` boundaries and callback chains within one logical async execution — conceptually
  identical to Python's `contextvars.ContextVar`, which is exactly what `asyncio`/Starlette
  use internally for the same purpose. `attachRequestContext` runs *before* rate limiting and
  route handlers, meaning `getLogger()`/`getRateLimiter()` deep inside business logic can
  fetch "the current request's" logger/auth state without it being passed down explicitly.
  `AuthenticatedRequestContext` additionally carries a live `Repository` (DB access scoped
  to the caller's project/permissions) and `Symbol.dispose`-based cleanup, called explicitly
  in the error handler and success path.
- **Gap vs fhir-gql today:** **Partially has an equivalent, via a different mechanism.**
  fhir-gql uses `request.state` (Starlette's per-`Request`-object attribute bag) instead of
  `contextvars` — see `RequestIdMiddleware` setting `request.state.request_id` in
  `app/core/middleware.py`, and `get_current_user` setting `request.state.user`. This
  achieves the *same practical result* for anything that has access to the `Request` object
  (route handlers, middleware, `Depends()`-injected functions) — which covers the large
  majority of fhir-gql's code today. The gap is narrower than Medplum's: it only manifests
  for code that does *not* have the `Request` object threaded to it — e.g.
  `app/core/logging.py`'s `get_logger()` has no way to auto-bind `request_id` the way
  Medplum's `getLogger()` does; every call site must manually pass `extra={"request_id":
  request.state.request_id}` or the field is simply absent from that log line. Since
  `Container` (`app/di/container.py`) resolves services outside of any per-request scope
  (singletons wired once at startup), a service method several layers deep in
  `app.services.*` has no ambient way to know the current request ID/trace ID/user unless
  it's explicitly passed as a function argument.
- **Port notes for fhir-gql (FastAPI/Python):** Introduce a `contextvars.ContextVar` (e.g. in
  a new `app/core/request_context.py`, structurally parallel to `request-context-store.ts`)
  holding a small dataclass (`request_id`, `trace_id`, optionally `user_id`). Set it in
  `RequestIdMiddleware.dispatch` (`app/core/middleware.py`) via `token = ctx_var.set(ctx);
  try: ... finally: ctx_var.reset(token)` — `contextvars` correctly propagates across `await`
  in ASGI the same way `AsyncLocalStorage` does across Node's event loop, so this is a very
  close mechanical port. Then add a `logging.Filter` (or wrap `_JsonFormatter.format` in
  `app/core/logging.py`) that reads the `ContextVar` and injects `request_id`/`trace_id` into
  every log record automatically — removing the need for every call site to pass `extra={}`
  manually and closing the gap described above. This is the single most valuable structural
  improvement in this category: it's what makes Medplum's `getLogger()` "just work" from
  anywhere in the call stack.
- **Priority:** Medium — current `request.state`-based approach covers most real call sites
  today (this is a thin service with a shallow call stack), but the gap will grow as
  `app/services/*` business logic deepens and as background/async work (batch jobs, workers)
  is added, at which point there's no `Request` object to thread through at all.

---

### Request ID vs. Distributed Trace ID (traceparent propagation)
- **What it does:** Distinguishes between a per-hop **request ID** (unique to this service's
  handling of one HTTP call) and a cross-service **trace ID** (a single identifier that
  should stay constant as a logical operation crosses multiple services/hops), and knows how
  to extract the latter from three different industry-standard propagation headers.
- **Source files:** `traceparent.ts` — `parseTraceparent()` (parses the W3C
  `traceparent` header format per the Trace Context spec). `context.ts` — `getTraceId()`
  (tries `x-trace-id` first if it's a valid UUID, then falls back to parsing `traceparent`,
  then falls back to AWS's `x-amzn-trace-id` ALB format via `extractAmazonTraceId()`),
  `requestIds()` (generates a fresh `requestId` via `randomUUID()` on every call regardless
  of headers, but reuses an inbound trace ID if present — or mints a new one only if none of
  the three header formats matched).
- **How it works:** `traceparent`'s format is `version-traceId(32 hex)-parentId(16
  hex)-flags`, standardized by W3C so that OpenTelemetry, AWS X-Ray, Datadog, etc. can all
  interoperate. Unlike the request ID (always fresh per hop), the trace ID is meant to be
  the *same* value the client (or an upstream service) generated, propagated through every
  hop, so a single distributed operation can be reassembled from logs/traces across services
  by that one ID. `buildTracingExtension()` in `context.ts` also embeds `requestId`/`traceId`
  into outgoing FHIR resource `meta.extension` so the tracing IDs are recoverable even from
  the persisted resource itself.
- **Gap vs fhir-gql today:** **Lacks an equivalent entirely, though a close relative
  exists.** `RequestIdMiddleware` (`app/core/middleware.py`) implements only *half* of this
  pattern: it reads `X-Request-ID` and echoes it back, conflating "request ID" and "trace
  ID" into one field with no distinction. It does not parse or propagate the W3C
  `traceparent` header, does not understand AWS ALB's `X-Amzn-Trace-Id` format, and — because
  fhir-gql sits *in front of* a downstream fhir-server (i.e., it is itself a hop in a
  distributed call chain: client → fhir-gql → fhir-server) — this is exactly the topology
  where trace propagation matters most, yet nothing here forwards a trace ID to the
  downstream `FhirClient` calls either.
- **Port notes for fhir-gql (FastAPI/Python):** This is worth doing properly rather than
  patching `RequestIdMiddleware` in place, given fhir-gql's proxy position. Add a
  `get_trace_id(request)` helper mirroring `context.ts`'s `getTraceId()`: check `traceparent`
  first (a regex-parseable one-liner exactly like `traceparent.ts`'s
  `traceparentRegex`), and keep `X-Request-ID` as the per-hop ID (already implemented).
  Critically, propagate the resolved trace ID (as a `traceparent` header, W3C-compliant) on
  every outbound `FhirClient` call to the downstream fhir-server, so a single clinical
  operation is traceable end-to-end across both services in whatever log
  aggregation/APM tool is used. If OpenTelemetry is adopted later, this manual parsing
  becomes unnecessary (the `opentelemetry-instrumentation-fastapi`/`httpx` packages handle
  W3C trace-context propagation automatically) — but even without full OTel, the cheap regex
  parse + forwarding is worth having now given the proxy topology.
- **Priority:** Medium-High — directly relevant to fhir-gql's specific architecture (a
  middleware hop in front of another service) in a way it might not be for a standalone
  server; debugging a slow/failed request across both services is currently only possible by
  manually correlating timestamps.

---

### Structured Logging
- **What it does:** Emits every log line as structured, machine-parseable output with
  consistent base fields (timestamp, level, message) plus arbitrary caller-supplied metadata,
  suitable for direct ingestion into log aggregation systems.
- **Source files:** `logger.ts` — `globalLogger` (a `@medplum/core` `Logger` instance bound
  to `writeLineToStdout`), `getLogger()` (returns the current request-scoped logger if inside
  an `AsyncLocalStorage` context, else `globalLogger`), `writeLineToStdout()` /
  `drainStdout()` / `exitAfterStdoutDrain()` (backpressure-safe stdout writing + flush-before-exit).
- **How it works:** `Logger` (from the shared `@medplum/core` package, not shown here) takes
  a write function, static metadata, and a `LogLevel`; every `.info()`/`.error()` call merges
  its args into that static metadata and serializes to one line. Because `getLogger()` reads
  from `requestContextStore` (see prior section), every log call inside request handling
  automatically carries `requestId`/`traceId`/`projectId`/`profile` without the caller
  passing them — this is the payoff of the `AsyncLocalStorage` pattern.
- **Gap vs fhir-gql today:** **Has an equivalent, with one structural difference already
  covered above.** `app/core/logging.py`'s `setup_logging()` + `_JsonFormatter` +
  `get_logger()` is functionally equivalent to Medplum's `logger.ts` for the base case: JSON
  lines to stdout, `extra={}` fields promoted to top-level JSON keys (mirrors Medplum merging
  call-site metadata into the base record), exception tracebacks captured. The gap is exactly
  the one described in "Request-Scoped Context Propagation" above: fhir-gql's `get_logger()`
  has no ambient access to request ID/trace ID the way Medplum's does, since Python's version
  doesn't consult a `ContextVar`. There is also no `drainStdout`/flush-before-exit equivalent
  (see "Process Entrypoint" above).
- **Port notes for fhir-gql (FastAPI/Python):** Once the `ContextVar`-based request context
  from the earlier section exists, wire it into `_JsonFormatter.format()` (or a
  `logging.Filter` added in `setup_logging()`) so `request_id`/`trace_id` are injected
  automatically into `out` for every record — this single change is what makes fhir-gql's
  logging match Medplum's ergonomics without touching every call site.
- **Priority:** Medium — same priority and same underlying fix as the context-propagation
  gap; treat as one unit of work.

---

### Health Check Endpoint
- **What it does:** Reports whether the process and its critical dependencies (database,
  Redis) are actually reachable and responsive — not just whether the process is alive.
- **Source files:** `healthcheck.ts` — `healthcheckHandler()`, `getReservedDatabaseConnection()`
  (holds one long-lived pooled connection per pool, reused across health check calls rather
  than acquiring fresh each time — avoids exhausting the pool under frequent
  liveness/readiness polling), `cleanupReservedDatabaseConnections()`, `testPostgres()`,
  `testRedis()`.
- **How it works:** On each call, runs `SELECT 1` against the writer Postgres pool (and
  reader pool too, if a separate one is configured) and `PING` against *every* configured
  Redis instance (default, cache, rate-limit, pub/sub, background-jobs — see `redis.ts`),
  timing each round-trip and recording it as an OpenTelemetry gauge
  (`medplum.db.healthcheckRTT`, `medplum.redis.healthcheckRTT`). Returns a JSON body with a
  per-dependency boolean breakdown plus version/platform/runtime info — this is a genuine
  *readiness* check (can this instance actually serve traffic right now), not just liveness.
- **Gap vs fhir-gql today:** **Partially has an equivalent — narrower in scope.**
  `app/main.py`'s `GET /health` (see `health_check()`) is pure liveness: it returns
  `{"status": "ok", "req_id": ...}` unconditionally, with no check of Redis (despite Redis
  being pinged once at startup and stored on `app.state.redis` — that connectivity is never
  re-verified per health-check call) and no check of the downstream fhir-server's
  reachability (which, for a pure middleware/proxy service, is arguably the *most* important
  dependency to verify — if fhir-server is down, fhir-gql cannot serve any real traffic even
  though `/health` would report "ok").
- **Port notes for fhir-gql (FastAPI/Python):** Extend `health_check()` (or add a separate
  `/health/ready` distinct from a pure liveness `/health`, following the standard
  liveness-vs-readiness split many orchestrators expect) to: (1) `await
  request.app.state.redis.ping()` if present, wrapped in try/except so a Redis outage
  produces a degraded-but-informative response rather than a raw 500; (2) issue a lightweight
  request to the downstream fhir-server's own health endpoint via `FhirClient` (see
  `app/di/core.py`/`CoreContainer` for how it's constructed) with a short timeout. Return a
  structured body mirroring Medplum's `{ok, redis: {...}, fhirServer: bool}` shape rather
  than a flat string, so monitoring can alert on *which* dependency is down. Keep the
  existing unauthenticated `/health` (no `Depends(get_current_user)`) for the liveness case —
  this matches Medplum's `/healthcheck` also being registered before `authenticateRequest`.
- **Priority:** High — for a middleware service whose entire job is proxying to a downstream
  server, a health check that doesn't verify that downstream connection provides a false
  sense of security to whatever's polling it (load balancer, k8s readiness probe, etc.).

---

### Heartbeat / Periodic Event Bus
- **What it does:** A single shared timer that fires a `heartbeat` event on a fixed interval
  (default 10s), which other subsystems subscribe to instead of each running their own
  `setInterval`.
- **Source files:** `heartbeat.ts` — `heartbeat` (a `TypedEventTarget`), `initHeartbeat()`,
  `cleanupHeartbeat()`, `DEFAULT_HEARTBEAT_MS`.
- **How it works:** Wraps Node's `setInterval` in an `EventTarget` so multiple independent
  consumers (`server-registry.ts`'s heartbeat listener, WebSocket keep-alive pings via
  `ws/routes.ts` — not read as part of this assignment but referenced by `app.ts`'s
  `initWebSockets`, and OTel's periodic metric flush via `otel/otel.ts`) can each register a
  listener rather than each maintaining a separate timer. This is a resource-efficiency and
  coordination pattern, not a correctness-critical one.
- **Gap vs fhir-gql today:** **Lacks an equivalent — but has no current consumer that would
  need it.** fhir-gql has no WebSocket server, no multi-instance server registry (see next
  section), and no periodic metrics flush, so there is nothing today that would subscribe to
  a shared heartbeat.
- **Port notes for fhir-gql (FastAPI/Python):** No action needed now. If/when fhir-gql adds
  WebSocket subscriptions (FastAPI supports this natively) or the server-registry pattern
  below, revisit — a simple `asyncio.create_task` loop dispatching to a small pub/sub of
  async callbacks (or just `asyncio`'s own `Event`/callback registration) is the direct port
  of `TypedEventTarget` + `setInterval`.
- **Priority:** Low — no current consumer; purely a "know this exists if you build X" note.

---

### Multi-Instance Server Registry (Cluster Coordination)
- **What it does:** Lets each server process announce "I'm alive, here's my version" into a
  shared Redis-backed registry with a TTL, so any instance (or an admin endpoint) can query
  "what instances are currently running, and are they all on the same version" — useful
  during rolling deploys to detect a stuck/mixed-version rollout.
- **Source files:** `server-registry.ts` — `setServerRegistryPayload()`,
  `initServerRegistryHeartbeatListener()` (subscribes to the `heartbeat` event above and
  re-announces on every tick), `getRegisteredServers()`, `getClusterStatus()` (computes
  version histogram, oldest/newest version, homogeneity).
- **How it works:** Each instance writes `medplum:server-registry:<uuid>` → JSON payload
  (`{id, firstSeen, lastSeen, version, fullVersion}`) to the "cache" Redis instance with a
  60-second TTL, refreshed every heartbeat (10s default) — so an instance that crashes or is
  killed simply ages out of the registry within a minute with no explicit deregistration
  needed. This is *not* leader election (no consensus, no single elected leader) — it's pure
  instance discovery/observability, likely surfaced through an admin API to answer "is my
  rollout done."
- **Gap vs fhir-gql today:** **Lacks an equivalent entirely.** No mechanism exists to
  discover how many fhir-gql instances are running or whether they're on consistent
  versions. Note this is genuinely optional infrastructure, not a correctness requirement —
  Medplum's own rate limiting and everything else that matters for multi-instance
  correctness runs through Redis directly (see `RateLimitMiddleware`'s Redis-sorted-set
  approach in `app/middleware/rate_limit.py`, already multi-instance-safe on its own) rather
  than depending on the registry.
- **Port notes for fhir-gql (FastAPI/Python):** Low-value unless fhir-gql operates a
  non-trivial fleet (multiple replicas with independent deploy timing) and needs rollout
  visibility. If pursued: a `redis_client.setex(f"fhir-gql:registry:{uuid4()}", 60,
  json.dumps(payload))` on a periodic `asyncio` task, using the existing `redis_client`
  singleton (`app/core/redis.py`) — this is a direct, low-effort port if the need arises,
  it just isn't needed yet.
- **Priority:** Low — genuinely optional; only worth building once fhir-gql runs enough
  replicas that "which version is each instance on" becomes a real operational question.

---

### Rate Limiting Middleware
- **What it does:** Throttles clients to a configurable number of requests per time window,
  with separate limits for different request categories, returning 429 with standard
  rate-limit headers when exceeded.
- **Source files:** `ratelimit.ts` — `rateLimitHandler()` (builds a singleton Express
  handler), `getRateLimiter()` (constructs a `RateLimiterRedis` from the `rate-limiter-flexible`
  npm package), `getRateLimitKey()`, `getRateLimitCategory()` (three categories: `login` —
  5/min on `/auth/login`,`/auth/newuser`,`/auth/newproject`; `auth` — 1200/min on other
  `/auth/*`,`/oauth2/*`; `default` — 60,000/min catch-all), `blockedUsers` (an in-process
  `LRUCache` short-circuit so a client already known-blocked skips the Redis round-trip
  entirely until their block expires), `addRateLimitHeader()` (IETF `RateLimit` header, not
  the `X-RateLimit-*` convention).
- **How it works:** `rate-limiter-flexible`'s `RateLimiterRedis` implements a token-bucket
  algorithm entirely server-side in Redis (Lua-scripted, atomic). Limits are keyed by
  `req.ip` + category suffix (not by authenticated user ID — Medplum's limiter is IP-based
  even for authenticated traffic, unlike fhir-gql's). Per-project overrides are supported:
  `ctx.project.systemSetting` can override the default-per-category limit for a specific
  FHIR Project, read from the `AuthenticatedRequestContext` — i.e., rate limits are
  configurable *per tenant*, not just globally.
- **Gap vs fhir-gql today:** **Has a direct, comparable equivalent — with different design
  tradeoffs, not a strict subset.** `app/middleware/rate_limit.py`'s `RateLimitMiddleware`
  implements a hand-rolled Redis sorted-set sliding window (exact window, no boundary
  double-counting) versus Medplum's token-bucket via a battle-tested library — fhir-gql's
  algorithm is arguably *more precise* at the cost of being self-maintained and (by its own
  docstring) not atomic (no Lua script), so it can allow a small over-limit burst under
  concurrent same-client requests — a real edge Medplum's Lua-atomic implementation doesn't
  have. Where fhir-gql is ahead: (1) **local fallback** — when Redis is down, fhir-gql
  degrades to a working (if non-distributed) in-process limiter rather than presumably
  failing open or closed (Medplum's `rateLimitHandler` has no visible fallback path if
  `getRateLimitRedis()` is unreachable — a `RateLimiterRedis` call would simply reject with
  an `Error`, which `ratelimit.ts`'s catch block forwards to `next(err)`, meaning a Redis
  outage in Medplum surfaces as request failures, not degraded-but-functional limiting); (2)
  **client identity** — fhir-gql keys on the authenticated user's JWT `sub` when available
  (isolating limits per-user even behind shared IPs/NAT), falling back to IP only for
  anonymous traffic, versus Medplum's pure IP-based keying for everyone. Where Medplum is
  ahead: (1) **category-based limits** — distinct, much lower limits specifically on
  login/auth endpoints (5/min) to blunt credential-stuffing/brute-force, versus fhir-gql's
  flat read/write split with no special case for auth endpoints (fhir-gql's auth is fully
  delegated to an external BetterAuth IAM service — see `app/config.py`'s
  `IAM_JWKS_URL`/`IAM_ISSUER` — so login-endpoint rate limiting may be *that* service's
  responsibility, not fhir-gql's, which would make this a non-gap by design rather than an
  oversight; worth explicitly confirming); (2) **per-tenant override** — Medplum lets
  individual Projects configure their own limits via FHIR resource system settings;
  fhir-gql's limits are global-only (`settings.RATE_LIMIT_READ`/`WRITE`/`WINDOW` in
  `app/config.py`), with no per-organization override mechanism.
  (3) **standardized header format** — Medplum emits the newer IETF `RateLimit` draft header;
  fhir-gql emits the older, non-standardized `X-RateLimit-*` convention (still widely
  supported by client tooling, just not the current IETF draft).
- **Port notes for fhir-gql (FastAPI/Python):** No urgent rewrite needed — the sliding-window
  approach is sound and the fallback/per-user-identity design is genuinely good. Two
  concrete, low-effort improvements worth considering: (1) if login/auth-adjacent endpoints
  ever move into fhir-gql itself (currently delegated to BetterAuth), add a `login` category
  with a much stricter limit, mirroring `ratelimit.ts`'s `categories` array pattern; (2) if
  per-tenant limits become a requirement, the JWT payload already available via
  `get_current_user` could carry an org/tenant claim used to look up an override, analogous
  to Medplum reading `ctx.project.systemSetting`.
- **Priority:** Low — existing implementation is solid and arguably better-suited to
  fhir-gql's single-service, JWT-authenticated model than a line-for-line port of Medplum's
  would be; only the auth-endpoint-category question needs an explicit decision (delegate to
  BetterAuth vs. handle here), not more code.

---

### Redis Client Management
- **What it does:** Provides application-wide access to Redis, used for rate limiting (both
  systems), plus — in Medplum's case — caching, pub/sub, and background job queuing.
- **Source files:** `redis.ts` — `initRedis()`, `closeRedis()`, `getCacheRedis()` /
  `getRateLimitRedis()` / `getPubSubRedis()` / `getPubSubRedisSubscriber()` /
  `getAllRedisInstances()`, `reconnectOnError()`.
- **How it works:** Maintains up to five independently-configurable `ioredis` instances
  (`default`, `cache`, `rateLimit`, `pubSub`, `backgroundJobs`) — each optional config
  (`config.cacheRedis`, `config.rateLimitRedis`, etc.) falls back to sharing the `default`
  instance if not separately configured, letting an operator split Redis workloads onto
  separate physical instances only when scale demands it, with zero code changes elsewhere
  (`getCacheRedis()` etc. abstract the fallback). `reconnectOnError()` special-cases
  `READONLY`/`LOADING` errors (which occur during Redis failover) to trigger ioredis's
  built-in reconnect rather than treating them as fatal. Pub/sub subscribers are tracked in a
  `Set` so `closeRedis()` can disconnect every outstanding subscriber cleanly on shutdown
  (subscribers use `.disconnect()`, not `.quit()`, since a subscriber in `SUBSCRIBE` mode
  can't process a `QUIT` command).
- **Gap vs fhir-gql today:** **Has a narrower equivalent, sufficient for current scope.**
  `app/core/redis.py`'s module-level `redis_client` singleton covers exactly the one use
  Medplum's `default`/`rateLimit` instances cover for fhir-gql today (rate limiting). There
  is no cache-specific Redis, no pub/sub Redis, and no background-jobs Redis — but fhir-gql
  also has no caching layer, no pub/sub feature, and no job queue today, so this isn't a
  hidden gap so much as "not needed yet."
- **Port notes for fhir-gql (FastAPI/Python):** If/when fhir-gql adds a caching layer
  (e.g. caching JWKS lookups, or FHIR search results) or pub/sub (e.g. GraphQL subscriptions
  — Strawberry supports these), don't overload the rate-limit Redis client with unrelated
  traffic; follow Medplum's purpose-scoped-instance pattern from day one: add
  `settings.CACHE_REDIS_URL: str | None` (optional, falls back to `settings.REDIS_URL`) in
  `app/config.py`, and a `get_cache_redis()` accessor in `app/core/redis.py` mirroring
  `getCacheRedis()`'s fallback logic, rather than a second unrelated global.
  `redis.asyncio`'s built-in `retry_on_error`/`RETRY` support covers the `reconnectOnError`
  concern (`redis-py` has this natively; the current `redis_client` construction in
  `app/core/redis.py` doesn't currently pass a retry policy — worth adding
  `retry=Retry(ExponentialBackoff(), 3)` for resilience against Redis failover blips, which
  today would surface as `RateLimitMiddleware`'s "Redis error, falling back to local" path
  rather than transparently reconnecting).
- **Priority:** Low now / Medium later — fine as-is for the current single-purpose (rate
  limiting) use; revisit the purpose-scoped-instance pattern the moment a second Redis use
  case (cache, pub/sub, jobs) is introduced, to avoid an awkward retrofit.

---

### Database Connection Pool & Schema Migrations
- **What it does:** Owns the Postgres connection pool(s) (writer + optional reader
  replica), enforces per-connection statement/idle timeouts, and runs versioned schema
  migrations (both "pre-deploy," which must complete before the server starts serving
  traffic, and "post-deploy," which can run after startup with compatibility windows
  enforced against server version) using a Postgres advisory lock to prevent concurrent
  migration races across multiple booting instances.
- **Source files:** `database.ts` — `initDatabase()`, `getDatabasePool()`, `initPoolConfig()`
  (sets `statement_timeout`, `default_transaction_isolation=repeatable read`,
  `idle_in_transaction_session_timeout`), `acquireAdvisoryLock()`/`releaseAdvisoryLock()`
  (`pg_try_advisory_lock`), `runMigrations()`, `migrate()` (bootstraps the
  `DatabaseMigration` tracking table on first boot, applies pending pre-deploy migrations
  sequentially, then checks for a pending post-deploy migration and enforces a
  `requiredBefore` server-version compatibility gate). `migration-sql.ts` —
  `getPreDeployVersion()` / `getPostDeployVersion()` / `markPostDeployMigrationCompleted()`
  (the raw SQL against the `DatabaseMigration` tracking row).
- **How it works:** A single `DatabaseMigration` row (id=1) tracks two independent version
  counters — `version` (schema/pre-deploy) and `dataVersion` (data-backfill/post-deploy,
  which can lag behind schema changes and run asynchronously). The advisory lock
  (`pg_try_advisory_lock`, retried up to 30 times with 2s delay) ensures that if multiple
  server instances boot simultaneously (common in a rolling deploy), only one actually runs
  migrations while the others wait/skip.
- **Gap vs fhir-gql today:** **Not applicable — out of scope by architecture, not a gap.**
  fhir-gql explicitly does not own Postgres or any persistence (per `app/main.py`'s own
  docstring: "this service is a pure middleware layer... it never writes to a database
  directly. All persistence flows through the downstream FHIR Server via FhirClient"). There
  is no `database.py`/`migration-sql.py` in fhir-gql and there should not be — this entire
  category of concern belongs to the downstream fhir-server, not this codebase. Listed here
  only for completeness of the file-by-file comparison, per the assignment's file list.
- **Port notes for fhir-gql (FastAPI/Python):** None — do not build this. If fhir-gql ever
  needs its own local state (e.g. a cache table, audit log, or feature-flag store separate
  from FHIR resources), *that* would warrant its own lightweight
  SQLAlchemy/asyncpg pool + Alembic migration setup, but that's a new architectural decision,
  not a gap against Medplum's design.
- **Priority:** N/A — out of scope.

---

### Initial Database Seeding
- **What it does:** On first boot against an empty database, creates the bootstrap
  superadmin user, the "Super Admin" and "FHIR R4" Projects, and rebuilds the FHIR
  StructureDefinitions/ValueSets/SearchParameters tables from the spec — the minimum data a
  freshly-provisioned Medplum instance needs to be usable at all.
- **Source files:** `seed.ts` — `seedDatabase()`, `createSuperAdmin()`, `isSeeded()`.
  `constants.ts` — `r4ProjectId`/`syntheticR4Project` (the hardcoded UUIDv5 IDs seeding
  writes into, deterministic so every fresh Medplum install gets the identical base Project
  ID).
- **How it works:** `isSeeded()` checks for the existence of any `User` resource as a proxy
  for "has this ever been seeded" — if none exists, `seedDatabase()` runs the whole bootstrap
  inside a single transaction (`systemRepo.withTransaction`) so a crash mid-seed doesn't
  leave a half-initialized database. Called unconditionally on every boot (`initAppServices`
  → `await seedDatabase(config)`) — cheap no-op after the first successful run.
- **Gap vs fhir-gql today:** **Not applicable — out of scope by architecture, not a gap.**
  Same reasoning as the database section above: fhir-gql owns no persistence, so there is no
  database to seed. Any bootstrap data (structure definitions, base FHIR resources) is the
  downstream fhir-server's responsibility.
- **Port notes for fhir-gql (FastAPI/Python):** None — do not build this in fhir-gql. If
  fhir-gql later grows its own persisted configuration (e.g. rate-limit overrides per
  tenant, feature flags), a much smaller-scoped "ensure default config row exists" idempotent
  startup check would be the appropriate analog, not full FHIR resource seeding.
- **Priority:** N/A — out of scope.

---

### OpenAPI Spec Assembly
- **What it does:** Serves a machine-readable OpenAPI 3.1 document describing the API's
  shape, generated from the FHIR spec's own JSON Schema definitions rather than hand-written.
- **Source files:** `openapi.ts` — `openApiHandler()`, `buildSpec()`, `buildBaseSpec()`
  (info/servers/security schemes — Basic, Bearer, OpenID Connect all declared), `buildFhirType()`
  / `buildSchema()` / `buildObjectSchema()` / `refReplacer()` (converts each FHIR
  StructureDefinition's JSON Schema into an OpenAPI `SchemaObject`, remapping `$ref`s from
  JSON Schema's `#/definitions/` to OpenAPI's `#/components/schemas/`), `buildPaths()`
  (hand-writes the five generic FHIR REST interaction shapes — search/create/read/update/
  delete/patch/vread — parameterized by `{resourceType}` rather than generating one path per
  resource type).
- **How it works:** Because Express has no request/response type system FastAPI-style route
  decorators could introspect, Medplum builds the spec *manually* from its already-existing
  FHIR JSON Schema definitions (`getJsonSchemaDefinitions()`) — the spec is generated once,
  cached in a module-level `cachedSpec` variable, and served statically thereafter per
  request via `openApiHandler`.
- **Gap vs fhir-gql today:** **Has a superior equivalent, by virtue of the framework.**
  `app/main.py`'s `_custom_openapi()` uses FastAPI's built-in `get_openapi()`, which
  introspects route signatures, Pydantic models, and `Depends()` automatically — this is
  categorically less manual-maintenance-prone than Medplum's hand-built JSON-Schema-to-
  OpenAPI conversion, since fhir-gql's spec always reflects the actual Pydantic models/route
  signatures with zero hand-authored path objects. fhir-gql's override only needs to inject
  the `BearerAuth` security scheme (`get_openapi()` has no constructor param for top-level
  `security`/`securitySchemes` — the same limitation Medplum works around, just with far less
  code needed on fhir-gql's side since the rest is automatic). The one thing Medplum's spec
  has that fhir-gql's doesn't: an `OpenID Connect` security scheme entry
  (`openIdConnectUrl: config.baseUrl + '.well-known/openid-configuration'`) — see the
  `.well-known` section below.
- **Port notes for fhir-gql (FastAPI/Python):** No structural change needed; this is already
  the stronger pattern. Optional: once/if `.well-known/openid-configuration` is added (see
  below), add an `OpenIdConnect` scheme alongside `BearerAuth` in `_custom_openapi()`'s
  `securitySchemes` block for parity with Medplum and better tooling support (some API
  clients auto-configure OAuth flows from an `openIdConnectUrl`).
- **Priority:** Low — already ahead of Medplum's approach structurally; only a minor optional
  addition contingent on the `.well-known` gap below.

---

### OAuth/OIDC `.well-known` Discovery Endpoints
- **What it does:** Serves the standard OAuth2/OIDC/SMART-on-FHIR discovery documents that
  let clients (and tooling) auto-configure themselves against this server's auth endpoints
  without hardcoding URLs: JWKS (public signing keys), OIDC/OAuth-Authorization-Server
  metadata, OAuth Protected Resource metadata (RFC 9728), and SMART-on-FHIR configuration.
- **Source files:** `wellknown.ts` — `wellKnownRouter` mounted at `/.well-known/`, exposing
  `/jwks.json`, `/oauth-authorization-server`, `/openid-configuration` (both aliases for the
  same `handleOAuthConfig`), `/oauth-protected-resource` (`handleOauthProtectedResource`,
  RFC 9728 — validates the requested `resource` param is same-origin), `/smart-configuration`
  and `/smart-styles.json` (SMART-on-FHIR app-launch discovery).
- **How it works:** These are pure metadata endpoints — no auth, no state — describing
  *this server's own* OAuth endpoints (`authorization_endpoint`, `token_endpoint`, etc., all
  pulled straight from `getConfig()`). Because Medplum *is* the OAuth/OIDC authorization
  server, it must publish this metadata itself.
- **Gap vs fhir-gql today:** **Lacks an equivalent — likely correctly, since it's not this
  service's authority to publish.** fhir-gql delegates all JWT issuance/JWKS to an external
  BetterAuth IAM service (`app/config.py`: `IAM_JWKS_URL`, `IAM_ISSUER` — fhir-gql *fetches*
  the JWKS to verify inbound JWTs, it doesn't mint them). The authoritative `.well-known`
  endpoints for this token issuer should live on the BetterAuth service itself, not be
  duplicated/proxied by fhir-gql — publishing OIDC discovery metadata that describes
  someone else's `token_endpoint`/`authorization_endpoint` from fhir-gql would be
  confusing/incorrect unless carefully scoped. The one piece that *would* be fhir-gql's own
  legitimate responsibility, since fhir-gql is the resource server being protected: `GET
  /.well-known/oauth-protected-resource` (RFC 9728) — this describes *fhir-gql itself* as a
  protected resource (which authorization server(s) issue valid tokens for it, which scopes
  it supports), which is squarely fhir-gql's own metadata to publish, not BetterAuth's.
- **Port notes for fhir-gql (FastAPI/Python):** Skip mirroring `/jwks.json` and
  `/openid-configuration`/`/oauth-authorization-server` — those belong to BetterAuth. Do
  consider adding `GET /.well-known/oauth-protected-resource` (a small `APIRouter`,
  no-auth, similar to `app/routers/__init__.py`'s pattern) returning
  `{"resource": "<this service's base URL>", "authorization_servers": [settings.IAM_ISSUER],
  "bearer_methods_supported": ["header"]}` — this is increasingly checked by MCP/agent
  clients and modern OAuth-aware HTTP clients doing automatic discovery, and is cheap to
  add given `settings.IAM_ISSUER` already exists.
- **Priority:** Low — the bulk of this category is correctly out-of-scope for fhir-gql by
  design; only the protected-resource metadata endpoint is a genuine (small) opportunity.

---

### Async/Deferred Batch Operation Handling (`Prefer: respond-async`)
- **What it does:** Lets a client submit a large FHIR Bundle for processing asynchronously
  (returning `202 Accepted` with a polling location immediately) instead of blocking the HTTP
  connection until the whole batch completes — necessary for batches large enough that
  synchronous processing risks client/gateway timeouts.
- **Source files:** `async-batch.ts` — `asyncBatchHandler()`, wired in `app.ts` as
  `app.post('/fhir/R4', authenticateRequest, asyncBatchHandler(config))`, positioned *before*
  the normal body-parser middleware chain so it can apply the batch-specific size limit
  (`config.maxBatchSize`) rather than the general JSON size limit.
- **How it works:** Checks the `Prefer: respond-async` request header; if absent, calls
  `next()` to fall through to the normal synchronous FHIR batch handler. If present, parses
  the body as a `Bundle`, rejects `transaction`-type bundles for async processing (only
  `batch` bundles are eligible — transactions need atomicity guarantees that don't fit an
  async worker model), creates an `AsyncJob` resource via `AsyncJobExecutor`, enqueues the
  actual work onto a background worker queue (`queueBatchProcessing`), and immediately
  returns `202 Accepted` with a `Content-Location` header pointing at the `AsyncJob`'s status
  URL for polling.
- **Gap vs fhir-gql today:** **Lacks an equivalent entirely — plausibly acceptable for
  current scope.** fhir-gql has no background job queue, no `Prefer: respond-async` handling,
  and no async job status/polling resource. Given fhir-gql is currently a "patient-only
  slice" (per `app/main.py`'s docstring) proxying individual FHIR operations rather than
  accepting bulk Bundle submissions, this gap is unsurprising and likely not urgent — but
  it's worth flagging now because it has architectural implications (a job queue, worker
  process, and job-status resource type) that are much cheaper to plan for early than retrofit.
- **Port notes for fhir-gql (FastAPI/Python):** Not needed today. If/when fhir-gql accepts
  bulk write operations (e.g. a bulk-import endpoint, or full Bundle submission rather than
  single-resource CRUD), the FastAPI-idiomatic starting point is `BackgroundTasks` for
  light-weight cases, or a real queue (Celery, RQ, or Arq — Arq is asyncio-native and pairs
  well with the existing `redis.asyncio` client already in `app/core/redis.py`) for
  anything that needs to survive a process restart or run on a separate worker. The pattern
  to mirror from `async-batch.ts`: check `request.headers.get("prefer") ==
  "respond-async"`, branch early before expensive body parsing/limits differ from the sync
  path, return `202` with a `Content-Location`/`Location` header pointing at a pollable job
  status endpoint.
- **Priority:** Low today / re-evaluate as scope grows — no current caller needs this; the
  main risk is not building it, it's not being aware it's a known, well-trodden pattern when
  bulk operations are eventually requested.

---

## Summary Table

| Feature | Priority | Gap status |
|---|---|---|
| Application Bootstrap / Composition Root | Low | Has equivalent (`app/main.py`) |
| Process Entrypoint, Signal Handling & Graceful Shutdown | Low | Partial (uvicorn covers drain; no asyncio exception handler) |
| Standard Security Response Headers | **High** | Missing entirely |
| CORS Policy | **High** | Missing entirely |
| Response Compression | Medium | Missing entirely |
| Global/Central Error Handling | Low | Has equivalent (`app/core/errors.py`) |
| Request-Scoped Context Propagation | Medium | Partial (`request.state` covers most cases; no `contextvars`) |
| Request ID vs. Distributed Trace ID | Medium-High | Missing (only has flat request ID) |
| Structured Logging | Medium | Has equivalent, missing auto request-ID binding |
| Health Check Endpoint | **High** | Partial (liveness only; no Redis/downstream check) |
| Heartbeat / Periodic Event Bus | Low | Missing, no current consumer |
| Multi-Instance Server Registry | Low | Missing, optional |
| Rate Limiting Middleware | Low | Has comparable equivalent (different tradeoffs) |
| Redis Client Management | Low→Medium | Has narrower equivalent, sufficient for now |
| Database Connection Pool & Migrations | N/A | Out of scope (downstream fhir-server's job) |
| Initial Database Seeding | N/A | Out of scope (downstream fhir-server's job) |
| OpenAPI Spec Assembly | Low | Has superior equivalent (FastAPI auto-generation) |
| OAuth/OIDC `.well-known` Discovery | Low | Mostly out of scope; protected-resource endpoint is a small opportunity |
| Async/Deferred Batch Operation Handling | Low | Missing, not yet needed |

## Recommended Next Steps

The two items that should be addressed soonest are the ones with no mitigating factor and
real exposure: **CORS** (any browser-based frontend is currently unable to call this API at
all, or would rely on an unreviewed upstream proxy to inject headers) and **security response
headers** (zero-cost hardening that's simply absent). Both are small, self-contained
`Starlette`/FastAPI middleware additions with no architectural risk — reasonable to bundle
into a single PR alongside `GZipMiddleware`, since all three are additive `app.add_middleware()`
calls with no interaction with existing business logic. Next, extend `/health` to actually
verify Redis and the downstream fhir-server, since a middleware service's health check that
doesn't check its one dependency is close to meaningless for orchestrator readiness probes.
The context-propagation/logging/trace-ID cluster (three related findings above) is a
coherent second phase: introducing one `contextvars.ContextVar`-based request context object
pays off across all three simultaneously, and is best done deliberately (with W3C
`traceparent` propagation to the downstream `FhirClient` calls) rather than patched
piecemeal — this is also the one place where fhir-gql's specific "middleware in front of
another service" topology makes it more important here than it was for Medplum's monolithic
server. The three N/A categories (database pool, migrations, seeding) should stay
out of scope; resist any pressure to "port" them, since doing so would violate the
architecture documented in `app/main.py`'s own docstring. Rate limiting, Redis management,
and OpenAPI generation need no immediate work — fhir-gql's existing choices there are sound,
in a couple of respects (auto-generated OpenAPI, Redis-fallback rate limiting) arguably
better-suited to this codebase than a literal port of Medplum's approach would be.
