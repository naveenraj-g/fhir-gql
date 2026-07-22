# Automation & Bots: Medplum vs. fhir-gql

Scope: Bot resource execution (sandboxing/runtimes), bot deployment pipelines, the Bot
input/output contract, CDS Hooks (SMART CDS Hooks spec), cron-based scheduled automation,
and the async/batch job processing framework.

Medplum source reviewed (`packages/server/src`): `bots/execute.ts`, `bots/types.ts`,
`bots/utils.ts`, `bots/vmcontext.ts`, `cds/routes.ts`, `workers/batch.ts`, `workers/cron.ts`,
`cloud/aws/lambda.ts`, `cloud/aws/execute.ts`, `cloud/aws/executestreaming.ts`,
`cloud/aws/deploy.ts`, `cloud/aws/deploystreaming.ts`, `cloud/fission/deploy.ts`,
`cloud/fission/execute.ts`, `cloud/fission/utils.ts`, `cloud/fission/wrapper.ts`.

fhir-gql context: a FastAPI/Strawberry middleware layer in front of a separate fhir-server
that owns persistence. Only Patient is implemented today. There is no bot engine, no job
queue, and no CDS Hooks support — this entire domain is greenfield. Redis is already wired
up (`app/core/redis.py`, used today only for rate limiting) which matters for job-queue
port notes below.

---

### Bot Resource & Execution Dispatch

- **What it does:** A `Bot` is a FHIR resource holding user-authored JavaScript/TypeScript
  that runs server-side — triggered by a FHIR event (Subscription on create/update), invoked
  on-demand via `$execute`, called as a CDS Hooks service, or run on a cron schedule. This is
  the automation/business-rule-engine primitive clinical platforms need for things like
  "auto-flag abnormal labs," "sync a new Patient to an external registry," "generate a PDF
  discharge summary," or "reject an Observation that violates a business rule." Without it,
  every such rule has to be hardcoded into the server itself.
- **Source files:** `src/bots/execute.ts` (`executeBot`) — the single dispatch entrypoint;
  `src/bots/types.ts` (`BotExecutionRequest`, `BotExecutionContext`, `BotExecutionResult`) —
  the shared contract every runtime adapter must satisfy; `src/bots/utils.ts`
  (`isBotEnabled`, `getBotAccessToken`, `getBotSecrets`, `writeBotInputToStorage`,
  `normalizeBotExecutionResult`, `sendBotResponse`, `getJsFileExtension`) — supporting
  plumbing shared by every runtime.
- **How it works:**
  - `executeBot()` is the single chokepoint all trigger paths funnel through (HTTP
    `$execute`, Subscription delivery, CDS Hooks, cron). It: (1) checks `isBotEnabled` —
    reads the owning `Project` and requires the `bots` feature flag; (2) calls
    `writeBotInputToStorage` to persist the raw input as a JSON blob in binary storage,
    keyed `bot/{project}/{yyyy/mm/dd}/{timestamp}-{uuid}.json`, partitioned for later Athena
    analytics/debugging/replay; (3) builds a `BotExecutionContext` by minting a **fresh
    Login + OAuth access token** for the bot's `runAs` ProjectMembership
    (`getBotAccessToken`) and resolving layered secrets (`getBotSecrets`); (4) dispatches by
    `bot.runtimeVersion` to one of three runtimes: `awslambda`, `vmcontext`, or `fission`;
    (5) normalizes the result (a returned non-OK `OperationOutcome` flips `success` to
    false) and records an OpenTelemetry histogram plus a `AuditEvent` for every execution
    (success or failure) — this is the audit trail a clinical platform needs to prove what
    automation ran against a patient record and when.
  - The **execution contract** (`BotExecutionContext`) passed into every runtime is
    identical regardless of sandbox: `{ bot, runAs, requester, input, contentType,
    accessToken, secrets, subscription?, agent?, device?, traceId?, headers?,
    responseStream? }`. Every runtime's wrapper code destructures this into a `medplum`
    SDK client (pre-authenticated with the minted access token) and calls the user's
    exported `handler(medplum, { bot, requester, input, contentType, secrets, traceId,
    headers })`. The **output contract** (`BotExecutionResult`) is `{ success: boolean,
    logResult: string, returnValue?: any }` — `logResult` is captured console output,
    `returnValue` is whatever the handler returned (resource, string, boolean, or an
    `OperationOutcome` for errors).
  - Secrets resolution (`getBotSecrets`) layers up to 4 sources with "most specific wins":
    bot-project system secrets → bot-project secrets → runAs-project system secrets →
    runAs-project secrets. This lets a bot shared across projects still see per-tenant
    overrides.
  - HL7v2 input gets special treatment throughout: `writeBotInputToStorage` parses PID/OBX/MSH
    segments into extra columns for analytics; every runtime stringifies `Hl7Message` for
    transport and re-parses it inside the sandbox before calling the handler.
- **Belongs in:** Conceptually this is `fhir-gql (middleware)` territory — dispatch, secrets
  resolution, auditing, and the runtime-selection decision are all orchestration concerns
  that sit naturally next to the JWT/RBAC/rate-limiting fhir-gql already owns, not raw data
  persistence. However, the *actual sandboxed code execution* (the three runtime adapters
  below) is a distinct concern from both orchestration and persistence — see each runtime's
  entry for why it likely wants to be a **separate execution service**.
- **Port notes for fhir-gql (FastAPI/Python):** Model `Bot` as a new resource type following
  the existing `PatientService` → `PatientClient` pattern (`app/services/bot_service.py` →
  `app/fhir_client/bot.py`), with the Bot *definition* (code, runtime, secrets refs, trigger
  config) persisted on the downstream fhir-server like any other resource. Add a
  `BotExecutionService` in fhir-gql that mirrors `executeBot()`: validate `isBotEnabled`,
  build an execution context (mint a scoped JWT for `runAs`, resolve secrets — potentially
  from a secrets manager instead of Project resources), dispatch to a runtime backend by
  `runtimeVersion`, normalize the result, and emit an audit log entry (fhir-gql already has
  auth/RBAC machinery to attach actor identity — extend that pattern here). Define the
  execution contract as Pydantic models (`BotExecutionRequest`/`Context`/`Result`) mirroring
  `types.ts` 1:1 so the shape stays stable across runtimes.
- **Priority:** High — this is the entry point for the entire automation domain; nothing
  else here works without a dispatch layer and a stable input/output contract.

---

### VM Context Bots (in-process Node `vm` sandbox)

- **What it does:** Runs bot JavaScript directly inside the server process using Node's
  built-in `vm` module. Fastest and simplest runtime — no external infra — but explicitly
  **not a security boundary**.
- **Source files:** `src/bots/vmcontext.ts` (`runInVmContext`, `DEFAULT_VM_CONTEXT_TIMEOUT`).
- **How it works:** Gated behind a server config flag (`vmContextBotsEnabled`) that must be
  explicitly turned on — the file's top-of-file comment is blunt about the threat model:
  *"This is intentionally powerful and must be treated as unsafe for untrusted code... not
  intended to be a sandbox boundary for hostile users, multi-tenant user-submitted code, or
  arbitrary third-party JavaScript."* It's meant only for local dev or single-tenant
  deployments where whoever can write Bot code already has server-equivalent trust.
  Mechanically: fetches the bot's compiled code from Binary storage, wraps it in an async
  IIFE that constructs a `MedplumClient` pre-authenticated with the minted access token,
  parses HL7v2 input if needed, and calls `exports.handler(medplum, event)`. The sandbox
  object passed to `vm.runInNewContext` exposes `console` (captured via `MockConsole`),
  `fetch`, `require` (via `createRequire` — meaning the bot **can require arbitrary Node
  built-ins/installed packages**, which is exactly why this isn't a real sandbox), `process`,
  and various Medplum SDK types. Execution is capped by `vm.RunningScriptOptions.timeout`
  (`bot.timeout * 1000` or a 10s default) — this bounds wall-clock CPU time but Node's `vm`
  module does **not** isolate memory, filesystem, network, or the global process — a
  malicious bot can still access `process.env`, spawn child processes via `require('child_process')`,
  or exhaust memory to crash the host.
- **Belongs in:** `separate execution service` for anything beyond local dev — the source
  comment itself concedes this isn't a sandbox boundary. If ported at all, it should never
  run inside the same process that holds JWT signing keys, database credentials, or serves
  other tenants' requests.
- **Port notes for fhir-gql (FastAPI/Python):** Do **not** replicate this pattern as "run
  eval() in the FastAPI process" — Python has no equivalent of a semi-isolated VM context,
  and `exec()`/`eval()` in-process is strictly worse than Node's `vm` module (no timeout
  primitive, no separate global object). If an in-process low-security option is wanted for
  local dev only, `RestrictedPython` (compiles a restricted AST, blocks dunder access and
  dangerous builtins) is the closest analog, run inside a subprocess with a `SIGALRM`/
  `multiprocessing` timeout and `resource.setrlimit` for CPU/memory caps — but treat it as
  dev-only, gated by an explicit config flag, exactly as Medplum does.
- **Priority:** Low — useful for local development ergonomics only; not something to build
  out for production use given the security posture. Do not prioritize over the sandboxed
  runtimes below.

---

### AWS Lambda Bot Runtime (deploy + execute)

- **What it does:** Runs each bot as its own AWS Lambda function — one function per bot,
  provisioned and versioned independently. This is Medplum's recommended production sandbox:
  real OS-level process isolation, per-bot resource limits, and AWS-managed scaling.
- **Source files:** `src/cloud/aws/lambda.ts` (`getBotManagementLambdaClient`,
  `deleteOldLambdaVersions` — version pruning/GC); `src/cloud/aws/execute.ts`
  (`runInLambda`, `buildLambdaPayload`, `getLambdaFunctionName`, `parseLambdaLog`,
  `sanitizeLogResult`); `src/cloud/aws/executestreaming.ts` (`runInLambdaStreaming`,
  `processEventStream` — SSE-style streaming responses); `src/cloud/aws/deploy.ts`
  (`deployLambda`, `deployLambdaInternal`, `createBotZipFile`, `createLambda`,
  `updateLambda`, `LAMBDA_RUNTIME`, `LAMBDA_HANDLER`, `MAX_LAMBDA_TIMEOUT=900`);
  `src/cloud/aws/deploystreaming.ts` (`deployLambdaStreaming` — variant using
  `awslambda.streamifyResponse`).
- **How it works:**
  - **Deployment** (`deploy.ts`): the bot's raw code is wrapped with a generated CJS or ESM
    prefix (`getJsFileExtension` sniffs `export`/`module.exports` usage or a `.cjs`/`.mjs`
    Binary title to decide) that constructs a `MedplumClient` from the incoming event,
    injects trace headers, exposes a `createPdf()` helper (backed by `pdfmake`, with bundled
    Helvetica/Roboto/Avenir font files via a Lambda Layer), calls the user's `handler`,
    catches `OperationOutcomeError` specially, and returns the result. The zipped bundle
    (`user.cjs`/`user.mjs` + `index.cjs`/`index.mjs`) is deployed via
    `CreateFunctionCommand`/`UpdateFunctionCodeCommand` against a shared Lambda Layer
    (`getLayerVersion` — pulls the latest published layer with the `@medplum/core` SDK and
    `pdfmake` pre-installed, keeping per-bot zips small). Function name is deterministic:
    `medplum-bot-lambda-{botId}` (or an operator-configured custom function id if
    `botCustomFunctionsEnabled`). `updateLambdaConfig` diffs the existing config
    (runtime/handler/layer/timeout) and only calls `UpdateFunctionConfigurationCommand` if
    something actually changed — avoiding unnecessary Lambda cold-starts/version bumps.
    `updateLambdaCode` retries up to 5x with exponential backoff on
    `ResourceConflictException` (Lambda is "still updating" from a previous deploy). After
    every update, `deleteOldLambdaVersions` runs **fire-and-forget** to prune old published
    versions (default: keep latest 2), skipping any version that still has an alias pointing
    to it. Bot timeout is capped at AWS's hard limit of 900s (15 min).
  - **Execution** (`execute.ts`): `runInLambda` builds the payload from
    `BotExecutionContext` (bot ref, baseUrl, accessToken, requester, input, contentType,
    secrets, traceId, headers), invokes synchronously (`InvocationType: RequestResponse`)
    with `LogType: Tail` to get the last 4KB of CloudWatch logs back inline, and parses
    `response.FunctionError` to determine `success`. `parseLambdaLog` strips AWS's
    START/END/REPORT markup lines from the base64-encoded tail log, and `sanitizeLogResult`
    strips control characters that would violate FHIR string validation before the log is
    written into an AuditEvent.
  - **Streaming execution** (`executestreaming.ts`): for bots needing to stream a response
    (e.g., long-running report generation) — uses `InvokeWithResponseStreamCommand`. The
    Lambda wrapper (`deploystreaming.ts`) writes a JSON "preamble" line
    (`{statusCode, headers}`) as the first chunk so the server knows how to start the HTTP
    response, then raw body chunks follow; `processStreamingPreamble` buffers until it finds
    the newline-delimited preamble (capped at 64KB to avoid unbounded buffering), then pipes
    subsequent chunks straight to the client's `responseStream`. A `nonStreamingResponse`
    flag lets a bot fall back to a normal buffered JSON response even in streaming mode.
  - Isolation model: each bot is a **separate Lambda function** — separate execution
    environment, separate IAM role (`botLambdaRoleArn`, shared across bots but scoped away
    from the main server's credentials), separate memory/CPU allocation (1024MB fixed),
    separate timeout. AWS's Firecracker microVM isolation is the actual security boundary —
    this is real multi-tenant-safe sandboxing, unlike vmcontext.
- **Belongs in:** `separate execution service` — bot deployment/invocation talks to AWS's
  Lambda control plane directly and is architecturally independent of both fhir-gql's
  request orchestration and the fhir-server's persistence. It could be *orchestrated* by
  fhir-gql (deciding when to invoke a bot, building the payload, handling the result) while
  the actual Lambda function inventory/deployment lives in dedicated
  infrastructure-as-code/deployment tooling — but the runtime boundary itself (AWS account,
  IAM roles, function code) is a separate execution surface from either service's current
  responsibilities and should not be embedded in FastAPI request handling.
- **Port notes for fhir-gql (FastAPI/Python):** This maps cleanly onto Python + `boto3`.
  Deployment: build a zip with `user_code.py` + a generated wrapper (equivalent CJS/ESM
  prefix logic isn't needed in Python — just a fixed `lambda_handler` that imports
  `user_code` and calls `user_code.handler(client, event)`), publish via
  `boto3.client("lambda").create_function`/`update_function_code`, same layer strategy for a
  shared `httpx`-based FHIR client SDK. Execution: `client.invoke(FunctionName=..., Payload=...)`
  for sync, or Lambda response streaming (`invoke_with_response_stream`, boto3 supports this)
  for SSE-like use cases — wire this into fhir-gql as an async wrapper via
  `asyncio.to_thread` since boto3 is sync. Build `BotExecutionService.run_in_lambda()`
  parallel to `PatientService`'s pattern: a thin orchestration method that builds the payload
  (bot ref, minted JWT, secrets, input) and calls out to a `LambdaBotClient`. Timeout,
  version pruning, and IAM role scoping port directly as config values.
- **Priority:** High — this is the production-grade sandboxing story; if fhir-gql wants to
  offer bots at all beyond a toy/dev feature, Lambda-per-bot (or an equivalent
  container-per-bot approach) is the realistic target, not in-process execution.

---

### Fission/Kubernetes Bot Runtime

- **What it does:** Alternative bot runtime for self-hosted/Kubernetes deployments that don't
  use AWS — runs each bot as a Fission (serverless-on-k8s) function, giving the same
  per-bot isolation story as Lambda but on any Kubernetes cluster.
- **Source files:** `src/cloud/fission/deploy.ts` (`deployFissionBot`); `src/cloud/fission/execute.ts`
  (`executeFissionBot`); `src/cloud/fission/utils.ts` (`deployFissionFunction`,
  `executeFissionFunction`, `getFissionConfig`, `FissionFunctionResponse`);
  `src/cloud/fission/wrapper.ts` (`FISSION_INDEX_CODE`, `FISSION_PACKAGE_JSON`).
- **How it works:**
  - **Deployment**: zips `user.js` + a fixed `index.js` wrapper + a generated
    `package.json` declaring a dependency on `@medplum/bot-layer`, then talks directly to
    the Kubernetes API (`@kubernetes/client-node`'s `CustomObjectsApi`) to create/patch three
    Fission CRDs: a `Package` (the code, base64-literal-encoded, referencing a pre-built
    Fission `environment`), a `Function` (binds the package's `index` export, configured with
    `ExecutorType: poolmgr`, `MinScale: 0`/`MaxScale: 1` — scale-to-zero — `concurrency: 500`,
    `functionTimeout: 60s`, `idletimeout: 120s`), and an `HTTPTrigger` (exposes it at
    `/bot-{botId}` on Fission's router, POST only). Uses Kubernetes server-side apply
    (`PatchStrategy.ServerSideApply` with a `fieldManager`) so repeated deploys are
    idempotent merges rather than full replacements. Package names are timestamped
    (`bot-package-{id}-{Date.now()}`) since Fission packages are versioned by name.
  - **Execution**: `executeFissionBot` builds the same payload shape as Lambda, POSTs it as
    JSON to the Fission router at `http://{routerHost}:{routerPort}/bot-{id}`
    (`executeFissionFunction`), and interprets the JSON response body
    (`{success, returnValue, logResult}`) that the wrapper (`FISSION_INDEX_CODE`) produces.
  - The wrapper (`wrapper.ts`) itself monkey-patches `console.log/error/warn/info/debug` to
    capture output into an array (`logOutput`) that gets joined and returned in the response
    body — Fission functions don't have a built-in "get me the logs from this one
    invocation" API like Lambda's `LogType: Tail`, so log capture has to happen inside the
    function itself.
  - Isolation model: Kubernetes pod-per-function (with pooling/specialization for warm
    starts) — process + cgroup isolation, weaker than Lambda's Firecracker microVMs but still
    a real OS-level boundary, and it's the self-hosted alternative for teams that can't/won't
    use AWS.
- **Belongs in:** `separate execution service`, same reasoning as Lambda — this is a
  Kubernetes control-plane integration (creating CRDs, talking to the k8s API server) that's
  orthogonal to both fhir-gql's request orchestration and fhir-server's persistence.
- **Port notes for fhir-gql (FastAPI/Python):** Only worth building if/when fhir-gql commits
  to a self-hosted Kubernetes-native execution story — otherwise this is redundant with the
  Lambda path and adds real operational complexity (running a Fission cluster, or an
  equivalent like Knative/OpenFaaS). If pursued, the Python `kubernetes` client library
  mirrors `@kubernetes/client-node` closely (`CustomObjectsApi`, server-side apply). A
  simpler container-native alternative worth considering instead: **one-off Docker container
  per invocation** (via `docker run` / `podman run` with `--memory`, `--cpus`, `--network
  none` or an allowlist proxy, `--read-only` filesystem, non-root user, and a wall-clock
  timeout) orchestrated from fhir-gql through the Docker SDK for Python — gets most of the
  isolation benefit without standing up a full serverless-on-k8s framework, at the cost of
  slower cold starts than Fission's warm pools.
- **Priority:** Low/Medium — defer until there's a concrete self-hosted deployment target;
  Lambda (or plain per-invocation containers) covers the sandboxing need with far less
  operational surface area for a project at fhir-gql's current maturity.

---

### CDS Hooks (Clinical Decision Support service discovery & invocation)

- **What it does:** Implements the [CDS Hooks](https://cds-hooks.hl7.org/) spec — a
  standardized way for an EHR to call out to external decision-support services at specific
  points in a clinical workflow (e.g., the `patient-view` hook fires when a clinician opens a
  patient chart) and receive back "cards" (alerts, suggestions, links) to display inline.
  This is a widely-adopted interop standard in clinical platforms (drug-interaction checks,
  guideline reminders, risk scores) and is a natural fit on top of a Bot engine since each
  CDS service is just a Bot with hook metadata attached.
- **Source files:** `src/cds/routes.ts` (`cdsRouter`) — two routes: discovery (`GET /`) and
  invocation (`POST /:id`).
- **How it works:**
  - **Discovery** (`GET /cds-services`, spec-mandated path): queries all `Bot` resources
    where `cdsService` is present (`Operator.MISSING = false` filter), capped at 100 results
    since the spec has no pagination and real deployments rarely exceed a handful of
    services. Maps each into the spec's discovery response shape: `{ id, hook, title,
    description, usageRequirements, prefetch }` — `hook` identifies which workflow event
    triggers it (e.g. `"patient-view"`, `"order-select"`), `prefetch` is a map of FHIR
    query templates the calling EHR should resolve and pass along so the service doesn't
    have to make its own FHIR calls for common data.
  - **Invocation** (`POST /cds-services/{id}`): reads the Bot as the *authenticated user's*
    repo first (`ctx.repo.readResource`) purely to enforce normal RBAC/visibility — if the
    bot doesn't exist or isn't visible or has no `cdsService`, returns 404. Then re-reads it
    via the *system* repo to get full bot details (code, secrets refs) regardless of the
    user's own field-level permissions. Delegates straight to the shared `executeBot()` —
    same audit trail, same secrets resolution, same runtime dispatch as any other bot
    invocation — with `input: req.body` (the CDS Hooks request payload: context, prefetch
    data) and `contentType: JSON`. The result is sent back via the shared `sendBotResponse`
    helper, so a CDS service's `handler` just returns a plain object (the CDS Hooks
    response — `{ cards: [...] }`) like any other bot.
  - Notably there's **no CDS-Hooks-specific execution logic at all** — the entire feature is
    a thin routing/discovery layer bolted onto the generic bot execution pipeline. The
    protocol-specific parts (discovery response shape, hook names, cards) live entirely in
    the Bot resource's `cdsService` metadata and in whatever the bot handler itself returns.
- **Belongs in:** `fhir-gql (middleware)` — this is pure HTTP routing, discovery, and
  request/response shaping around bot execution, with zero persistence or sandboxing
  concerns of its own. It's the same shape as any other REST endpoint fhir-gql already
  builds (auth middleware → read a resource → call a service → format response), just backed
  by the Bot execution service instead of `PatientClient`.
- **Port notes for fhir-gql (FastAPI/Python):** Add `app/routers/cds.py` with two FastAPI
  routes: `GET /cds-services` and `POST /cds-services/{id}`, protected by the existing
  `authenticate_request`/`require_permission` dependency pattern used in
  `app/routers/patient.py`. Discovery calls a `BotClient.list_cds_bots()` (fetch Bots with
  `cdsService` populated from the fhir-server, same shape mapping as `routes.ts`).
  Invocation reads the Bot, calls `BotExecutionService.execute()` (see the dispatch section
  above) with the raw POST body as `input`, and returns the handler's return value directly
  as JSON — no special-casing needed since CDS Hooks responses are just JSON the bot handler
  produces. Define `CdsServiceDiscovery`/`CdsCard` as Pydantic response models for OpenAPI
  documentation and spec-shape validation. This is a good "prove the bot pipeline works"
  first customer once `BotExecutionService` exists, since the CDS layer itself is nearly
  zero-logic.
- **Priority:** Medium — high value once a bot execution backend exists (it's cheap to add
  and unlocks a standard clinical interop surface), but it has a hard dependency on the Bot
  execution pipeline being built first, so it can't be prioritized ahead of that.

---

### Cron-Scheduled Bot Automation

- **What it does:** Lets a Bot run on a recurring schedule (e.g., nightly data-quality
  sweep, weekly report generation) instead of only in response to an event. This is the
  "batch automation" half of the bot engine — the other trigger path besides
  create/update/on-demand.
- **Source files:** `src/workers/cron.ts` (`initCronWorker`, `addCronJobs`,
  `getCronStringForBot`, `convertTimingToCron`, `execBot`, `removeBullMQJobByKey`,
  `reloadCronBots`, `getCronQueue`, `CronJobData`).
- **How it works:** Built on **BullMQ** (Redis-backed job queue) using its `JobScheduler`
  feature (`queue.upsertJobScheduler(botId, { pattern: cronString }, { data })`) which
  natively supports cron-pattern-based repeatable jobs keyed by a stable ID (the bot ID, so
  re-registering just updates the existing schedule rather than duplicating it).
  - Two ways a Bot resource can define its schedule: a raw `bot.cronString` (validated with
    `cron-validator`'s `isValidCron`), or a FHIR `Timing` structure (`bot.cronTiming`) that
    gets algorithmically converted to a cron string by `convertTimingToCron` — it maps
    `timing.repeat.period` into either a `*/N` minute or hour pattern (capped at once/minute
    granularity) and `timing.repeat.dayOfWeek` (FHIR's `sun`/`mon`/... codes) into cron's
    numeric day-of-week field.
  - `addCronJobs` is invoked from the generic resource-write pipeline (not shown in this
    file set, but called via `BackgroundJobContext` on Bot create/update) — it's project-gated
    (`project.features.includes('cron')`), diffs the effective cron string between the
    previous and new bot version, and only touches the queue if it actually changed
    (add/update via `upsertJobScheduler`, or remove via `removeJobScheduler` if the cron was
    cleared).
  - `execBot` is the BullMQ worker callback: given a `botId`, it reads the Bot via the
    system repo, resolves the bot's own `runAs` project membership (`findProjectMembership`),
    and calls the same shared `executeBot()` with `input: bot` and `contentType:
    FHIR_JSON` — i.e., a cron-triggered bot receives *itself* (the Bot resource) as input,
    since there's no triggering event/resource to pass.
  - `reloadCronBots` is a startup/recovery routine: `queue.obliterate({ force: true })` wipes
    all existing scheduled jobs (including active ones) and then re-scans every Bot resource
    in the system (`processAllResources`, paginated 500 at a time with a 1s delay between
    pages to avoid hammering the DB) re-registering cron jobs from scratch — this is how the
    in-memory/Redis schedule state gets reconciled with the source-of-truth Bot resources
    after a restart or config change.
- **Belongs in:** Split concern. The *scheduling infrastructure* (queue, worker, reconciling
  schedules with Bot resource state) is an orchestration concern that fits `fhir-gql
  (middleware)` — it's really just "call executeBot() on a timer," no different in kind from
  the CDS Hooks router calling it on an HTTP POST. But note this worker needs to run as a
  **long-lived background process** (a BullMQ `Worker` polling Redis), which is a different
  deployment shape than FastAPI's per-request model — it can't just live inside a request
  handler.
- **Port notes for fhir-gql (FastAPI/Python):** Redis is already provisioned
  (`app/core/redis.py`), so the natural port is **`arq`** (asyncio-native Redis job queue,
  designed for FastAPI-style codebases) or **Celery beat** if broader ecosystem/tooling
  matters more than async-native fit. Either supports cron-style scheduling. Structure:
  a `CronSchedulerService` mirroring `addCronJobs`/`getCronStringForBot` — on Bot
  create/update (via the Bot service's write path, same place `PatientService.update` stamps
  `updated_by`), diff the effective cron string and register/deregister the schedule.
  `convertTimingToCron` ports near-verbatim as a pure function (FHIR `Timing` → cron string).
  The actual scheduled task is a small async function that mirrors `execBot`: fetch the Bot,
  resolve `runAs`, call `BotExecutionService.execute()`. This needs a **separate worker
  process** (`arq` worker or `celery worker` command) run alongside — not inside — the
  FastAPI app; document this as a new deployment unit rather than trying to run it in-process
  with uvicorn. A `reload_cron_bots()` startup reconciliation routine ports directly as an
  idempotent full-rescan-and-reregister function, run once at worker startup.
- **Priority:** Medium — valuable but not foundational; sequence after the core bot
  execution/dispatch service exists, since cron is just one more trigger path into it. Lower
  urgency than CDS Hooks if the near-term goal is clinical-workflow integration rather than
  batch housekeeping.

---

### Async Batch/Bundle Job Processing

- **What it does:** Decouples large FHIR `Bundle` (batch/transaction) submissions from the
  synchronous HTTP request — instead of holding a connection open while potentially hundreds
  of bundled operations execute, the server returns immediately with an `AsyncJob` handle the
  client polls, while the actual work happens in a background worker. This matters for
  clinical data platforms doing bulk imports/migrations where a single HTTP request timeout
  would make large-batch operations impossible.
- **Source files:** `src/workers/batch.ts` (`initBatchWorker`, `queueBatchProcessing`,
  `execBatchJob`, `getBatchQueue`, `BatchJobData`).
- **How it works:**
  - Also BullMQ-based, but a plain `Queue`/`Worker` pair (not a scheduler — one-shot jobs,
    `attempts: 1`, `concurrency: 1` per worker instance) rather than cron's repeatable jobs.
  - `queueBatchProcessing(bundle, asyncJob)` captures the *current* authenticated request
    context (`getAuthenticatedContext()` — login, project, membership, requestId, traceId)
    into `BatchJobData` and enqueues it — this is how the background worker later
    reconstructs "who was making this request" (`runInAuthenticatedContext`) even though it's
    now running outside the original HTTP request's lifecycle.
  - `execBatchJob` reconstructs a repo scoped to the original submitting user
    (`getRepoForLogin`), builds a synthetic `FhirRequest` wrapping the bundle, and replays it
    through the same `FhirRouter.handleRequest()` used for a live inline batch request — i.e.
    async batch and sync batch share the exact same execution engine; only the invocation
    path differs. On success, the resulting Bundle is uploaded as a Binary
    (`uploadBinaryData`) for later retrieval (bulk results aren't inlined into job status —
    the client fetches the Binary), and the `AsyncJob` is marked complete
    (`AsyncJobExecutor.completeJob`) with a `Parameters` resource pointing at the results
    Binary. On any outcome-level or thrown error, the job is marked failed
    (`AsyncJobExecutor.failJob`) — errors are deliberately swallowed after that point so
    BullMQ doesn't retry and risk executing part of the batch twice (each Bundle entry may
    itself be a non-idempotent write).
  - The `worker.on('failed', ...)` handler is a safety net for job-level failures BullMQ
    itself detects (e.g., unhandled exception escaping `execBatchJob` entirely) — it still
    marks the AsyncJob failed even if `execBatchJob`'s own try/catch didn't run.
- **Belongs in:** This is genuinely ambiguous and depends on where "the FHIR router that
  processes bundle entries" ends up living in the fhir-gql/fhir-server split. Since fhir-gql
  is described as owning orchestration and fhir-server owns persistence, the async job
  *bookkeeping* (AsyncJob status, queueing, polling contract) is a `fhir-gql (middleware)`
  concern, but each *entry* inside the bundle still has to be executed against fhir-server's
  write API — so this is a middleware-orchestrated queue whose worker calls back into
  fhir-server per entry, not a resource this document assigns wholesale to one side.
- **Port notes for fhir-gql (FastAPI/Python):** This isn't bot-specific — it's a generic
  "run this expensive multi-step operation asynchronously" pattern, but it's the same
  infrastructure (`arq`/Celery + Redis) that cron and bot-triggering need, so it's worth
  building once and reusing for both. An `AsyncJobService` would: create an `AsyncJob`-like
  status record, enqueue a task carrying the actor's JWT claims (`AuthUser.sub`/`org_id`,
  mirroring `authState` capture) plus the bundle payload, and a worker task that replays each
  bundle entry through the existing `PatientClient`/future `FhirClient` methods (or a generic
  FHIR-transaction endpoint if fhir-server exposes one), uploading results and flipping job
  status to complete/failed exactly once. Given fhir-gql currently only implements Patient,
  this is lower priority than getting Bot execution and CDS Hooks working, but the queue
  infrastructure decision (arq vs Celery) should be made once and shared across cron, async
  batch, and any future subscription-driven bot triggering.
- **Priority:** Low for fhir-gql today — there's no bulk/batch Bundle endpoint yet and only
  one resource type implemented, so there's nothing to make async. Revisit once multi-resource
  transactional writes or bulk import/export exist.

---

## Summary Table

| Feature | Priority | Belongs in |
|---|---|---|
| Bot Resource & Execution Dispatch (`executeBot`, contract) | High | fhir-gql (middleware) |
| VM Context Bots (in-process `vm` sandbox) | Low | separate execution service (dev-only) |
| AWS Lambda Bot Runtime (deploy + execute + streaming) | High | separate execution service |
| Fission/Kubernetes Bot Runtime | Low/Medium | separate execution service |
| CDS Hooks (discovery + invocation) | Medium | fhir-gql (middleware) |
| Cron-Scheduled Bot Automation | Medium | fhir-gql (middleware), separate worker process |
| Async Batch/Bundle Job Processing | Low | fhir-gql (middleware) orchestrating fhir-server writes |

## Recommended Next Steps

The dependency order matters more than raw priority: nothing else in this domain works
without a Bot execution dispatch layer and a stable execution contract, so that should land
first, modeled directly on Medplum's `BotExecutionRequest`/`Context`/`Result` split and wired
into fhir-gql the same way `PatientService` wraps `PatientClient` today. For the sandbox
itself, skip in-process execution entirely (Python offers nothing as workable as even
Medplum's admittedly-unsafe `vm` module) and go straight to AWS Lambda via `boto3`, or — if
avoiding a hard AWS dependency matters — one-off Docker containers per invocation, since that
gets real OS-level isolation without standing up a Kubernetes/Fission-equivalent control
plane the team doesn't otherwise need. Once execution exists, CDS Hooks is nearly free to add
(it is, in Medplum, a thin router with no logic of its own) and delivers a standards-based
integration point immediately, making it the highest-leverage next feature after the
execution service itself. Cron scheduling and async batch processing both need a Redis-backed
job queue (`arq` is the natural fit given fhir-gql's existing async FastAPI style and already-
provisioned Redis instance) — build that queue infrastructure once and treat cron and future
subscription-driven bot triggering as two consumers of the same worker rather than separate
systems. Async batch/bundle processing itself can wait: fhir-gql only implements Patient
today and has no multi-entry transaction endpoint, so there is nothing yet that needs to run
asynchronously.
