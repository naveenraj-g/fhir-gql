# Real-Time Events, FHIR Subscriptions, WebSockets, FHIRcast, and Webhooks

Comparison scope: Medplum `packages/server/src/{workers,ws,fhircast,webhook}/*` and
`src/pubsub.ts` vs. `fhir-gql`. This is a **currently-nonexistent capability domain**
in fhir-gql — there is no Subscription resource support, no WebSocket endpoint, no
webhook delivery, and no FHIRcast today. This document is written to be
implementation-ready.

## Architectural framing (read this before the feature list)

Medplum is a monolith: the same process that commits a resource write to Postgres
also evaluates `Subscription` criteria and enqueues delivery jobs, all inside (or
immediately after) the write transaction. It can do this because it *is* the data
layer.

`fhir-gql` is not the data layer. It is a FastAPI middleware in front of a separate
downstream **fhir-server** that owns persistence (see `app/fhir_client/client.py` —
every write is an outbound `httpx` call to the FHIR Server; fhir-gql never touches a
database directly, per `app/main.py`'s own docstring: *"this service is a pure
middleware layer... never writes to a database directly"*).

This has one hard consequence that recurs in almost every feature below:

> **Only fhir-server sees every write land.** If fhir-server has any write path that
> does not go through fhir-gql (a bulk import job, another internal service, a
> migration script), fhir-gql cannot originate a reliable subscription trigger by
> hooking its own REST/GraphQL handlers — it would silently miss those writes.
> The trigger for "did a resource change" must originate in fhir-server. Everything
> downstream of that trigger (matching, delivery, retry, WebSocket fanout, FHIRcast) is
> fair game for fhir-gql to own, and mostly *should* be fhir-gql's job, because that's
> where auth, RBAC, rate limiting and the Redis connection already live.

Existing fhir-gql infrastructure relevant to this domain (both skimmed in full):

- `app/core/redis.py` — a single module-level `redis.asyncio` client
  (`redis_client`), lazily connected, pinged at startup in `app/main.py`'s
  `lifespan()`, stored on `app.state.redis`, closed on shutdown. `decode_responses=True`
  is set, which matters for anything that wants to store raw bytes (WebSocket binary
  frames would need re-encoding).
- `app/middleware/rate_limit.py` — `RateLimitMiddleware`, a sliding-window limiter
  using Redis sorted sets (`ZREMRANGEBYSCORE` + `ZCARD` + `ZADD` + `EXPIRE`), with an
  in-process fallback when Redis is down. The failure-tracking pattern used by
  Medplum's `subscription-failure-tracker.ts` (sorted set of timestamps, `ZCOUNT` over
  a window) is structurally identical to this file's sliding-window algorithm — the
  same Redis idiom can be reused almost verbatim for subscription auto-disable.

Recommended new Redis client role split (mirroring Medplum's `getCacheRedis()` /
`getPubSubRedis()` / `getPubSubRedisSubscriber()` three-way split in
`packages/server/src/redis.ts`, referenced throughout the files below): a Redis
client in **subscribed** mode cannot issue other commands, so pub/sub subscriber
connections must be separate from the general-purpose cache/rate-limit client.
fhir-gql should add at minimum a second client instance (or a small pool) dedicated
to pub/sub subscribe, alongside the existing `redis_client` used for rate limiting
and now also general key/value/sorted-set storage.

---

### FHIR Subscription Resource — Rest-Hook Webhook Delivery

- **What it does:** Lets a client (an EHR module, an external integration, a bot) register a
  `Subscription` FHIR resource declaring "notify this URL every time a resource
  matching this search-criteria is created/updated/deleted." This is the standard
  FHIR mechanism for event-driven integration — e.g. notify a lab system when an
  Observation is finalized, notify a billing system when an Encounter closes, notify
  a care-coordination platform when a Patient's address changes. Without it, every
  integration partner has to poll, which does not scale in a clinical setting with
  real-time workflow requirements.
- **Source files:**
  `packages/server/src/workers/subscription.ts` — `addSubscriptionJobs()` (evaluates
  criteria and enqueues), `execSubscriptionJob()` (job handler), `sendRestHook()`
  (does the actual `fetch` POST), `execBot()` (Bot-channel variant), `matchesCriteria()`
  (delegates to `@medplum/core`'s `resourceMatchesSubscriptionCriteria`),
  `getSubscriptions()` (loads active `Subscription` resources for the project +
  resource type), `buildRestHookHeaders()` (headers incl. HMAC signature).
- **How it works:**
  - `Subscription.channel.type = 'rest-hook'`, `channel.endpoint` = target URL,
    `channel.header` = extra headers, `criteria` = a FHIR search-request string
    (e.g. `Patient?active=true`) or, for topic-based (R5-style) subscriptions, a
    `SubscriptionTopic` reference.
  - On every resource write, `addSubscriptionJobs()` loads all `active` Subscriptions
    for the project + resource type, evaluates `resourceMatchesSubscriptionCriteria`
    (search-parameter matching against the new resource, with access to the previous
    version for update-diff-aware criteria), and for each match enqueues a
    `SubscriptionJobData` job onto a BullMQ queue (`SubscriptionQueue`).
  - `execSubscriptionJob()` re-reads the current version of both the `Subscription`
    and the target resource at execution time (not the evaluation-time snapshot) —
    this guards against the Subscription being deleted/disabled or the resource being
    superseded between enqueue and execute.
  - The POST body is the FHIR JSON of the resource (`{}` for deletes), with headers
    `X-Medplum-Subscription`, `X-Medplum-Interaction`, optional `X-Signature` (HMAC-SHA256
    over the body using a secret stored in a `subscription-secret` extension), and
    trace headers. `AbortSignal.timeout(120_000)` bounds the outbound call.
  - Success/failure is recorded as an `AuditEvent` for compliance visibility.
  - `Subscription.channel.endpoint` referencing `Bot/{id}` routes through `execBot()`
    instead of a raw HTTP POST — not relevant to fhir-gql since it has no Bot/runtime
    execution model.
- **Belongs in: both, coordinated.** The *trigger* (did a write happen, what
  changed) must originate in fhir-server — it is the only party that observes every
  commit, including ones that don't route through fhir-gql. But *criteria matching*
  and *delivery* are stateless business logic that has no dependency on the database
  transaction and fit naturally into fhir-gql, which already owns RBAC/orchestration
  and the Redis connection needed for queuing.
  Concrete integration pattern:
  1. fhir-server publishes a small "resource changed" event to a Redis Stream
     (e.g. `fhirserver:resource-events`) immediately after each committed write:
     `{resourceType, id, versionId, previousVersionId, interaction, tenantId, timestamp}`.
     This is the one piece of new work required *in* fhir-server — a single hook at
     the end of its write path, analogous to Medplum's `addDispatchJobs()` call site
     in `dispatch.ts`. No FHIR-server business logic needs to move.
  2. fhir-gql owns the `Subscription` resource CRUD API (new REST/GraphQL routes,
     following the existing Patient pattern in `app/routers/` and `app/gql/`) and
     persists Subscriptions either via the same downstream fhir-server (as a first-class
     FHIR resource, simplest — reuses `FhirClient`) or in a fhir-gql-local store.
     Storing them as ordinary FHIR resources in fhir-server is preferred: it keeps a
     single source of truth and means no dual-write consistency problem.
  3. A fhir-gql background worker (arq, see Port notes) consumes the Redis Stream via
     a **consumer group**, fetches the changed resource via `FhirClient`, loads
     candidate Subscriptions (cached in Redis, refreshed on Subscription CRUD, keyed
     by resourceType — same shape as Medplum's `getActiveSubsKey`), evaluates search
     criteria against the resource JSON, and enqueues a delivery job per match.
  4. A separate delivery worker executes `sendRestHook`-equivalent HTTP POSTs with
     retry/backoff (see next feature).
- **Port notes for fhir-gql (FastAPI/Python):**
  - Criteria matching: FHIR search-parameter matching against a resource dict is
    non-trivial to hand-roll correctly (chained params, modifiers, `_include`, token
    vs. reference vs. date comparators). Evaluate whether `fhir.resources` /
    `fhirpath.py` or a vendored subset of match logic (start with simple equality /
    `active=true`-style criteria, since fhir-gql is Patient-only today) is sufficient
    for v1 before building a full FHIRPath-based evaluator.
  - Redis Streams (`XADD`/`XREADGROUP`/`XACK`) are a good fit for the
    fhir-server → fhir-gql event bus specifically because they give consumer-group
    load balancing across multiple fhir-gql instances *and* replay/at-least-once
    semantics (a plain Pub/Sub channel drops messages for subscribers that are
    briefly disconnected — unacceptable for a clinical event feed). Use Pub/Sub only
    for the downstream WebSocket fanout, where Medplum itself accepts drop-on-disconnect
    semantics (see WebSocket Subscription Channel below).
  - HMAC signing: Python's `hmac` + `hashlib.sha256`, direct equivalent of
    `createHmac('sha256', secret)`.
  - Outbound HTTP: reuse `httpx.AsyncClient` (already a project dependency via
    `FhirClient`) with a per-request timeout, mirroring Medplum's 120s
    `AbortSignal.timeout`.
- **Priority: High.** This is the flagship FHIR real-time feature and the one most
  external integrations expect from *any* FHIR server/middleware. Nothing else in
  this document is useful without it.

---

### Subscription Delivery Retry, Backoff, and Dead-Letter Handling

- **What it does:** When a webhook delivery fails (target down, non-2xx, timeout),
  retries it automatically with increasing delay instead of dropping the event or
  hammering a broken endpoint. Clinically this matters because a missed
  Observation-finalized or Encounter-closed notification can mean a downstream
  system (billing, results routing, care coordination) silently falls out of sync.
- **Source files:** `packages/server/src/workers/subscription.ts` — constants
  `MAX_JOB_ATTEMPTS` (19), `DEFAULT_ATTEMPTS` (4, overridable via the
  `subscription-max-attempts` extension), `MAX_PREAMBLE_ATTEMPTS`, `BASE_DELAY`
  (20s), `MAX_DELAY` (8h); the `backoffStrategy` callback passed to BullMQ's
  `Worker` `settings`; `catchJobError()` (decides retry vs. give-up + calls
  `job.changePriority()` to de-prioritize repeatedly-failing jobs).
- **How it works:**
  - Two independent failure classes are distinguished: **preamble errors** (loading
    the Subscription/resource — treated as *fhir-server*/Medplum-side issues, retried
    up to `MAX_JOB_ATTEMPTS`=19 to ride out transient outages) vs. **delivery errors**
    (the client's endpoint/bot failing — retried only up to the Subscription's
    configured `attempts`, default 4, so a permanently broken client endpoint doesn't
    retry for 3 days).
  - Backoff formula: `delay = min(BASE_DELAY * 2^(attemptsMade-1) * jitterFactor, MAX_DELAY)`
    where `jitterFactor` is uniform random in `[0.9, 1.1]` (±10%) to avoid thundering-herd
    retries across many failing subscriptions. With `BASE_DELAY=20_000ms` and
    `MAX_DELAY=28_800_000ms` (8h), 19 attempts spans roughly 72–80 hours total.
  - On exhausting attempts, the job throws BullMQ's `UnrecoverableError` — a sentinel
    that tells BullMQ to move the job straight to the `failed` state instead of
    retrying again (this *is* Medplum's dead-letter mechanism: failed jobs remain
    queryable in BullMQ's failed set rather than vanishing).
  - Every failed final attempt also calls `recordSubscriptionFailure()` (next feature)
    to track consecutive failures independent of BullMQ's per-job retry count.
- **Belongs in: fhir-gql (middleware).** Delivery execution, retry bookkeeping, and
  backoff timing have zero dependency on the FHIR data layer — they operate purely on
  "this HTTP POST failed, when do we try again." This is squarely orchestration work.
- **Port notes for fhir-gql (FastAPI/Python):** BullMQ (Redis-backed, Node) has no
  drop-in Python port, but the *pattern* — a Redis-backed job queue with configurable
  per-job max-attempts and a custom backoff function — maps directly onto **arq**
  (asyncio-native, Redis-backed, built by the `pydantic`/`aiohttp` ecosystem author,
  no extra broker required beyond the Redis already running for rate limiting). arq's
  `Worker` supports `max_tries` per job and a custom `retry` exception that carries an
  explicit `defer` delay — implement the same
  `min(BASE_DELAY * 2**(attempt-1) * jitter, MAX_DELAY)` formula in the job function
  and `raise Retry(defer=delay_seconds)`. Celery is the heavier alternative (needs
  its own broker conventions and result backend, and is sync-first — a worse fit for
  an all-async FastAPI codebase) but is worth considering only if the team already
  runs Celery elsewhere. A minimal hand-rolled Redis Streams consumer with
  `XCLAIM`/`XPENDING` for redelivery is a third option if avoiding a new dependency
  entirely is a priority, at the cost of reimplementing scheduling/backoff by hand.
  Recommendation: **arq**, given fhir-gql is already 100% async FastAPI and already
  depends on `redis.asyncio`.
- **Priority: High.** Retry/backoff is not an optional enhancement to webhook
  delivery — an implementation without it is not production-viable for clinical
  integrations (a single transient network blip would silently drop events).

---

### Subscription Auto-Disable on Repeated Failure

- **What it does:** Automatically flips a `Subscription.status` to `off` after it has
  failed N consecutive times within a configurable time window, and records why. This
  protects the platform (repeated outbound calls to a dead endpoint waste worker
  capacity and can look like an outbound DoS) and protects the subscriber (a clear
  audit trail of *why* their integration went dark, instead of silent, indefinite
  failure).
- **Source files:** `packages/server/src/workers/subscription-failure-tracker.ts` —
  `recordSubscriptionFailure()`, `clearSubscriptionFailures()`,
  `getSubscriptionAutoDisableTriggers()` (server-config default + per-project
  override via a `Project.systemSetting`); `autoDisableSubscription()` in
  `subscription.ts` (the actual status flip).
- **How it works:**
  - One Redis sorted set per subscription: `medplum:sub:failures:{subscriptionId}`,
    member = `{timestamp}:{randomId}` (uniqueness even for same-millisecond failures),
    score = timestamp. A single Redis pipeline does: prune entries older than the
    largest configured window (`ZREMRANGEBYSCORE`), add the new failure
    (`ZADD`), then `ZCOUNT` the window for *each* configured trigger (multiple
    triggers can co-exist, e.g. "10 failures in 5 minutes" AND "50 failures in 24
    hours"), then reset the key's `EXPIRE` to the largest window. This is the exact
    sliding-window-counter idiom already used in
    `app/middleware/rate_limit.py::_check_redis()`.
  - If any trigger's count meets its `maxConsecutiveFailures` threshold,
    `autoDisableSubscription()` runs a **transactional JSON Patch**: `test` op
    asserts `status == 'active'` (so a concurrent auto-disable or manual re-enable
    doesn't race), `replace` flips `status` to `off`, `add` records an `/error`
    message, and an `AuditEvent` is written — all inside `systemRepo.withTransaction`.
  - On any successful delivery, `clearSubscriptionFailures()` (`UNLINK` on the key)
    resets the counter — the trigger is about *consecutive* failures, not
    cumulative-ever failures.
- **Belongs in: fhir-gql (middleware).** Same reasoning as retry/backoff: this
  observes and reacts to delivery outcomes fhir-gql itself produces. The only
  fhir-server-side piece is the eventual `PATCH Subscription.status = off`, which is
  just a normal FHIR write fhir-gql already knows how to make via `FhirClient.patch()`.
  The compare-and-swap "test op" trick needs the downstream FHIR Server's transaction
  endpoint (or an equivalent conditional-update / `If-Match` header) to be atomic —
  worth confirming the downstream fhir-server supports FHIR `PATCH` with JSON Patch
  test operations, or falling back to an `ETag`/`If-Match` conditional PATCH if not.
- **Port notes for fhir-gql (FastAPI/Python):** Directly portable — use
  `redis_client` (the existing Redis client) with a `redis.asyncio` pipeline:
  `zremrangebyscore`, `zadd`, `zcount` per trigger, `expire`. This is close enough to
  `_check_redis()` in `app/middleware/rate_limit.py` that a shared helper function
  ("sliding-window counter with N thresholds") could serve both rate limiting and
  subscription auto-disable, reducing duplicate Redis-idiom code.
- **Priority: Medium.** Valuable operationally but not blocking for a v1 launch of
  Subscriptions — a v1 can ship with unlimited retries + manual monitoring/alerting,
  and layer in auto-disable shortly after. Sequence it right after the core rest-hook
  feature ships.

---

### Dispatch Worker — Post-Write Event Fan-out Hook

- **What it does:** The single choke point, on the data-layer side, through which
  *every* resource write flows before triggering any downstream async work
  (subscriptions, file downloads/exports, scheduled cron-trigger resources, etc.).
  Historically this logic ran synchronously in the request path; moving it to a
  queued worker decoupled request latency from fan-out cost and made individual
  fan-out jobs independently retryable.
- **Source files:** `packages/server/src/workers/dispatch.ts` — `addDispatchJobs()`
  (called once per write, from the write-transaction commit path — not shown in this
  file, but is the trigger point), `execDispatchJob()` (loads the versioned resource +
  previous version + project, then calls `addSubscriptionJobs`, `addDownloadJobs`,
  `addCronJobs` in sequence with independent try/catch per fan-out target so one
  failing target doesn't block the others); `workers/index.ts` — `addBackgroundJobs()`
  is the actual call site invoked after a commit, and `initWorkers()` registers all
  queue/worker pairs (`dispatch`, `subscription`, `download`, `cron`, `reindex`,
  `batch`, etc.) against a single BullMQ/Redis connection, each independently
  enable/disable-able via config (`config.workers.enabled`).
- **How it works:** `DispatchJobData` carries just resource identity
  (`resourceType`, `id`, `versionId`, `previousVersionId`, `interaction`) — cheap to
  enqueue, no resource payload duplication. The dispatch job handler re-reads the
  full resource + previous version from the repo at execution time (fresh data, not
  a stale copy), then hands off to `addSubscriptionJobs` which does criteria matching
  and enqueues the *actual* delivery jobs described above.
- **Belongs in: fhir-server (data layer, since it sees writes first) — but only the
  trigger; the fan-out logic it calls is what fhir-gql should own.** This file *is*
  the conceptual proof that the trigger for all real-time behavior has to sit right
  next to the write. In the split-service design, fhir-server's write path needs the
  minimal equivalent of `addDispatchJobs()`: publish `{resourceType, id, versionId,
  previousVersionId, interaction}` to the Redis Stream described in the Subscription
  feature above. fhir-server does **not** need to know anything about Subscriptions,
  criteria, or delivery — it just needs to emit "this happened." Everything
  `execDispatchJob()` currently does after that (loading the resource, calling
  `addSubscriptionJobs`) is fan-out logic that belongs in fhir-gql's consumer.
- **Port notes for fhir-gql (FastAPI/Python):** N/A for fhir-gql itself to implement
  — this is the one piece of new code required inside the separate fhir-server
  codebase. Flag this early as a cross-team/cross-repo dependency: FHIR Subscriptions
  cannot ship in fhir-gql until fhir-server exposes this event stream. If fhir-server
  cannot be modified in the short term, the fallback is a fhir-gql-side polling
  worker that periodically diffs `_lastUpdated` across watched resource types — much
  higher latency (seconds-to-minutes instead of near-real-time) and higher load on
  fhir-server, but requires zero fhir-server changes. Recommend this only as a
  stopgap, not the target architecture.
- **Priority: High** (as a cross-team coordination item) — this is the critical path
  blocker for every other feature in this document that depends on knowing "a write
  happened." Raise it with the fhir-server team immediately, in parallel with
  building fhir-gql's consumer side.

---

### Cross-Instance Redis Pub/Sub Fan-out Layer

- **What it does:** The shared plumbing that lets any server instance publish an
  event and have it delivered to whichever instance(s) currently hold the relevant
  WebSocket connection(s) — necessary because in a horizontally-scaled deployment,
  the instance that evaluates "this resource changed" is not necessarily the instance
  holding the browser's live socket.
- **Source files:** `packages/server/src/pubsub.ts` — `publish()` (thin wrapper over
  `redis.publish`), the "Active WebSocket subscription hash" helpers
  (`getActiveSubsKey`, `setActiveSubscription`, `getActiveSubscriptions`,
  `removeActiveSubscriptions`, `isSubscriptionActive`) that maintain, per
  project+resourceType, a Redis hash of `{subscriptionRef: {criteria, expiration,
  author, loginId, membershipId}}` so *any* instance can evaluate whether a newly
  written resource matches an actively-bound WebSocket subscription without needing
  in-memory state from the instance that originally bound it; the "per-user active
  set" helpers (`addUserActiveWebSocketSubscription`,
  `getUserActiveWebSocketSubscriptionCount`, etc.) used to enforce a per-user
  concurrent-WebSocket-subscription cap; `cleanupActiveSubs` / `cleanupUserSubs` for
  garbage-collecting stale entries.
- **How it works:** Redis is used in two distinct roles here: (1) plain **Pub/Sub**
  (`publish`/`subscribe`, fire-and-forget, no persistence, no delivery guarantee to
  disconnected subscribers) as the cross-instance message bus, and (2) **regular
  key/value + hash + set storage** as a shared source of truth for "which
  subscriptions are currently bound by some WebSocket, somewhere in the fleet."
  `WEBSOCKET_SUB_PUBLISH_CHANNEL` is the single channel every instance subscribes to;
  published messages carry `{resource, events: [[subscriptionId, options], ...]}` —
  note the *matching already happened* before publish (in `addSubscriptionJobs`), so
  every instance's subscriber handler just needs to look up local socket bindings by
  subscription ID and forward, not re-evaluate criteria.
- **Belongs in: fhir-gql (middleware), but the event trigger still comes from
  fhir-server.** This is pure connection-management/fan-out infrastructure with no
  data-layer dependency — a natural fit for fhir-gql, which already has a shared
  Redis instance and will run multiple instances in production. The distinction from
  the Subscription Delivery feature above: that one is about *matching + retrying
  webhook POSTs*; this one is about *routing an already-matched event to the specific
  process holding a live socket*.
- **Port notes for fhir-gql (FastAPI/Python):** `redis.asyncio` supports Pub/Sub
  natively (`client.pubsub()`, `.subscribe(channel)`, async iteration over
  `.listen()`) — direct equivalent of `getPubSubRedisSubscriber()`. Key design point
  carried over from Medplum: **a Redis connection in subscribed mode cannot run other
  commands**, so each active WebSocket connection that binds to a subscription needs
  either (a) its own dedicated subscriber connection (Medplum's per-socket approach in
  `echo.ts`/`fhircast.ts`/`agent.ts` — simple but connection-count-heavy at scale) or
  (b) a single shared subscriber process per fhir-gql instance that fans out
  in-process to the right `WebSocket` objects held in an in-memory dict (Medplum's
  approach in `subscriptions.ts`, via `wsToSubLookup`/`subToWsLookup` — more
  efficient, recommended for fhir-gql from day one given FastAPI's single-event-loop
  model makes in-process fan-out cheap). The active-subscription hash/set state
  (`setActiveSubscription`, per-user sets) maps directly to `redis.asyncio`
  `hset`/`hgetall`/`sadd`/`smembers` calls — no structural changes needed.
- **Priority: High.** Required as soon as fhir-gql runs more than one instance
  (which any real deployment will) and WebSocket subscriptions exist at all —
  without it, a client's WebSocket subscription only receives events that happen to
  be evaluated on the same instance it connected to.

---

### WebSocket Server Infrastructure & Connection Lifecycle

- **What it does:** The generic multiplexed WebSocket entry point all the
  more-specific channels (subscriptions, echo, FHIRcast, agent, ai-realtime) attach
  to — upgrade handling, per-path routing to a handler, connection tracking, and
  graceful shutdown so in-flight sockets aren't just dropped when the process exits.
- **Source files:** `packages/server/src/ws/routes.ts` — `initWebSockets()` (registers
  the `http.Server` `'upgrade'` listener, routes by the first URL path segment via a
  `handlerMap`), `closeWebSockets()` (graceful drain: sends close code `1001` "Going
  Away" to every open socket, waits up to `WS_CLOSE_TIMEOUT_MS` (30s) for the close
  handshake, then force-`terminate()`s stragglers), the per-"generation" `WebSocketState`
  closure pattern (so a socket that connects mid-shutdown can't corrupt the next
  `initWebSockets()` call's state — relevant for tests/hot-reload, less so for a
  single long-running prod process, but a good defensive pattern regardless).
- **How it works:** Uses the `ws` library with `noServer: true` — it does not bind
  its own port; it hooks into the existing HTTP server's `'upgrade'` event and only
  completes the WebSocket handshake (`handleUpgrade`) if the requested path matches a
  registered handler (`echo`, `agent`, `ai-realtime`, `fhircast`,
  `subscriptions-r4`), otherwise responds `404`. `maxPayload` is bounded by the same
  `maxJsonSize` config used for REST bodies. Every handler gets `(socket, request)`
  and is invoked inside a fresh `RequestContext` (Medplum's async-local-storage
  request-scoped context, used for logging/tracing).
- **Belongs in: fhir-gql (middleware).** WebSocket connection lifecycle is pure
  transport/orchestration concern with zero data-layer coupling — exactly the kind
  of thing fhir-gql should own outright, the same way it owns JWT auth and rate
  limiting today.
- **Port notes for fhir-gql (FastAPI/Python):** FastAPI has first-class native
  WebSocket support (`@app.websocket("/ws/{channel}")`, `WebSocket.accept()`,
  `.receive_text()`/`.receive_json()`, `.send_json()`, `WebSocketDisconnect`
  exception) — no separate library needed, unlike Node/Express which requires the
  `ws` package bolted on. This is materially simpler to port than the Node version:
  route registration is just normal FastAPI path routing (no manual `'upgrade'` event
  handling), and `Depends()` can run JWT auth on the WebSocket handshake the same way
  it does for REST (mirroring `get_current_user` used today in `app/main.py`).
  Graceful shutdown: track open `WebSocket` connections in a module-level `set()`
  (or better, a small connection-manager class), and in the FastAPI `lifespan()`
  shutdown block (same place `redis_client.aclose()` already happens in
  `app/main.py`) iterate the set, call `.close(code=1001)` on each, and
  `asyncio.wait_for(..., timeout=30)` on their disconnect events before returning.
  Route dispatch: use FastAPI's path parameter (`/ws/{channel}`) instead of manually
  parsing `request.url` segments as Medplum does.
- **Priority: High.** Foundational — every other WebSocket feature below depends on
  this existing first.

---

### FHIR WebSocket Subscription Channel (R4/R5 `SubscriptionStatus` protocol)

- **What it does:** Lets a browser/mobile client hold a live WebSocket connection and
  receive `Subscription` notifications in-band instead of via an outbound webhook —
  the standard mechanism for real-time clinical UI updates (e.g. a vitals dashboard
  that live-updates as new Observations land, or an inbox that live-updates as new
  Tasks/CommunicationRequests arrive) without polling.
- **Source files:** `packages/server/src/ws/subscriptions.ts` —
  `handleR4SubscriptionConnection()` (the connection handler), `onBind`/`onUnbind`
  (bind/unbind a socket to a subscription ID via a signed token), `verifyWsToken()`
  (JWT verification of the binding token), `createHandshakeBundle()`,
  `createSubHeartbeatEvent()`, `createSubEventNotification()` (build the
  `Bundle`/`SubscriptionStatus` payloads), `checkWebSocketSubscriptionLimit()`
  (per-user concurrent-subscription cap), the `wsToSubLookup`/`subToWsLookup`
  in-memory maps (bidirectional socket↔subscription index within one process),
  `markInMemorySubscriptionsInactive()` / `cleanupR4SubscriptionResources()`
  (cleanup on unbind/disconnect/shutdown). Also relevant, referenced but out of the
  assigned file list: `fhir/operations/getwsbindingtoken.ts` (the
  `$get-ws-binding-token` FHIR operation that mints the JWT used to bind).
- **How it works:**
  1. Client first creates a `Subscription` resource with `channel.type = 'websocket'`
     via normal FHIR REST (handled in `workers/subscription.ts`, not this file — note
     websocket-channel Subscriptions are *not* persisted as durable server resources
     the way rest-hook ones are; "websocket subscriptions are persisted differently...
     more transient", per a comment in `subscription.ts`).
  2. Client calls `$get-ws-binding-token` to get a short-lived signed JWT encoding
     `{subscription_id, login_id, membership_id, profile, exp}`.
  3. Client opens a WebSocket to `/ws/subscriptions-r4`, sends
     `{type: 'bind-with-token', payload: {token}}`.
  4. Server verifies the JWT, looks up the cached `Subscription` resource (from
     `getCacheRedis()`), records the binding in the cross-instance active-subscription
     hash (see Pub/Sub Fan-out feature), registers the socket in the in-process
     lookup maps, and sends back a **handshake** `Bundle` (`SubscriptionStatus.type =
     'handshake'`) — sent *before* the heartbeat handler is (re-)registered, explicitly
     to avoid a race where a heartbeat could otherwise interleave before the handshake.
  5. On every server-wide heartbeat tick (`DEFAULT_HEARTBEAT_MS`), every bound socket
     receives a `SubscriptionStatus.type = 'heartbeat'` Bundle — a liveness signal
     distinct from the low-level WebSocket ping/pong frame, at the FHIR resource
     level, so clients can detect "connected but Subscription not actually being
     serviced" vs. "socket died."
  6. On a real event match (delivered via the Pub/Sub channel from
     `addSubscriptionJobs`), the socket receives a `SubscriptionStatus.type =
     'event-notification'` Bundle whose `entry` optionally includes the actual
     resource (`includeResource` option) alongside the notification metadata
     (`notificationEvent[].eventNumber`, `.timestamp`, `.focus` reference).
  7. `type: 'ping'` client messages get an immediate `{type: 'pong'}` — a
     lightweight app-level keepalive independent of the heartbeat broadcast.
  8. Socket close triggers `onDisconnect`, which unbinds every subscription this
     socket held and marks them inactive cross-instance.
  9. A per-user cap (`checkWebSocketSubscriptionLimit`, default from config,
     overridable per-`Project`) prevents one user from holding unbounded concurrent
     bindings.
- **Belongs in: fhir-gql (middleware), matching already resolved upstream by whatever
  consumes the fhir-server event stream.** The entire protocol here — token
  verification, socket registration, heartbeat, message framing — is transport/session
  management with no data-layer dependency, and should live in fhir-gql alongside the
  WebSocket infrastructure feature above. The one piece that must trace back to
  fhir-server is, again, the underlying "did a matching resource change" trigger
  (same Redis Stream consumer described in the rest-hook feature); this feature is
  purely "given a match already happened, deliver it over this specific socket."
- **Port notes for fhir-gql (FastAPI/Python):**
  - FastAPI WebSocket handler receives JSON via `websocket.receive_json()`, matches
    on a `type` field the same way (`bind-with-token` / `unbind-from-token` / `ping`).
  - JWT verification: fhir-gql already has JWT infrastructure for auth
    (`app/auth/dependencies.py`) — the `$get-ws-binding-token`-equivalent short-lived
    token can reuse the same signing key/library (`python-jose` or `PyJWT`,
    whichever `app/auth` already uses) with a short `exp` and the subscription/profile
    claims embedded.
  - In-process socket↔subscription maps: a plain `dict[str, set[WebSocket]]` +
    `dict[WebSocket, dict[str, ...]]` pair, same structure as
    `subToWsLookup`/`wsToSubLookup`. Given FastAPI/Starlette's single-threaded
    event-loop-per-worker model this needs no extra locking beyond what asyncio
    already gives for free (no concurrent mutation across OS threads within one
    worker process) — but if fhir-gql runs multiple **worker processes** behind
    uvicorn/gunicorn, remember each process has its own independent maps, and the
    cross-instance Redis Pub/Sub layer is what bridges that (a socket bound on worker
    A only ever gets pushed to by worker A's local subscriber handler).
  - Heartbeat: an `asyncio.create_task` loop (e.g. `asyncio.sleep(30)` then broadcast)
    scoped to app lifespan, or reuse an `arq` cron job if the worker infra is already
    running arq for delivery retries.
  - `SubscriptionStatus`/`Bundle` payload shapes: these are just Python dicts built
    to match the FHIR `Bundle` / `SubscriptionStatus` resource shape — no special
    library needed beyond whatever FHIR type validation fhir-gql already applies
    (compare to `app/schemas/patient/fhir_schemas.py`'s pattern).
- **Priority: High.** This is the feature most directly useful to a *clinical UI*
  specifically (vs. rest-hook, which mostly serves system-to-system integration) —
  live-updating dashboards are a common clinical UX requirement, and this is the
  standard FHIR-native way to build them. Sequence after rest-hook delivery + the
  fhir-server event stream are working, since it depends on the same match pipeline.

---

### Generic WebSocket Echo/Test Endpoint

- **What it does:** A trivial WebSocket endpoint that echoes back whatever it
  receives. Purely a smoke-test/dev-tool for verifying WebSocket connectivity,
  load balancer/proxy WebSocket pass-through configuration, and the Redis pub/sub
  round-trip, independent of any FHIR-specific logic.
- **Source files:** `packages/server/src/ws/echo.ts` — `handleEchoConnection()`,
  `initEchoHeartbeat()`/`stopEchoHeartbeat()` (metrics only, no functional role).
- **How it works:** On connect, subscribes to a **freshly generated random Redis
  channel** (`randomUUID()`) unique to this one connection, and on every inbound
  client message, publishes it to that same channel rather than echoing directly
  in-process. This is a deliberate design choice: it exercises the *entire* pub/sub
  round-trip (publish → Redis → subscribe → deliver) as a health check for that
  infrastructure specifically, not just "is the WebSocket itself alive." Listeners
  are bound before the `subscribe()` await resolves, to avoid dropping messages sent
  immediately after connect.
- **Belongs in: fhir-gql (middleware).** Trivial, self-contained, no data-layer
  interaction at all.
- **Port notes for fhir-gql (FastAPI/Python):** A ~15-line FastAPI WebSocket route.
  Worth keeping the same "round-trip through Redis pub/sub" design if fhir-gql wants
  it to double as an infra health check rather than just a network-level ping;
  otherwise a plain in-process echo is simpler and sufficient.
- **Priority: Low.** Pure dev/ops convenience, not a product feature. Cheap to add
  once the WebSocket infrastructure feature exists — implement it first as the
  simplest possible validation that WebSocket routing, auth-free access, and (if
  desired) the Redis round-trip all work end-to-end, before building the more complex
  Subscription channel on top of the same infrastructure.

---

### FHIRcast Real-Time Context Synchronization Protocol

- **What it does:** A separate real-time protocol (not part of core FHIR — a distinct
  HL7 specification, STU2/STU3) for synchronizing "what a clinician is currently
  looking at" across multiple independent applications in the same session — e.g. an
  EHR, a PACS/imaging viewer, and a dictation tool all need to stay pointed at the
  same Patient/Encounter/DiagnosticReport/ImagingStudy as the user navigates in any
  one of them. This is the standard mechanism for multi-app context sync in radiology
  and other imaging-heavy clinical workflows (SMART on FHIR's companion real-time
  spec).
- **Source files:** `packages/server/src/fhircast/routes.ts` (HTTP: subscribe/publish
  REST endpoints, `.well-known/fhircast-configuration` discovery, get-current-context),
  `packages/server/src/fhircast/utils.ts` (Redis key helpers, `getCurrentContext`,
  `setTopicCurrentContext`, `getTopicForUser`), `packages/server/src/ws/fhircast.ts`
  (the WebSocket hub connection that actually delivers events to subscribed apps).
- **How it works:**
  - **Topics**: a `topic` is an opaque ID identifying one "session" shared across
    apps (`getTopicForUser` mints one per user, cached with `SET ... NX` + `EXPIRE`
    of 3600s — matching FHIRcast's requirement that a subscription lease not outlive
    its OAuth token).
  - **Subscribe flow**: `POST /fhircast/:version` with `hub.mode=subscribe`,
    `hub.channel.type=websocket`, `hub.topic=...` — server generates (or reuses, via
    Redis `SETNX`) a random per-topic `subscriptionEndpoint`, maps
    `endpoint → {projectId}:{topic}` in Redis, and returns
    `hub.channel.endpoint = wss://.../ws/fhircast/{subscriptionEndpoint}`. The client
    then opens a WebSocket to that URL; `ws/fhircast.ts`'s
    `handleFhircastConnection()` looks up the endpoint's `projectId:topic`, subscribes
    to that Redis Pub/Sub channel, and forwards every published message verbatim to
    the socket. Reference-counts topics (`topicRefCountMap`) across possibly many
    sockets sharing one topic.
  - **Publish flow (context change)**: `POST /fhircast/:topic` with an `event`
    payload (`hub.event` = e.g. `Patient-open`, `DiagnosticReport-update`,
    `ImagingStudy-close`) — validated, then `publish()`ed onto the topic's Redis
    channel so every subscribed WebSocket (potentially spanning multiple app
    instances) receives it. `-open`/`-close`/`-update` events additionally maintain a
    **current-context cache** in Redis (`getTopicCurrentContextKey`,
    `getTopicContextStorageKey`) so a late-joining app can `GET /fhircast/:topic` and
    immediately learn "what's open right now" instead of waiting for the next event.
  - **DiagnosticReport-update** is the most complex event: it carries a JSON-Patch-like
    "update Bundle" (PUT/DELETE entries only) applied to a **content Bundle** tracked
    per-context, with strict optimistic-concurrency versioning
    (`context.versionId`/`context.priorVersionId` must match exactly or the request is
    rejected `400`) — this is effectively a mini collaborative-editing protocol for
    shared draft report content across apps.
  - **Heartbeat**: every heartbeat tick, one FHIRcast heartbeat event per active topic
    is published to keep subscribers aware the hub is alive.
- **Belongs in: fhir-gql (middleware) — this one is almost entirely orchestration,
  with essentially no dependency on fhir-server at all.** Unlike core FHIR
  Subscriptions, FHIRcast context state ("what's currently open") is ephemeral
  session state, not a persisted FHIR resource change — it never needs to originate
  from a fhir-server write. The only interaction with fhir-server would be
  incidental (e.g. resolving a `Patient`/`DiagnosticReport` reference embedded in a
  context payload for display), which fhir-gql already knows how to do via
  `FhirClient`. This makes FHIRcast one of the *cleanest* fits for fhir-gql to own
  outright in this entire document.
- **Port notes for fhir-gql (FastAPI/Python):** Structurally this is: (a) a handful
  of REST routes (`app/routers/fhircast.py`, following the existing
  `app/routers/patient.py` pattern) for subscribe/publish/get-current-context/
  well-known-config, (b) a FastAPI WebSocket route for the hub connection, and (c)
  Redis for topic↔endpoint mapping, per-topic Pub/Sub, and current-context caching —
  all directly portable idioms already covered by the WebSocket infrastructure and
  Redis pub/sub features above. The optimistic-concurrency version-check logic on
  `DiagnosticReport-update` is plain Python conditional logic, no special library
  needed. This is a good candidate to build as a fully independent module
  (`app/fhircast/`) since it has almost no coupling to the Patient/FHIR-resource code
  fhir-gql has today.
- **Priority: Medium.** High technical fit for fhir-gql, but the *product* need is
  narrow — FHIRcast specifically serves imaging/multi-app-context-sync workflows.
  Build it only if/when fhir-gql's roadmap includes imaging viewer integration or
  similar multi-application session sync; otherwise it's speculative scope. Flagged
  here as "ready to build" rather than "needed now."

---

### Agent WebSocket Channel (Device/Gateway Message Relay)

- **What it does:** A specialized WebSocket protocol for Medplum's "Agent" — a
  lightweight software gateway deployed on-prem near medical devices (HL7 v2
  interfaces, DICOM devices) that relays messages between those devices and the
  Medplum server, executing a `Bot` to transform/route each message.
- **Source files:** `packages/server/src/ws/agent.ts` — `handleAgentConnection()`
  (connect/heartbeat/transmit message handling), `handleConnect`/`handleTransmit`
  (auth via access token, resolves the `Agent` and target `Bot` resources, calls
  `executeBot`), `updateAgentInfo`/`updateAgentStatus` (writes connection state to
  Redis with a 24h TTL, read by a separate `$status` FHIR operation for monitoring).
- **How it works:** The on-prem Agent process opens a WebSocket and sends
  `agent:connect:request` with an access token + `agentId`; server verifies, reads
  the `Agent` resource, subscribes to a Redis Pub/Sub channel keyed by the agent's own
  reference string (so other parts of the system can push messages *to* the agent by
  publishing there), and tracks connection state (`CONNECTED`/`DISCONNECTED`) in
  Redis for the `$status` operation to read. `agent:transmit:request` messages carry
  an HL7v2/JSON/FHIR-JSON payload plus a target `channel` name that maps (via the
  `Agent.channel[]` config) to a `Bot` reference, which is then executed
  (`executeBot`) and the result relayed back.
- **Belongs in: neither, currently — out of scope.** This entire feature is built on
  top of two things fhir-gql does not have: a `Bot`/serverless-execution runtime
  (`executeBot`), and a device-gateway deployment model. It is not "fhir-server vs.
  fhir-gql" — it's a different product surface (on-prem device integration) that
  neither service currently addresses. Flagging it here only because `agent.ts` was
  in scope for this document, and to correctly scope it *out* rather than silently
  omit it.
- **Port notes for fhir-gql (FastAPI/Python):** Not recommended to build until/unless
  fhir-gql (or a sibling service) grows a Bot-equivalent execution model — without
  that, there is nothing for a transmitted device message to be routed *to*. If this
  becomes a roadmap item, the WebSocket connection-management and Redis-pub/sub
  relay pattern here is directly reusable from the infrastructure already recommended
  above.
- **Priority: Low.** Not aligned with fhir-gql's current scope (REST/GraphQL
  middleware over a Patient-only resource set, no device integration or bot runtime).
  Revisit only if device/HL7v2 gateway integration enters the roadmap.

---

### AI-Realtime WebSocket Proxy

- **What it does:** A thin authenticated WebSocket proxy that lets a browser client
  talk to OpenAI's Realtime API (voice transcription/streaming) without exposing the
  OpenAI API key to the browser — the server holds the key (from
  `Project.secret`), the browser only ever holds a short-lived Medplum access token.
  Useful for ambient clinical documentation / voice-driven note-taking features.
- **Source files:** `packages/server/src/ws/ai-realtime.ts` —
  `handleAiRealtimeConnection()`, `connectToUpstream()` (validates access token +
  project feature flag `ai-realtime`, reads the `OPENAI_API_KEY` from project
  secrets, opens an upstream `ReconnectingWebSocket` to OpenAI with the key injected
  server-side), `bindUpstreamSocket()` (bidirectional message/error/close relay
  between the client socket and the upstream OpenAI socket).
- **How it works:** Client connects and must send `{type: 'ai-realtime:connect',
  accessToken}` as its first message (binary frames before that are rejected with
  close code `1008`). Server authenticates, checks a project feature flag gate,
  looks up the API key, and opens the upstream connection using OpenAI's
  `ReconnectingWebSocket` (auto-reconnect on transient upstream drops). From then on
  it's a pure bidirectional byte-pipe: client→server frames are forwarded verbatim
  upstream, upstream frames are forwarded verbatim back to the client, and
  close/error events on either side propagate to the other with normalized close
  codes (any code outside the valid WebSocket range 1000–4999 is remapped to `1011`
  Internal Error).
- **Belongs in: fhir-gql (middleware), if pursued at all.** This has zero FHIR
  data-layer dependency — it's a generic "authenticated proxy to a third-party
  realtime API, keeping the API key server-side" pattern. It would sit entirely on
  fhir-gql's side, reusing its existing JWT auth (`app/auth/dependencies.py`) for the
  handshake and needing no interaction with fhir-server at all beyond, at most,
  fetching a config/secret value.
- **Port notes for fhir-gql (FastAPI/Python):** A FastAPI WebSocket route that opens
  a second outbound WebSocket client connection (e.g. via `websockets` library, since
  `httpx` doesn't do WebSocket) to the upstream provider, then relays frames in both
  directions with two concurrent `asyncio` tasks (one pumping client→upstream, one
  upstream→client) — this is a very standard asyncio proxy pattern (`asyncio.gather`
  of two forwarding loops, cancel both on either side closing). No FHIR-specific
  code needed.
- **Priority: Low.** Speculative — only relevant if/when fhir-gql's product roadmap
  includes an ambient-voice/AI-transcription feature. Technically trivial to add
  later; no reason to build ahead of an actual product requirement.

---

### Inbound Anonymous Webhook Receiver (Bot-Triggered Public Webhook)

- **What it does:** The *inbound* counterpart to rest-hook delivery — lets an
  external system POST to a public, unauthenticated URL (scoped to a specific `Bot`
  via a `ProjectMembership`) to trigger server-side logic, e.g. receiving a webhook
  from a lab results vendor, a payment processor, or a third-party scheduling system
  that doesn't support FHIR-native auth.
- **Source files:** `packages/server/src/webhook/routes.ts` — `webhookHandler()`,
  `webhookRouter` (`POST /webhook/:id` where `:id` is a `ProjectMembership` ID).
- **How it works:** No authentication at all on the route itself — security is
  enforced entirely through configuration: the target `ProjectMembership` must (1)
  belong to a `Bot` profile, (2) have an `AccessPolicy` attached, and (3) the `Bot`
  resource must have `publicWebhook: true` explicitly set. If all three hold, the
  request body (POST) or query string (GET) is passed as input to `executeBot()`
  running *as* that Bot's membership (so the Bot's own AccessPolicy scopes what it
  can read/write), and the Bot's return value becomes the HTTP response.
- **Belongs in: neither, currently — depends on infra fhir-gql doesn't have.** This
  entire feature exists to trigger arbitrary server-side execution (`executeBot`),
  which requires the Bot/serverless-runtime concept fhir-gql does not have, same as
  the Agent channel above. The *inbound public endpoint with scoped identity*
  pattern itself is reusable, but there is currently nothing on the fhir-gql side for
  it to invoke.
- **Port notes for fhir-gql (FastAPI/Python):** Not recommended until fhir-gql (or
  fhir-server) has some equivalent of a Bot/scripted-handler execution model. If a
  narrower need shows up first (e.g. "receive a webhook from an external lab and
  create/update a specific known resource type"), it would be simpler and safer to
  build a small number of purpose-built inbound endpoints with real authentication
  (a shared secret / HMAC verification of the sender, not Medplum's
  all-or-nothing-on-Bot-config model) rather than porting the generic Bot-execution
  webhook receiver as-is.
- **Priority: Low.** No current use case in fhir-gql's Patient-only scope; revisit
  once specific inbound-integration requirements exist, and consider a narrower,
  purpose-built design rather than a direct port.

---

## Summary Table

| Feature | Priority | Belongs in |
|---|---|---|
| FHIR Subscription Resource — Rest-Hook Webhook Delivery | High | Both, coordinated |
| Subscription Delivery Retry, Backoff, and Dead-Letter Handling | High | fhir-gql (middleware) |
| Subscription Auto-Disable on Repeated Failure | Medium | fhir-gql (middleware) |
| Dispatch Worker — Post-Write Event Fan-out Hook | High (cross-team blocker) | Both, coordinated (trigger in fhir-server) |
| Cross-Instance Redis Pub/Sub Fan-out Layer | High | fhir-gql (middleware) |
| WebSocket Server Infrastructure & Connection Lifecycle | High | fhir-gql (middleware) |
| FHIR WebSocket Subscription Channel (SubscriptionStatus protocol) | High | fhir-gql (middleware), matching resolved upstream |
| Generic WebSocket Echo/Test Endpoint | Low | fhir-gql (middleware) |
| FHIRcast Real-Time Context Synchronization Protocol | Medium | fhir-gql (middleware) |
| Agent WebSocket Channel (Device/Gateway Relay) | Low | Out of scope (needs Bot runtime) |
| AI-Realtime WebSocket Proxy | Low | fhir-gql (middleware), if pursued |
| Inbound Anonymous Webhook Receiver (Bot-Triggered) | Low | Out of scope (needs Bot runtime) |

## Recommended Next Steps

The single hardest architectural fact in this domain is that **fhir-gql cannot
reliably originate a subscription trigger from its own request handlers** — any
write to fhir-server that doesn't route through fhir-gql (bulk import, another
service, a migration) would be invisible to it. That makes the *first* concrete step
a cross-repo one: get a minimal event-emission hook added to fhir-server's write
path — on every committed create/update/delete, `XADD` a compact event
(`resourceType`, `id`, `versionId`, `previousVersionId`, `interaction`, `tenantId`,
`timestamp`) to a Redis Stream (e.g. `fhirserver:resource-events`). This is
deliberately the *smallest possible* fhir-server change — no Subscription knowledge,
no criteria matching, no delivery logic moves into fhir-server. Everything else in
this document is fhir-gql-side.

Proposed fhir-gql architecture, in build order:

1. **WebSocket infrastructure** (`app/ws/` or similar, wired into `app/main.py`
   alongside the existing middleware stack) — FastAPI native WebSocket routes,
   connection tracking, graceful shutdown in `lifespan()`. Validate with the Echo
   endpoint first.
2. **Redis role split** — add a dedicated pub/sub-subscriber Redis client alongside
   the existing `redis_client` (which stays general-purpose/cache, matching
   Medplum's `getCacheRedis()` vs. `getPubSubRedis()` split), since a subscribed
   connection can't run other commands.
3. **`Subscription` resource CRUD** (`app/routers/subscription.py`,
   `app/gql/resolvers/subscription.py`, following the existing Patient-slice
   pattern), persisted through `FhirClient` to fhir-server as an ordinary FHIR
   resource — single source of truth, no dual-write problem.
4. **arq-based worker pool** on the existing Redis instance: one consumer group
   reading the fhir-server event stream (criteria matching + fan-out to per-channel
   delivery queues), one queue for rest-hook HTTP delivery (retry/backoff per the
   capped-exponential-with-jitter formula documented above), one for websocket-channel
   fan-out (publish already-matched events to the in-process socket lookup, same
   `subToWsLookup`/`wsToSubLookup` pattern).
5. **FHIR WebSocket Subscription channel** (`$get-ws-binding-token`-equivalent
   operation + `/ws/subscriptions-r4`-equivalent route) on top of steps 1–4.
6. **Subscription auto-disable** (sliding-window failure counter, reusing/extending
   the `RateLimitMiddleware` Redis idiom) once the core delivery path is stable.
7. **FHIRcast**, if/when imaging or multi-app context-sync becomes a product
   requirement — independent module, minimal coupling to the rest of fhir-gql.

Everything gated on step (0), the fhir-server event hook, should be raised with
whoever owns that repo now, in parallel with steps 1–2, since it is the longest-lead
dependency and blocks steps 3 onward from being end-to-end testable.
