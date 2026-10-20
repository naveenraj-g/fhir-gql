# fhir-gql (Patient slice)

A patient-only slice of the `fhir-gql` middleware/orchestration layer that sits in
front of a FHIR R4 data server. It owns authentication, RBAC, and rate limiting for
the **Patient** resource — nothing else. Every other resource (Organization,
Appointment, Encounter, ...) was intentionally left out of this copy; add them back
the same way Patient is wired (see [Extending](#extending-with-another-resource)).

```
Client Applications (Web / Mobile / AI Agent)
              │  HTTPS — REST, JWT Bearer
              ▼
         fhir-gql   (this service)
              │  HTTP — plain JSON, no auth
              ▼
        fhir-server  (FHIR R4 data layer)
              │
       PostgreSQL + Redis
```

**Key contract:**

- This service never writes to a database directly — all persistence goes through the `fhir-server` REST API.
- `fhir-server` never validates business rules — it trusts whatever valid payload it receives.
- Auth claims (`user_id`, `org_id`, `created_by`, `updated_by`) are resolved here from the validated JWT and passed through on every write — callers never supply them directly.

## Two transports, one service layer

Both REST and GraphQL route through the exact same `PatientService`:

```
Router / Resolver → PatientService → PatientClient (httpx) → fhir-server
```

- **REST** — `app/routers/patient.py`, 42 endpoints under `/api/v1/patients` (core CRUD +
  9 sub-resource types × 4 endpoints each). Swagger UI at `/docs`.
- **GraphQL** — `app/gql/schema.py` + `app/gql/resolvers/patient.py`, mounted at `/graphql`
  (GraphiQL IDE in non-production environments).

## Directory layout

```
app/
├── auth/         # JWT validation (get_current_user, decode_token) + RBAC (require_permission)
├── core/         # config, logging, redis client, content negotiation, request-id middleware
├── di/           # dependency-injector container (composition root) + patient module
├── errors/       # AppError hierarchy
├── fhir_client/  # low-level httpx wrapper (client.py) + Patient-specific paths (patient.py)
├── gql/          # GraphQL context, schema, permissions, error translation, patient resolvers/types
├── middleware/   # Redis-backed sliding-window RateLimitMiddleware
├── routers/      # FastAPI route definitions (patient.py)
├── schemas/      # Pydantic request/response schemas — shared enums + app/schemas/patient/
└── services/     # PatientService — orchestration between routers/resolvers and PatientClient
```

Request flow, error handling, auth, and rate limiting follow the same design as the
full fhir-gql service — see the docstrings in `app/main.py`, `app/gql/context.py`, and
`app/middleware/rate_limit.py` for the reasoning behind each.

## Setup

Dependencies are managed with [uv](https://docs.astral.sh/uv/).

```bash
uv sync                        # install dependencies into .venv
cp .env.example .env           # point at your fhir-server / IAM / Redis instances
just dev                       # uvicorn app.main:app --port 8005 --reload
```

`.env` needs a BetterAuth-compatible IAM issuer for JWT validation
(`IAM_JWKS_URL` / `IAM_ISSUER`) and Redis for rate limiting (`REDIS_URL` —
falls back to an in-process store if unreachable). The running `fhir-server`
instance's address is `configs/connectors/internal.yaml`'s `base_url`
instead (override per-environment with `CONNECTORS__INTERNAL__BASE_URL`).

## Extending with another resource

1. Copy the pattern from the source project's `app/{routers,services,fhir_client,schemas,di/modules,di/dependencies}/<resource>.py` and `app/gql/{types,resolvers}/<resource>.py`.
2. Add its `providers.Container(...)` (with `core=core`) to `app/di/container.py`.
3. Register its router in `app/routers/__init__.py` and its Query/Mutation mixins in `app/gql/schema.py`.
