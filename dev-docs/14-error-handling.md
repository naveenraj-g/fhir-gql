# Error handling, end to end

How an error travels from `fhir-server` (the separate service that owns persistence) through
`fhir-gql`'s HTTP client, service layer, and both APIs (REST, GraphQL), plus what a frontend should
do with what it receives. Written after the two fixes below landed, so this describes actual
behavior, not aspirational behavior.

```
fhir-server (OperationOutcome)
    → app/fhir_client/client.py (FhirClient._handle / _extract_detail)
        → app/services/*.py, app/services/tenant_scope.py (HTTPException / AppError)
            → REST: app/main.py's four handlers
            → GraphQL: app/gql/errors.py's translate_errors
                → frontend
```

## 1. fhir-server

`fhir-server` (`D:\code\work\projects\fhir\fhir-server`) normalizes every error — validation,
not-found, conflict, or unhandled — into a FHIR `OperationOutcome` resource via its own global
exception handlers (`app/errors/handlers.py` in that repo), registered for `ApplicationError`,
`HTTPException`, `RequestValidationError`, `ResponseValidationError`, and a catch-all `Exception`.

Wire shape:
```json
{
  "resourceType": "OperationOutcome",
  "issue": [
    {
      "severity": "error",
      "code": "invalid",
      "diagnostics": "Schedule 'Schedule/9' not found.",
      "expression": ["schedule"]
    }
  ]
}
```
`expression` (a field path) is only present for field-level validation errors — it comes from that
repo's `InputValidationError`, which converts each Pydantic error it catches into one `issue` entry.

In practice, most real validation there is raised as a plain `HTTPException(status, "message")`
from the repository layer (e.g. `slot_repository.py`, `practitioner_repository.py`), not through
its `ApplicationError` subclasses (`BusinessRuleViolationError`, `ResourceConflictError` exist but
have no call sites) — it doesn't matter here, since the global handler normalizes both into the
same `OperationOutcome` shape regardless of which exception type triggered it.

## 2. `app/fhir_client/client.py` — the boundary

`FhirClient._handle()` is the single point where every domain client (`OrganizationClient`,
`ScheduleClient`, `SlotClient`, ...) converts a raw `httpx.Response` into either a parsed dict or a
`fastapi.HTTPException`. On a 4xx/5xx, `_extract_detail()` parses the `OperationOutcome` body:

- **One issue, no `expression`** → `detail` is a plain string (`issue[0]["diagnostics"]`) — the
  common case (a single 404/409/422 message) stays a simple string.
- **Multiple issues, or any issue with `expression`** → `detail` becomes a `list[dict]` of
  `{"field": ..., "message": ...}` entries — deliberately the same shape
  `RequestValidationError.errors()` already produces in REST (see §3), so a field-level 422 looks
  the same wire whether it came from fhir-gql's own Pydantic schemas or from fhir-server.
- **Anything else** (non-JSON body, not an `OperationOutcome`) → falls back to the raw response
  text, defensively — shouldn't happen given fhir-server's contract, but avoids a crash if it does.

This is the only place that needs to understand fhir-server's wire format. Every service, REST
router, and GraphQL resolver above this layer only ever sees a plain `HTTPException` with a
already-normalized `detail`.

## 3. Service layer

Services (`app/services/*.py`) raise plain `fastapi.HTTPException` directly for their own
business-logic checks (duplicate-name conflicts, empty-patch rejections, actor-cardinality rules),
or call the shared helpers in `app/services/tenant_scope.py`:

- `check_tenant_ownership()` → 404 if `resource.get("org_id") != actor.org_id` (never 403 — same
  reasoning as REST/GraphQL: don't reveal a resource exists in a tenant the caller can't see).
- `validate_reference()` → 404/422 when a cross-resource reference (e.g. Schedule → Organization)
  doesn't resolve or fails tenant ownership.

Errors raised by `FhirClient._handle()` (§2) are never caught here — they propagate straight
through to whichever API layer called the service.

## 4. REST — `app/main.py`

Four handlers, registered once at startup, all producing the same `{"detail": ...}` envelope:

| Exception | Status | Body |
|---|---|---|
| `AppError` (and subclasses, e.g. `AuthenticationError`) | `exc.status_code` | `{"detail": exc.message}` |
| `HTTPException` (including everything forwarded from `FhirClient`) | `exc.status_code` | `{"detail": exc.detail}` — string or `list[dict]`, per §2 |
| `RequestValidationError` (fhir-gql's own Pydantic schemas failing on request body/query params) | `422` | `{"detail": exc.errors()}` — same `list[dict]` shape as §2's multi-issue case |
| Catch-all `Exception` | `500` | `{"detail": "Internal server error"}` — no internals leaked |

## 5. GraphQL — `app/gql/errors.py`

Every query/mutation resolver is wrapped in `@translate_errors`, which catches the same exception
types REST handles and converts them into a `graphql.GraphQLError`:

| Exception | `extensions.code` | Message / extra |
|---|---|---|
| `HTTPException` | `exc.status_code` | `str(exc.detail)` as the GraphQL error message |
| `AppError` | `exc.status_code` | `exc.message` |
| `pydantic.ValidationError` (raised by `input.to_pydantic()` — every mutation constructs a real instance of the same Pydantic schema class REST uses, so the same `min_length`/validators fire) | `422` | message `"Validation error"`, plus `extensions.errors = exc.errors()` — same shape as REST's `detail` array |

Anything else (a genuine bug) is left to propagate to Strawberry's default handling, same
philosophy as REST's catch-all: don't mask unexpected errors as something they're not.

## 6. Frontend consumption guidance

The two transports carry the same information in different envelopes. Normalize both to one shape
before the rest of the frontend touches errors, so UI code (toast, inline field errors, redirect on
401) doesn't need to branch on REST vs. GraphQL:

```ts
type NormalizedError = {
  code: number;                                   // HTTP-status-equivalent
  message: string;
  fields?: { field: string | null; message: string }[];
};
```

- **REST**: `code` = HTTP status. If `detail` is a string, that's `message`. If `detail` is an
  array (the `RequestValidationError`/multi-issue shape), map it to `fields` and set `message` to
  something generic like `"Validation error"` (or join the field messages).
- **GraphQL**: read `errors[0].extensions.code` as `code` — if absent, it's an uncaught exception
  Strawberry didn't recognize (treat as `500`). `errors[0].extensions.errors`, if present, maps to
  `fields`; otherwise `errors[0].message` is the `message`.
- A single normalization function per transport (REST fetch wrapper, GraphQL client's error link)
  should be the only place that knows this shape difference exists. Everything downstream —
  which toast to show, which form field to highlight, whether to redirect on a 401 — should consume
  `NormalizedError` only, regardless of which API produced it.
