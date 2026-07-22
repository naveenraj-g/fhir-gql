# 07 — Integrations & Media: Binary Storage, DICOM, HL7v2, Device Agent, MCP, OCR

Scope: Medplum's binary/content storage abstraction (filesystem, S3, Azure Blob, GCS), presigned URL
scheme, the FHIR `Binary` REST endpoint, a DICOMweb-shaped stub, HL7v2 message parsing, the Medplum
"Agent" (an on-prem device/edge connector talking to the server over WebSocket), the Model Context
Protocol (MCP) server, and AWS Textract/Comprehend Medical document OCR.

> **Architecture correction (post-analysis):** this stack already has a fourth service — **FileNest**
> — dedicated to exactly the binary/content-storage problem Medplum's `storage/` + `cloud/{aws,azure,
> gcp}/storage.ts` abstraction solves. The frontend uploads a file directly to FileNest; FileNest
> processes it and stores it in an object store (S3 or similar) and hands the frontend back file
> details (URL, content type, size, hash); the frontend then sends *that metadata* — not raw bytes —
> to fhir-gql, which persists it as an Attachment on a sub-resource (e.g. `Patient.photo`) or as a
> `DocumentReference` once that resource is ported. **This means every "Belongs in: fhir-server /
> storage backend" verdict below for binary storage, presigned URLs, and cloud storage backends is
> superseded** — none of that needs to be built in fhir-server either, since FileNest already exists
> and owns it. fhir-gql's actual job re: attachments was already correctly scoped even before this
> correction: accept attachment *metadata* and write it into the appropriate FHIR field, never handle
> raw bytes or storage/presigned-URL generation itself. Concretely, this is **already fully working
> today** for photos — `PhotoCreateSchema`/`PhotoPatchSchema` (`app/schemas/patient/input.py`) already
> have `url`, `content_type`, `size`, `hash` fields, exactly the shape FileNest would hand back, so
> `POST /patients/{id}/photos` already supports "upload to FileNest, then register the URL here" with
> zero code changes. The only real follow-up is making sure `DocumentReference` (Group 3 in
> `10-resource-rollout-plan.md`) is built to accept the same metadata shape for its `content.attachment`
> field when that resource gets ported.

Medplum source analyzed (server package, `packages/server/src/…`):
`storage/{base,filesystem,loader,presign,routes,types,utils}.ts`, `dicom/routes.ts`, `hl7/parser.ts`
(plus the underlying `packages/core/src/hl7.ts` for message-structure detail), `agent/utils.ts`,
`ws/agent.ts`, `mcp/{routes,server}.ts`, `fhir/binary.ts`, `cloud/aws/storage.ts`,
`cloud/azure/storage.ts`, `cloud/gcp/storage.ts`, `cloud/aws/textract.ts`.

fhir-gql today (`D:\code\work\projects\fhir-gql\app`) has no `storage`, `binary`, `dicom`, `hl7`,
`agent`, or `mcp` module of any kind — this entire domain is greenfield. It has `auth`, `rbac`,
`rate_limit`, `gql` (Strawberry), `routers` (FastAPI/REST), and a `fhir_client` that talks to a
downstream fhir-server. Only `Patient` is modeled end-to-end.

---

### Pluggable Binary Storage Abstraction (`BinaryStorage` interface)
- **What it does:** Defines a single interface for reading, writing, and copying binary blobs
  (the content behind a FHIR `Binary` resource — PDFs, images, attachments, DICOM files, exports)
  regardless of which physical backend holds the bytes.
- **Source files:**
  - `src/storage/types.ts` — `BinaryStorage` interface (`writeBinary`, `writeFile`, `readBinary`,
    `copyBinary`, `copyFile`, `getPresignedUrl`); `BinarySource = Readable | string` type.
  - `src/storage/base.ts` — `BaseBinaryStorage` abstract class implementing the FHIR-aware wrapper
    methods (`readBinary`, `writeBinary`, `copyBinary`, `getKey`) on top of backend-specific
    `abstract` primitives (`writeFile`, `readFile`, `copyFile`, `getPresignedUrl`); `getKey(binary)`
    computes the canonical storage key `binary/<id>/<versionId>`.
  - `src/storage/loader.ts` — `initBinaryStorage(type?)` factory that instantiates the correct
    backend from a config string prefix (`s3:`, `azure:`, `file:`, `gs:`); `getBinaryStorage()`
    singleton accessor; `getPresignedUrl(binary, opts)` top-level helper.
- **How it works:** Every concrete backend (`FileSystemStorage`, `S3Storage`, `AzureBlobStorage`,
  `GoogleCloudStorage`) extends `BaseBinaryStorage` and only implements 4 primitives; all FHIR
  Binary-versioning semantics (key layout, filename/content-type validation) live once in the base
  class. Backend selection is a single config string (e.g. `s3:my-bucket`, `file:/data/binaries`)
  parsed by prefix in `initBinaryStorage`, so swapping storage providers is a deploy-time
  configuration change, not a code change.
- **Belongs in:** `fhir-server (data layer/storage backend)` — this is squarely persistence-layer
  responsibility. In fhir-gql's architecture the downstream fhir-server is the one that would own
  actual bytes.
- **Port notes for fhir-gql:** Not applicable to port directly as code, but the **interface pattern**
  is worth adopting conceptually if/when fhir-gql needs to broker uploads: define a small Python
  `Protocol`/ABC (`BinaryStorage`) so the gql layer can remain backend-agnostic if it ever needs to
  generate presigned URLs itself instead of just forwarding to fhir-server.
- **Priority:** Low for fhir-gql directly (fhir-server's concern) — but High to flag for the
  fhir-server team building this out, since it's the foundational abstraction everything else here
  depends on.

### Filesystem Binary Storage Backend
- **What it does:** Local-disk implementation of `BinaryStorage` for dev/self-hosted deployments —
  stores each Binary version as a file under `<baseDir>/<binary.id>/<versionId>`.
- **Source files:** `src/storage/filesystem.ts` — `FileSystemStorage` class (`writeFile`, `readFile`,
  `copyFile`, `getPresignedUrl` which delegates to `generatePresignedUrl`), plus a
  `readFileByUrlForTests` test helper.
- **How it works:** Uses Node `fs`/`fs/promises` streams (`createWriteStream`/`createReadStream`)
  piped via `node:stream.pipeline`; creates parent directories recursively (`mkdir -p` semantics)
  before writing; presigned URLs are generated locally (see the "Local Presigned URL / Storage Proxy
  Endpoint" feature below) rather than backend-native, since there's no cloud IAM to delegate to.
- **Belongs in:** `fhir-server (data layer/storage backend)`.
- **Port notes for fhir-gql:** N/A for fhir-gql itself. If fhir-server is Python, this maps trivially
  to `aiofiles` (async streamed read/write) or a synchronous `shutil.copyfileobj` for a dev-only
  backend; `pathlib` for directory creation (`Path.mkdir(parents=True, exist_ok=True)`).
- **Priority:** Low for fhir-gql (not our layer at all).

### AWS S3 Binary Storage Backend
- **What it does:** Production-grade cloud object storage backend, including multipart streaming
  upload, optional server-side encryption with customer-provided keys (SSE-C), and two flavors of
  presigned URL (native S3 presign, or CloudFront signed URLs when a CDN + custom signing key is
  configured).
- **Source files:** `src/cloud/aws/storage.ts` — `S3Storage extends BaseBinaryStorage`; uses
  `@aws-sdk/client-s3` (`GetObjectCommand`, `PutObjectCommand`, `CopyObjectCommand`),
  `@aws-sdk/lib-storage` (`Upload`, for multipart/streamed uploads instead of the size-limited
  single-shot `PutObjectCommand`), `@aws-sdk/s3-request-presigner` (`getSignedUrl` for native S3
  presigning), `@aws-sdk/cloudfront-signer` (`getSignedUrl` for CloudFront-signed URLs).
- **How it works:**
  - `writeFile` uses `Upload` (`@aws-sdk/lib-storage`) with `queueSize: 3` for concurrent multipart
    parts, sets `CacheControl: max-age=3600, s-maxage=86400` (1hr browser cache matching presigned
    URL expiry, 1 day at CDN edge), and content type; SSE-C params spread in if `config.sseCustomerKey`
    is set (customer-supplied AES-256 key, MD5 digest computed via `node:crypto`).
  - `readFile` returns the S3 `Body` stream directly (`GetObjectCommand`).
  - `copyFile` uses server-side `CopyObjectCommand` (no data egress through the app) and forwards
    SSE-C headers (both destination and `CopySourceSSE*` for the source) when encryption is active.
  - `getPresignedUrl`: if no CloudFront signing key configured (or it's an upload request), falls
    back to native S3 presigned URL (`s3GetSignedUrl`, 3600s expiry) pointing straight at S3/the
    bucket. If a CloudFront key pair is configured (production setup — CDN in front of S3), it signs
    a CloudFront URL instead (`@aws-sdk/cloudfront-signer`, RSA key pair, `dateLessThan` expiry) so
    downloads go through the CDN edge cache rather than direct-to-S3, while uploads still bypass the
    CDN (writes go straight to S3 with a PUT presigned URL since CloudFront can't proxy uploads with
    a signed cookie/URL scheme the same way).
- **Belongs in:** `fhir-server (data layer/storage backend)` — but the **presigned-URL orchestration
  decision** (whether to mint the URL client-side-facing) is exactly the kind of thing fhir-gql could
  end up brokering if it fronts multiple storage backends per deployment.
- **Port notes for fhir-gql:** If fhir-gql ever needs to *generate* presigned URLs itself (rather than
  just relaying a URL the downstream fhir-server hands back), use `boto3` (`s3_client.generate_presigned_url`
  for GET/PUT, `S3Transfer`/`boto3.s3.transfer.TransferManager` for multipart uploads). CloudFront
  signed URLs map to `botocore.signers.CloudFrontSigner` with an RSA private key via `cryptography`.
  More realistically, per the stated architecture, fhir-server owns this and fhir-gql only needs to
  pass the presigned URL through in its GraphQL/REST response and enforce auth/rate-limit before the
  client is allowed to request one.
- **Priority:** Low for fhir-gql to *implement* (fhir-server's job); Medium to *understand* — the
  presigned-URL request/response shape needs to be mirrored in fhir-gql's GraphQL schema/REST DTOs so
  clients get a consistent contract regardless of which cloud backend fhir-server uses underneath.

### Azure Blob Storage Backend
- **What it does:** Azure equivalent of the S3 backend — blob upload/download/copy plus SAS
  (Shared Access Signature) URL generation using Azure AD managed identity (no static storage account
  keys).
- **Source files:** `src/cloud/azure/storage.ts` — `AzureBlobStorage extends BaseBinaryStorage`; uses
  `@azure/identity` (`DefaultAzureCredential`) and `@azure/storage-blob`
  (`BlobServiceClient`, `BlobSASPermissions`).
- **How it works:** `writeFile` branches on string vs. stream input (`blockBlobClient.upload` for
  strings, `uploadStream` for `Readable`s), setting `blobContentType`/`blobCacheControl`.
  `copyFile` uses `beginCopyFromURL` (async server-side copy, not awaited to completion here — fire
  and poll pattern typical of Azure blob copy). `getPresignedUrl` requests a **user delegation key**
  (`client.getUserDelegationKey`, 1hr validity) — this is the key mechanism: instead of a shared
  storage-account key, Azure AD issues a short-lived delegation key tied to the server's managed
  identity, and a SAS URL is signed with *that* (`generateUserDelegationSasUrl`), with
  read/write/create permissions set via `BlobSASPermissions` depending on `opts.upload`.
- **Belongs in:** `fhir-server (data layer/storage backend)`.
- **Port notes for fhir-gql:** `azure-storage-blob` (Python SDK) + `azure-identity`
  (`DefaultAzureCredential`) mirror this almost 1:1 — `BlobServiceClient.get_user_delegation_key()` and
  `generate_blob_sas(..., user_delegation_key=...)`. Only relevant if fhir-gql itself needs to mint
  Azure SAS URLs (unlikely given the stated architecture — this belongs downstream).
- **Priority:** Low for fhir-gql — same reasoning as S3.

### Google Cloud Storage Backend
- **What it does:** GCS equivalent — object upload/download/copy plus V4 signed URLs.
- **Source files:** `src/cloud/gcp/storage.ts` — `GoogleCloudStorage extends BaseBinaryStorage`; uses
  `@google-cloud/storage` (`Storage`, `GetSignedUrlConfig`).
- **How it works:** `writeFile` branches string (`file.save`) vs stream (`file.createWriteStream`
  piped, wrapped in a Promise); `resumable: true` is set for robustness on large/streamed uploads.
  `getPresignedUrl` uses V4 signing (`version: 'v4'`) with `virtualHostedStyle: true` (URL shape
  `https://<bucket>.storage.googleapis.com/...` rather than path-style) and a 1-hour expiry
  (`Date.now() + 3600*1000`), action `'read'` or `'write'` based on `opts.upload`.
- **Belongs in:** `fhir-server (data layer/storage backend)`.
- **Port notes for fhir-gql:** `google-cloud-storage` (Python SDK) — `blob.generate_signed_url(version="v4", ...)`
  maps directly. Same caveat as above: only relevant if fhir-gql needs to mint URLs itself rather than
  relay them.
- **Priority:** Low for fhir-gql.

### Local Presigned URL / Storage Proxy Endpoint
- **What it does:** When there's no cloud storage backend with native presigning (e.g. filesystem
  storage, or any backend where the storage base URL is configured to be the same host as the FHIR
  API), Medplum implements its **own** signed-URL scheme and a matching HTTP endpoint that validates
  the signature and streams the file — effectively a home-grown presigned-URL system built on RSA
  signatures.
- **Source files:**
  - `src/storage/presign.ts` — `generatePresignedUrl(binary, opts)`: builds the URL, sets `Expires`
    (Unix timestamp, +1hr) and optional `Project` query params, then signs `"<METHOD> <url>"` with
    `node:crypto.createSign('sha256')` using a configured RSA private key (`config.signingKey`
    + `config.signingKeyPassphrase`), appended as a `Signature` query param.
  - `src/storage/routes.ts` — `storageRouter`: `GET /:id/:versionId?` and `PUT /:id/:versionId?`
    endpoints that call `verifyAndLoadBinary()`, which re-derives the public key from the private key
    (`createPublicKey(createPrivateKey(...))`, cached), strips the `Signature` param, re-verifies with
    `createVerify('sha256')` against `"<METHOD> <url-without-signature>"`, checks `Expires` against
    current time (410 Gone if expired), and — notably — falls back to verifying **without** the HTTP
    method prefixed (a "legacy format" compatibility shim) for GET requests only. On success it loads
    the `Binary` resource via a **system-level repo** (bypassing normal per-request auth — the
    signature itself is the auth) either project-scoped (`Project` query param → `getProjectSystemRepo`)
    or global (`getGlobalSystemRepo`), then streams (`readBinary`) or accepts (`writeBinary`) the file.
- **How it works (protocol):** A presigned URL looks like
  `https://storage.example.com/<binaryId>/<versionId>?Expires=<unixTs>&Project=<projectId>&Signature=<b64>`.
  The signature covers the HTTP method + full URL (minus the signature param itself), so a GET-signed
  URL cannot be replayed as a PUT and vice versa. This is a **capability URL** pattern: possession of
  the URL *is* the authorization, valid for exactly 1 hour, with no session/cookie/bearer-token
  needed — which is what makes it safe to hand to an `<img src>` tag or a browser file download.
- **Belongs in:** `both`, but split: the **signing/verification mechanism and the storage-proxy route**
  belong in fhir-server (it owns the bytes and the private key). But the **concept** — issuing a
  short-lived, capability-style URL so a client can upload/download directly without going through
  authenticated API calls per byte — is exactly the kind of orchestration fhir-gql's middleware layer
  is designed for. If fhir-gql fronts uploads (e.g. clients call fhir-gql to get an upload URL, then
  PUT bytes directly to fhir-server or cloud storage), fhir-gql should own **requesting/relaying** the
  presigned URL and enforcing RBAC before minting one, even if it doesn't do the RSA signing itself.
- **Port notes for fhir-gql:** If fhir-gql needs its own capability-URL layer (e.g. fronting a
  fhir-server that doesn't support presigning, or adding an extra authorization hop), the
  `cryptography` library's `rsa` module (`sign`/`verify` with PKCS1v15 + SHA256) replicates
  `node:crypto.createSign/createVerify` exactly. More idiomatically for FastAPI: use `itsdangerous`
  `URLSafeTimedSerializer` or a JWT (fhir-gql already owns JWT auth) with short expiry as the
  signed-URL token instead of reinventing RSA query-param signing — this fits fhir-gql's existing auth
  stack far better than porting Medplum's bespoke scheme.
- **Priority:** Medium — worth designing for even before binary/media work starts, because the
  presigned-URL *contract* (what shape of URL/response the GraphQL and REST layers return) affects
  API design now. Low urgency to implement until Binary/Media resources are prioritized.

### File Metadata / Upload Safety Checks
- **What it does:** Blocks upload of known-dangerous file extensions and MIME/content types
  (executables, scripts, installers) before they're written to storage — a defense-in-depth measure
  against hosting malware via the FHIR `Binary` endpoint (e.g. someone uploading a `.exe` renamed with
  a benign content-type, or a `.php`/`.sh` that could be served back and executed if storage is ever
  misconfigured as a web root).
- **Source files:** `src/storage/utils.ts` — `checkFileMetadata(filename, contentType)`, called from
  `BaseBinaryStorage.writeBinary` and `FileSystemStorage.writeBinary`; `BLOCKED_FILE_EXTENSIONS`
  (~45 extensions, sourced from Gmail's blocked-attachment list — `.exe`, `.bat`, `.msi`, `.ps1`,
  `.vbs`, `.dmg`, `.apk`, etc.) and `BLOCKED_CONTENT_TYPES` (~5 MIME types: Java archive, MS-DOS
  executable, shell script, Apple installer, PE executable).
- **How it works:** Simple case-insensitive suffix match on filename against the blocklist, and exact
  match on content-type; throws `OperationOutcomeError(badRequest(...))` on match, which propagates as
  a FHIR `OperationOutcome` 400 response.
- **Belongs in:** `both` — the actual blocking check happens wherever bytes are accepted, which could
  be fhir-server (final gatekeeper) but is *also* a cheap, valuable early-rejection check fhir-gql
  could do at the API boundary (reject obviously-bad uploads before even proxying the request
  downstream, saving bandwidth and giving faster client feedback).
- **Port notes for fhir-gql:** Trivial to port — a small `set` of blocked extensions/content-types and
  a `check_file_metadata(filename, content_type)` function raising an `HTTPException(400)`. This is
  pure Python, no special library needed. If fhir-gql adds any upload-proxying endpoint, add this
  check as FastAPI request validation (dependency) before streaming to fhir-server.
- **Priority:** Medium — cheap, high-value, and independent of the rest of the storage stack; worth
  doing as soon as *any* binary upload path exists in fhir-gql, even a pass-through one.

### FHIR `Binary` Resource REST Endpoint (create/update/read)
- **What it does:** The actual `/fhir/R4/Binary` REST handlers — upload content as a new/updated
  `Binary` resource (accepting either raw bytes with a `Content-Type` header, or a full FHIR-JSON
  `Binary` resource body per spec), and read back the `Binary` resource's metadata (its content is
  fetched separately via the presigned `url`).
- **Source files:** `src/fhir/binary.ts` — `binaryRouter` (`POST /`, `PUT /:id`, `GET /:id`),
  `handleBinaryWriteRequest`, `uploadBinaryData` (exported — the reusable "create/update a Binary and
  write its bytes" helper used elsewhere, e.g. by the Textract flow), `getContentStream` (handles
  `Content-Encoding: gzip/deflate` by piping through `zlib.createInflate/createGunzip`),
  `readStreamToString`.
- **How it works:** Deliberately **bypasses Express's `body-parser`** for this route (comment
  explicitly explains why: body-parser buffers to a temp file on disk, unacceptable for
  multi-gigabyte uploads) — instead it streams `req` directly to storage. It handles the FHIR-spec
  special case where `Content-Type: application/fhir+json` but the *body* is actually a `Binary`
  resource JSON (buffers just enough to string, JSON-parses, and if it's shaped like a `Binary`
  resource, treats it as a normal resource create/update instead of raw content). Otherwise it treats
  the whole request body as opaque bytes: creates/updates the `Binary` resource row (id, contentType,
  optional `securityContext` from an `X-Security-Context` header — used for consent-based ABAC on the
  binary), streams the body straight to `getBinaryStorage().writeBinary(...)`, then sets
  `binary.url = await getPresignedUrl(binary)` on the response so the client immediately gets a
  download link back.
- **Belongs in:** `fhir-server (data layer/storage backend)` — this *is* the Binary resource
  persistence endpoint, tightly coupled to the storage abstraction above. However, fhir-gql's REST/
  GraphQL routers would be the ones **exposing** `Binary` to fhir-gql's own clients (auth'd,
  rate-limited) and proxying to this downstream endpoint — so fhir-gql needs a thin pass-through
  layer even if it does none of the storage work itself.
- **Port notes for fhir-gql:** Not to be implemented in fhir-gql per the stated architecture (no
  persistence here). If/when fhir-gql adds a `Binary` GraphQL type or REST pass-through, model it as:
  a streaming proxy endpoint (`StreamingResponse` in FastAPI) that forwards `Content-Type` and
  raw body to fhir-server without buffering (avoid `await request.body()` — use
  `request.stream()`), applying the extension/content-type checks above at the fhir-gql boundary
  first, then relaying fhir-server's JSON response (including the presigned `url`) back to the client
  unmodified.
- **Priority:** Medium — becomes High the moment any resource beyond Patient needs attachments
  (DocumentReference, Media, ImagingStudy, Patient photo, etc.), since `Binary` is a dependency of
  almost every rich-content FHIR resource.

### DICOMweb (WADO-RS) Endpoint — Stub Only
- **What it does:** Route scaffolding for the DICOMweb standard (WADO-RS/QIDO-RS-shaped URLs) for
  querying/retrieving medical imaging studies, series, and instances. **Every handler in Medplum's
  current implementation is a stub that just returns HTTP 200 with no body** — there is no real DICOM
  parsing, storage, or rendering logic in this file at all.
- **Source files:** `src/dicom/routes.ts` — `dicomRouter`, all routes gated by
  `authenticateRequest` middleware only.
- **How it works (protocol, as scaffolded):** Implements the DICOMweb URL shape
  (`GET/POST /studies`, `GET/POST /studies/:study`, `GET /studies/:study/series`,
  `GET /studies/:study/series/:series`, `.../instances`, `.../instances/:instance`, plus `/rendered`
  variants for browser-viewable images, `/metadata` variants for DICOM JSON metadata, `/frames/:frame`
  for individual multi-frame image frames, and a generic `/:bulkdataUriReference` for retrieving bulk
  binary data referenced from metadata). This mirrors the real DICOMweb spec
  (https://www.dicomstandard.org/dicomweb) — QIDO-RS for querying studies/series/instances, WADO-RS
  for retrieving them, WADO-URI-style bulk data — but none of it is wired to actual DICOM file
  parsing, a PACS, or `Binary`/`ImagingStudy` FHIR resources yet in this codebase.
- **Belongs in:** `both`, conceptually split — DICOMweb query/retrieve against real pixel data and
  study metadata is fundamentally a `fhir-server`/storage-backend concern (it needs the actual DICOM
  files and a DICOM metadata index). But request routing, auth, and potentially caching/rate-limiting
  of these endpoints is a natural fhir-gql concern if fhir-gql is the public-facing gateway.
- **Port notes for fhir-gql:** Because Medplum's own implementation is unfinished, there's nothing
  functional to port. If fhir-gql/fhir-server later add real DICOM support, `pydicom` is the standard
  Python library for parsing DICOM files (dataset/tag access), and `pynetdicom` for DICOM network
  protocol (C-STORE/C-FIND) if on-prem modality integration is needed; for DICOMweb specifically,
  consider `dicomweb-client` (client-side) as a reference for the wire format, or a framework like
  Orthanc (a full open-source DICOM server with a DICOMweb plugin) as the actual downstream imaging
  store rather than building WADO-RS from scratch — i.e. treat imaging storage as a specialized
  downstream service, not something to hand-roll in fhir-gql or even fhir-server.
- **Priority:** Low — Medplum itself hasn't built this out beyond routing stubs, and fhir-gql has no
  imaging use case yet. Flag as a placeholder for future roadmap only; not worth building ahead of
  actual demand, and even Medplum recommends pairing with a dedicated PACS/DICOM server rather than
  reimplementing DICOMweb server-side logic in the FHIR server itself.

### HL7v2 Message Parsing (Body Parser Middleware)
- **What it does:** Express middleware that recognizes incoming requests with an HL7v2 content type
  and parses the raw pipe-delimited text body into a structured, navigable message object before the
  route handler sees it — the ingestion point for legacy lab feeds, ADT (admit/discharge/transfer)
  messages, and other MLLP/HTTP-bridged HL7v2 traffic.
- **Source files:**
  - `src/hl7/parser.ts` — `hl7BodyParser(options: { type: string[] })` middleware factory; calls
    `Hl7Message.parse(req.body)` and replaces `req.body` with the parsed object.
  - `packages/core/src/hl7.ts` (read for context, not in server package) — the actual parser:
    `Hl7Context`, `Hl7Message`, `Hl7Segment`, `Hl7Field`, plus `parseHl7DateTime`/`formatHl7DateTime`.
- **How it works (HL7v2 message structure):** An HL7v2 message is segments (lines, separated by `\r`
  by convention) → fields (separated by `|`) → components (separated by `^`) → sub-components
  (separated by `&`), with `~` as a repetition separator within a field. The **first segment is
  always `MSH`** (Message Header), and critically, `MSH-1` through `MSH-4` *are themselves* the
  separator characters: `MSH|^~\&|...` — field sep is the literal `|` right after `MSH`, and the next
  4 characters (`^~\&`) declare the component/repetition/escape/subcomponent separators for the rest
  of the message. `Hl7Message.parse(text)` reads these separator characters directly out of positions
  3-7 of the text (`text.charAt(3..7)`) to build a per-message `Hl7Context`, then splits on
  `\r`/`\n` for segments. Parsing is **lazy**: segments/fields start as raw strings and are only
  parsed into `Hl7Segment`/`Hl7Field` objects when actually accessed (`getSegment`, `getField`,
  `.segments`, `.fields` getters) — an optimization for high-throughput feeds where most fields of a
  message are never read. Access is by 1-based field/component index matching HL7 naming conventions
  (`PID.5.1` == `segment.getComponent(5, 1)` on the `PID` segment), or convenience shortcuts
  (`getSegment('PID')`, `getAllSegments('OBX')` for repeating segments like lab result lines).
  `Hl7Message` also supports **building an ACK** (`buildAck({ackCode, errSegment})`) — HL7v2's
  synchronous acknowledgment pattern (`MSA-1` codes: `AA` accept, `AE` application error, `AR` reject,
  and commit-level `CA`/`CE`/`CR`), auto-populating the ACK's `MSH` by swapping
  sending/receiving app+facility from the original message and mirroring the message-type structure
  version-appropriately (1, 2, or 3-component `MSH-9` depending on HL7 version). Date/time fields use
  HL7's own compact format (`YYYYMMDDHHMMSS.SSSS+ZZZZ`), parsed/formatted via
  `parseHl7DateTime`/`formatHl7DateTime`.
- **Belongs in:** `both` — the wire-format parser itself is generic/reusable and could live in either
  layer, but *where messages actually enter the system* (an MLLP listener or HTTP bridge accepting
  raw HL7v2, invoking a bot/transform, and persisting resulting FHIR resources) is fundamentally a
  fhir-server/downstream-integration concern since it results in FHIR resource writes. fhir-gql's role
  would be limited to relaying/authenticating HL7-over-HTTP webhook-style ingestion if that transport
  is ever used, not owning the transform-to-FHIR logic.
- **Port notes for fhir-gql:** `python-hl7` is the standard library for HL7v2 parsing in Python
  (`hl7.parse(message_text)` gives similar segment/field/component/repetition access, and it
  understands the same `MSH-1`/`MSH-2` separator-declaration convention). For an ACK-building helper,
  `python-hl7` doesn't include one out of the box — that logic (mirroring MSH fields, MSA segment
  construction) would need to be hand-written similarly to Medplum's `buildAck`, which is not much
  code (~30 lines). Given fhir-gql doesn't currently ingest HL7v2 at all and has no bot/transform
  engine, this is squarely a "if we ever add a legacy lab/ADT feed" feature, not urgent.
- **Priority:** Low — no current fhir-gql use case; HL7v2 ingestion implies an entire integration
  engine (MLLP listener, ADT/ORU trigger-event routing, ACK round-trip) that doesn't exist in this
  project at any layer yet, and only Patient is modeled so far (no Encounter/Observation to receive
  ADT/ORU data into).

### Medplum "Agent" — On-Prem Device/Edge Connector (WebSocket Protocol)
- **What it does:** A downloadable, installable local service (the "Medplum Agent," a separate
  binary/executable not in this file set) that runs on-premises next to legacy medical devices,
  DICOM modalities, or HL7 feed sources with no direct internet-facing API, and relays their data to
  the Medplum server over an outbound WebSocket connection — solving the "hospital network,
  no inbound firewall holes" integration problem. The server-side half of this protocol is what's
  analyzed here.
- **Source files:**
  - `src/agent/utils.ts` — `AgentConnectionState` enum (`unknown`/`connected`/`disconnected`),
    `AgentInfo` type (`status`, `version`, `lastUpdated`) — the structure cached in Redis representing
    an agent's live status, consumed by the `Agent $status` FHIR operation (referenced but not in this
    file set: `fhir/operations/agentstatus.ts`).
  - `src/ws/agent.ts` — `handleAgentConnection(socket, request)`, the WebSocket connection handler;
    `stopAgentHeartbeat()`.
- **How it works (protocol):**
  - **Transport:** A raw `ws` WebSocket connection from the on-prem Agent to the server (this file is
    the server-side handler invoked once a socket is accepted). Every server process tracks its
    locally-connected sockets in an in-memory `Set<WebSocket>` and emits OpenTelemetry gauges
    (`medplum.agent.websocketCount`, messages sent/received per second) on a shared `heartbeat` event
    bus — but **multi-server fan-out is done through Redis pub/sub**, not the WebSocket set directly.
  - **Handshake (`agent:connect:request` → `agent:connect:response`):** The agent sends `{type:
    'agent:connect:request', accessToken, agentId}`. The server exchanges the access token for a login
    (`getLoginForAccessToken`), loads the `Agent` FHIR resource by id, and — critically — subscribes
    this WebSocket connection to a **Redis pub/sub channel named after the Agent's reference string**
    (`redisSubscriber.subscribe(getReferenceString(agent))`). Any message published to that Redis
    channel (from *any* server instance, not just the one holding the socket) gets forwarded down this
    specific WebSocket (`socket.send(message)`). This is how the system supports N horizontally-scaled
    API server instances each with their own subset of live agent connections: work destined for a
    given agent is published to Redis, and whichever server instance actually holds that agent's live
    socket delivers it. The connect handler is careful to bind the Redis message listener *before*
    awaiting `subscribe()` completion, to avoid a race where a message published immediately after
    subscribing is dropped.
  - **Heartbeat:** Server periodically emits `agent:heartbeat:request`; agent replies
    `agent:heartbeat:response` with its version, which the server records into Redis (`AgentInfo`,
    24h TTL) as the liveness/version signal surfaced by the `Agent.$status` FHIR operation.
  - **Transmit (`agent:transmit:request` → `agent:transmit:response`):** This is the actual
    data-relay path — e.g. the agent received an HL7v2 message from a local device and wants the
    server to process it. The request carries `accessToken`, `channel` (a named channel on the
    `Agent` resource, e.g. mapping to a specific device/port), `body`, `contentType`, and an optional
    `callback`/`remote`. The server re-authenticates via the access token, looks up the target
    `channel` on the `Agent` resource, resolves the channel's `targetReference` to a `Bot` resource,
    parses the body (`JSON.parse` for JSON/FHIR-JSON, `Hl7Message.parse` for `HL7_V2` content type),
    and **executes the Bot** (`executeBot`) with that input — i.e. the Agent is essentially a remote
    trigger for server-side Bot (automation/transform) execution, with the transmitted payload as the
    Bot's input event. The Bot's return value/logs are packaged into an `agent:transmit:response` and
    sent back down the same WebSocket, tagged with the original `callback` id so the agent can
    correlate request/response (this is the RPC-style pattern that lets a synchronous device-side
    call, e.g. "process this HL7 message and tell me if the FHIR write succeeded," round-trip through
    an async WebSocket + Bot execution).
  - **Reverse-direction commands** (`agent:reloadconfig:response`, `agent:upgrade:response`,
    `agent:logs:response`, `agent:stats:response`, `agent:error`): the server can also push commands
    *to* the agent (reload its local config, self-upgrade, fetch logs/stats) — those response message
    types are handled here by publishing them back onto a `command.callback` Redis channel, implying a
    request/response pattern initiated server-side (likely via the FHIR `Agent.$reload-config` /
    `$push` / `$status` operations referenced in `fhir/operations/agent*.ts`, not in this file set)
    that awaits the matching Redis-published response.
  - **Disconnect handling:** carefully orders cleanup (remove from in-memory set, unsubscribe
    heartbeat listener, disconnect Redis subscriber) *before* the async `updateAgentStatus` call, so a
    failed Redis call during shutdown can't leak listeners/subscriptions.
- **Belongs in:** `fhir-server (data layer/storage backend)` / downstream integration layer — this is
  fundamentally about server-side Bot execution and FHIR resource access triggered by an external
  device, which requires the full FHIR repository and Bot execution engine that fhir-gql explicitly
  does not own. It's also a stateful, connection-pinned WebSocket protocol requiring Redis pub/sub for
  horizontal scaling — a fair amount of infrastructure that belongs with the system that owns
  persistence and automation, not the auth/orchestration gateway.
- **Port notes for fhir-gql:** Not a near-term fit for fhir-gql given there's no Bot/automation engine
  and no on-prem device integration requirement mentioned. If ever needed, FastAPI supports WebSocket
  endpoints natively (`@app.websocket(...)`), and `redis.asyncio` (`aioredis` is now merged into
  `redis-py`) provides equivalent pub/sub. The RPC-style callback correlation pattern
  (`command.callback` → Redis channel → matching response) is a reasonable pattern to reuse if
  fhir-gql ever needs bidirectional async messaging with an external component, but building the
  Agent's actual device-facing binary and protocol is out of scope for fhir-gql specifically — it
  would be a downstream/adjacent service.
- **Priority:** Low for fhir-gql — no current device-integration requirement, and this is one of the
  most infrastructure-heavy features in the file set (WebSocket + Redis pub/sub + Bot execution
  engine dependency). Worth revisiting only if a specific on-prem device/modality integration becomes
  a project requirement.

### Model Context Protocol (MCP) Server
- **What it does:** Exposes the FHIR server's data and API as tools an LLM/AI agent can call via the
  standardized Model Context Protocol — letting Claude, ChatGPT, or other MCP-aware AI clients search
  for and fetch FHIR resources, and make arbitrary authenticated FHIR REST calls, directly through
  conversational tool-use rather than requiring bespoke integration code per AI product.
- **Source files:**
  - `src/mcp/server.ts` — `getMcpServer()`: constructs an `McpServer` (from
    `@modelcontextprotocol/sdk/server/mcp.js`) named `'medplum'`, registers three tools: `search`,
    `fetch`, and `fhir-request`.
  - `src/mcp/routes.ts` — `mcpRouter`, exposing the server over two transports:
    `ALL /mcp/stream` (Streamable HTTP) and `GET/POST /mcp/sse` (Server-Sent Events, deprecated but
    still widely used by clients).
- **How it works (MCP tool/resource contract):**
  - **Tool schemas** are defined with `zod` and registered via `server.registerTool(name, {
    inputSchema }, handler)` — this is the MCP SDK's mechanism for advertising a typed tool contract
    to the connecting LLM client (tool name, input schema, and on invocation, a handler returning
    `{ content: [...] }` where each content item has a `type` (`'text'`), `text`, and optionally a
    `uri`/`id`).
  - **`search` / `fetch`:** Currently **stub/dummy implementations** — both just return a hardcoded
    `dummyDocument` regardless of input. The code comment explains *why they exist at all*: ChatGPT's
    MCP connector specifically requires a server to implement exactly these two tool names
    (`search`, `fetch`) as a baseline compatibility contract, or it refuses to connect — so these are
    present purely for interop, not because they're functional yet.
  - **`fhir-request`:** The actually-functional tool — takes `{method, path, body}`, resolves the
    caller's already-authenticated context (`getAuthenticatedContext()` — the MCP session is
    authenticated the same way as any other API request, via `authenticateRequest` middleware applied
    to `mcpRouter`), constructs a `MedplumClient` scoped to that access token, and re-issues the
    request against the FHIR REST API (`GET/POST/PUT/PATCH/DELETE` on `fhir/R4/<path>`) — essentially
    a generic FHIR REST proxy exposed as a single AI tool, letting the LLM perform arbitrary
    authorized FHIR operations (search, create, update, etc.) without a dedicated tool per resource
    type or operation. The code comments flag this as intentionally suboptimal (re-fetches over HTTP
    rather than calling the in-process `FhirRouter`) with a known follow-up to route in-process once
    coverage allows.
  - **Transport 1 — Streamable HTTP (`/mcp/stream`):** The modern MCP transport. A fresh
    `StreamableHTTPServerTransport` and `McpServer` connection is created **per request**
    (`sessionIdGenerator: undefined` — stateless), and torn down (`transport.close()`,
    `server.close()`) when the HTTP response closes. All MCP JSON-RPC traffic for that call flows over
    this single HTTP request/response cycle (with streaming support).
  - **Transport 2 — SSE (`/mcp/sse`, deprecated but supported for compatibility):** A **stateful,
    long-lived** pattern split across two endpoints: `GET /mcp/sse` opens an SSE stream
    (`SSEServerTransport`) and subscribes to a Redis pub/sub channel keyed by the transport's
    session id (`medplum:mcp:sse:<sessionId>`) — this is the same "any server instance can handle the
    client's POSTed message, relay via Redis to whichever instance holds the SSE stream" pattern seen
    in the Agent WebSocket handler, necessary because SSE GET and the client's subsequent POSTs may
    land on different server instances behind a load balancer. `POST /mcp/sse?sessionId=<uuid>`
    (validated via `express-validator`: `sessionId` must be a UUID, body must have a `jsonrpc` field)
    publishes the JSON-RPC message onto that Redis channel; the GET handler's Redis subscriber picks
    it up and feeds it into the transport via `transport.handlePostMessage` (using synthetic
    stub `req`/`res` objects since there's no real HTTP round-trip on this side of the relay). Also
    wires an application-level ping heartbeat (`server.server.ping()`) on the shared `heartbeat` bus
    to keep the SSE connection alive.
  - **Auth:** Both endpoints are behind `authenticateRequest` (the same OAuth/bearer-token middleware
    used by the rest of the FHIR API) — an MCP client must present a valid Medplum access token
    exactly as any REST API client would.
- **Belongs in:** `fhir-gql (middleware)` — **this is the single feature in this entire assignment
  that maps most directly onto fhir-gql's own architecture and mission.** fhir-gql already owns JWT
  auth, RBAC, rate limiting, and orchestration across REST and GraphQL transports for exactly one
  downstream data source; an MCP server is structurally the *same kind of thing* — another transport
  (alongside REST/GraphQL) exposing the same authorized, RBAC'd operations, this time to LLM tool-use
  clients instead of human-facing apps. It requires no persistence of its own (Medplum's own
  `fhir-request` tool works by re-issuing authenticated HTTP calls against the FHIR API — precisely
  what fhir-gql's `fhir_client` module already does against the downstream fhir-server). Building this
  in fhir-gql, reusing its existing auth/RBAC/rate-limit stack, is a very natural fit — arguably more
  natural than in Medplum, where it bolts onto an already-monolithic server.
- **Port notes for fhir-gql:** Use the **official Python MCP SDK**, `mcp` (PyPI: `mcp`, published by
  Anthropic/the MCP working group — `pip install mcp`), which provides `mcp.server.fastmcp.FastMCP`
  (a high-level, decorator-based server analogous to `McpServer` here) or the lower-level
  `mcp.server.Server` API. FastMCP supports both **stdio** transport (for local/CLI MCP clients) and
  **Streamable HTTP** transport (`mcp.server.fastmcp.FastMCP(...).streamable_http_app()`, an ASGI app
  that **mounts directly into FastAPI** via `app.mount('/mcp', mcp_server.streamable_http_app())`),
  which is by far the cleanest fit for fhir-gql given it's already FastAPI/ASGI — no need to hand-roll
  the transport plumbing Medplum does over Express. For tool schemas, FastMCP tools are plain Python
  functions decorated with `@mcp.tool()`, with input schemas auto-derived from Pydantic-style type
  hints (fhir-gql already uses Pydantic v2 for its schemas — `app/schemas/patient/`), which is a more
  ergonomic fit than porting the zod-schema pattern verbatim. Concretely:
  - Register a `search`/`fetch` stub pair only if targeting ChatGPT's connector compatibility
    requirement is a goal; otherwise skip — they're pure interop shims, not a real feature.
  - Implement a `fhir-request`-equivalent tool that reuses fhir-gql's existing `fhir_client` module
    (`app/fhir_client/client.py`) to proxy authorized calls to the downstream fhir-server — this
    directly reuses code that already exists rather than adding a new HTTP client.
  - Auth: reuse fhir-gql's existing JWT/RBAC dependency chain (`app/auth`, `app/rbac`) as a FastAPI
    dependency on the MCP mount/tool-call path, exactly as Medplum reuses `authenticateRequest`.
  - Multi-instance SSE fan-out via Redis (needed only if deploying the legacy SSE transport across
    multiple replicas) can reuse fhir-gql's existing Redis integration (`app/core/redis.py`) with
    `redis.asyncio` pub/sub, mirroring the `medplum:mcp:sse:<sessionId>` channel-per-session pattern —
    but Streamable HTTP (stateless, one request/response) sidesteps this complexity entirely for most
    deployments and should be preferred unless a specific client requires SSE.
  - Given fhir-gql exposes both REST and GraphQL already, consider whether MCP tools should call
    through the GraphQL layer (reusing Strawberry resolvers/authorization) or the REST layer/fhir_client
    directly — the GraphQL schema likely already encodes the permitted shape of Patient queries, which
    could be exposed as MCP tools with tighter, more LLM-friendly schemas than a raw FHIR REST proxy.
- **Priority:** **High.** This is explicitly called out as likely high-relevance given the project is
  built in an AI-assisted development context, and structurally it is the best-fitting feature in this
  entire file set for fhir-gql's stated role as an orchestration/middleware layer — it needs no new
  persistence, no new storage backend, and no device-protocol work, just a new transport wired to
  functionality (authenticated FHIR access) fhir-gql already has. It's also low-risk to build
  incrementally: a single `fhir-request`-style proxy tool over the existing Patient resource would be
  a complete, useful first version.

### AWS Textract Document OCR / Text Detection Operation
- **What it does:** A FHIR "operation" (custom RPC-style endpoint, `$aws-textract` by convention)
  that runs AWS Textract's asynchronous OCR/text-detection over a `Media` or `DocumentReference`
  resource's attached document (e.g. a scanned lab report or referral PDF/image), stores the raw
  Textract JSON result as a new `Media` resource, and optionally chains AWS Comprehend Medical over
  the extracted text to pull out structured medical entities (medications, conditions, dosages, etc.),
  storing that as a second `Media` resource.
- **Source files:** `src/cloud/aws/textract.ts` — `awsTextractHandler(req)` (the FHIR operation
  handler), `createBinaryAndMedia` (shared helper for writing a result blob + wrapping it in a
  `Media` resource).
- **How it works:** Gated by a **project feature flag** (`project.features?.includes('aws-textract')`)
  — i.e. this is opt-in per tenant/project, not globally enabled — and requires the binary storage
  backend to actually be `S3Storage` (`storage instanceof S3Storage`), since Textract operates
  directly against an S3 object location rather than accepting uploaded bytes. Resolves the input
  `Binary` from either a `Media.content.url` or a `DocumentReference.content[0].attachment.url`
  reference, then calls Textract's **async job API**:
  `StartDocumentTextDetectionCommand` (kicks off a job referencing the binary's S3 `Bucket`/`Key`
  directly — no data transits through the Medplum server), then polls
  `GetDocumentTextDetectionCommand` in a loop (1-second `sleep` between polls, capped at 120
  iterations ≈ 2 minutes) until `JobStatus` leaves `IN_PROGRESS`. Textract results can be paginated
  (`NextToken`), so it follows the pagination chain to accumulate all `Blocks` (Textract's per-line/
  per-word detected-text units) into one combined result. The full raw Textract JSON is saved as a
  new `Binary` + `Media` pair (`createBinaryAndMedia`, `filename: 'textract.json'`) linked to the same
  `subject` as the input. If the caller's request body includes `{comprehend: true}`, it joins all
  detected text lines and sends them to **AWS Comprehend Medical**
  (`DetectEntitiesV2Command`) for medical entity extraction, storing that result as a second
  `Media` (`filename: 'comprehend.json'`) — this is the piece that turns raw OCR text into structured,
  codeable medical concepts.
- **Belongs in:** `fhir-server (data layer/storage backend)` — deeply coupled to the S3 storage
  backend (`storage.getKey`, `storage.bucket`) and to the FHIR operation/repository machinery
  (`FhirRequest`/`FhirResponse` types, `repo.readResource`, `repo.createResource`) that only
  fhir-server has. Not something fhir-gql could implement without owning storage.
- **Port notes for fhir-gql:** Not a near-term fit — no `Media`/`DocumentReference` support and no S3
  storage ownership in fhir-gql. If this capability is wanted eventually and fhir-server implements
  it, the Python equivalents are `boto3` (`textract` and `comprehendmedical` clients — same
  start/poll/paginate async-job pattern: `start_document_text_detection` /
  `get_document_text_detection`, `detect_entities_v2`). fhir-gql's only plausible role would be
  exposing a GraphQL mutation/REST endpoint that triggers this operation on the downstream server and
  polls/relays job status — i.e. the orchestration-only slice, not the OCR logic itself.
- **Priority:** Low — requires `Media`/`DocumentReference` resources (not yet modeled anywhere in this
  stack), AWS-specific, feature-flagged even in Medplum itself, and clearly a "nice to have, tenant
  opt-in" feature rather than core. Revisit only after Binary/Media/DocumentReference exist and there's
  a concrete document-ingestion use case.

---

## Summary Table

| Feature | Priority | Belongs in |
|---|---|---|
| Pluggable Binary Storage Abstraction (`BinaryStorage` interface) | Low (High for fhir-server team) | fhir-server (data layer) |
| Filesystem Binary Storage Backend | Low | fhir-server (data layer) |
| AWS S3 Binary Storage Backend | Low (Medium to understand contract) | fhir-server (data layer) |
| Azure Blob Storage Backend | Low | fhir-server (data layer) |
| Google Cloud Storage Backend | Low | fhir-server (data layer) |
| Local Presigned URL / Storage Proxy Endpoint | Medium | both |
| File Metadata / Upload Safety Checks | Medium | both |
| FHIR `Binary` Resource REST Endpoint | Medium (→High once non-Patient resources land) | fhir-server (data layer), thin proxy in fhir-gql |
| DICOMweb (WADO-RS) Endpoint | Low | both (stub only in Medplum itself) |
| HL7v2 Message Parsing | Low | both |
| Medplum Agent — Device/Edge WebSocket Connector | Low | fhir-server (data layer) |
| **Model Context Protocol (MCP) Server** | **High** | **fhir-gql (middleware)** |
| AWS Textract Document OCR | Low | fhir-server (data layer) |

## Recommended Next Steps

The clear standout from this file set is the **MCP server** — it is the one capability that plugs
directly into fhir-gql's existing strengths (FastAPI/ASGI, JWT auth, RBAC, an existing `fhir_client`
proxy to the downstream server) without requiring any new persistence, storage backend, or protocol
work, and it directly serves the project's AI-assisted-development context. A pragmatic first slice:
mount `mcp.server.fastmcp.FastMCP`'s Streamable HTTP ASGI app under `/mcp` in the existing FastAPI app,
reuse the current auth/RBAC dependency chain to gate it, and ship one real tool — a `fhir-request`-
style proxy that calls through the existing `fhir_client` — before investing in `search`/`fetch` stubs
or SSE transport (only needed for ChatGPT-connector compatibility or multi-replica deployments,
respectively). Everything else in this assignment (binary/S3/Azure/GCS storage, presigned URLs,
DICOMweb, HL7v2 ingestion, the on-prem Agent, Textract OCR) is legitimately out of scope for fhir-gql
under the stated architecture — it is fhir-server/storage-backend territory, gated behind resources
(`Binary`, `Media`, `DocumentReference`, `Agent`) that don't exist anywhere in this stack yet. The one
piece worth designing for early, even before those resources land, is the **presigned-URL contract**:
deciding now how fhir-gql's REST/GraphQL layers will represent "here's a URL to upload/download bytes"
in their schemas will avoid a breaking API change later, since virtually every future rich-content
feature (photos, attachments, imaging, OCR'd documents) depends on that same contract shape.
