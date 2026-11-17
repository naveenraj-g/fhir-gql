# fhir-gql

A GraphQL gateway that sits in front of a FHIR R4 data server. It owns authentication
(JWT), RBAC, rate limiting and the GraphQL schema; it never touches a database itself.

**Current scope: Organization and Location only.** Every other resource was removed to be
rebuilt later on the same pattern (see [Extending](#extending-with-another-resource)).

```
Client (web / mobile / AI agent)
        │  HTTPS — GraphQL (POST /graphql), JWT Bearer
        ▼
   fhir-gql  (this service: auth, RBAC, rate limit, schema)
        │  one active connector, chosen by config
        ├──────────────► internal  = our own fhir-server (`/organizations`, `/locations`)
        ├──────────────► medplum   = a Medplum server (`/Organization`, `/Location`)
        ├──────────────► openemr   = OpenEMR's FHIR R4 API (`/Organization`, `/Location`)
        └──────────────► epic      = Epic on FHIR sandbox, read-only (`/Organization`, `/Location`)
```

GraphQL is the only transport — there is no REST layer. `GET /health` exists for probes.

## How a request flows

```
GraphQL resolver (app/gql/<resource>/queries.py, mutations.py)
  → require_gql_permission(info, "<resource>", "<action>")   # JWT claims → RBAC
  → active connector (app/connectors/<name>/client.py)       # the HTTP call
      paths / search params / PATCH body from the active translator
      (app/connectors/translator_registry.py)
  → fhir-server or Medplum
```

- The resource is **genuine FHIR R4 JSON end to end**. The GraphQL types are generated from the
  Pydantic models in `app/fhir/schemas/`, and both backends speak the same shape, so there is no
  per-field mapping. A translator only supplies the URL paths, the search wiring and the PATCH body
  (`internal`: a plain partial object; `medplum`: an RFC 6902 JSON Patch array).
- **Search is real FHIR R4 search** on both backends (`app/connectors/fhir_search.py`). Every R4
  search parameter of the resource is a typed GraphQL argument; modifiers (`name:exact`), chains
  (`partof.name`) and anything else go through the generic `params` argument. `count`, `offset`,
  `sort`, `total`, `include` and `revinclude` are their own arguments.

## What is exposed

| Resource | Queries | Mutations |
|---|---|---|
| Organization | `getFhirOrganization`, `searchFhirOrganizations`, `getFhirOrganizations` | `createFhirOrganization`, `updateFhirOrganization`, `deleteFhirOrganization` |
| Location | `getFhirLocation`, `searchFhirLocations`, `getFhirLocations` | `createFhirLocation`, `updateFhirLocation`, `deleteFhirLocation` |

`searchFhir…` returns the whole searchset (matches, included resources, total, paging links,
warnings for ignored parameters); `getFhir…s` is the older matches-only form of the same search.
Permissions are `<resource>:read|create|update|delete`, read from the JWT.

Which resources are in the schema is set by `routes.enabled` in `configs/config.yaml` (names are the
keys of `RESOURCES` in `app/gql/schema.py`); a restart is required.

## Directory layout

```
app/
├── auth/          # JWT validation + RBAC
├── connectors/    # base.py (contracts), fhir_search.py (shared FHIR search plumbing),
│                  # registry.py (connector selection), translator_registry.py,
│                  # internal/ and medplum/ (client + one translator per resource)
├── core/          # settings, logging, redis, request context, security headers
├── di/            # dependency-injector container
├── errors/        # auth errors
├── fhir/schemas/  # canonical FHIR R4 Pydantic models (datatypes/, organization.py, location.py)
├── fhir_client/   # terminology client
├── gql/           # schema.py, context, permissions, error translation, shared search types,
│                  # organization/ and location/ packages
└── middleware/    # access log, Redis-backed rate limiting
configs/           # config.yaml (behaviour) and connectors/<name>.yaml (per-connector settings)
docker/connectors/openemr/   # a local OpenEMR for connector experiments
dev-docs/          # planning and research notes (see dev-docs/README.md for what is current)
```

## Setup

Dependencies are managed with [uv](https://docs.astral.sh/uv/).

```bash
uv sync                        # install dependencies into .venv
cp .env.example .env           # IAM issuer/JWKS, Redis, secrets
just dev                       # uvicorn app.main:app --port 8005 --reload
```

- `.env` needs a BetterAuth-compatible IAM issuer for JWT validation (`IAM_JWKS_URL`, `IAM_ISSUER`).
  `REDIS_URL` is used for rate limiting and falls back to an in-process store if Redis is
  unreachable (`redis.enabled: false` skips it).
- Which backend is live: `connectors.active` in `configs/config.yaml` (`internal`, `medplum`, `openemr` or `epic`).
  Each connector's own settings are in `configs/connectors/<name>.yaml`; the fhir-server address is
  `connectors.internal.base_url` (override with `CONNECTORS__INTERNAL__BASE_URL`). Medplum needs
  `CONNECTORS__MEDPLUM__CLIENT_ID` and `…__CLIENT_SECRET`. OpenEMR needs
  `CONNECTORS__OPENEMR__CLIENT_ID` and `…__PRIVATE_KEY_PATH` (an RSA private key; the matching public
  JWKS is registered in OpenEMR). It logs in with a signed JWT (RS384), not a secret. OpenEMR limits
  (verified live): with these system scopes it is **read-only** here (writes answer 405). `epic` is read-only too. Location has no write routes,
  Organization has no delete, and Organization create/update need an admin user login that system
  scopes can't provide (401). Scopes are `connectors.openemr.scope`.
- Any setting can be overridden by an environment variable using `__` for nesting.

## Extending with another resource

A resource is not finished until it works on **both** connectors. The pieces:

1. `app/fhir/schemas/<resource>.py`: the FHIR R4 Pydantic models (mirror `organization.py`).
2. `app/connectors/internal/translators/<resource>.py` and
   `app/connectors/medplum/translators/<resource>.py`, exported from each `translators/__init__.py`.
3. A `<RESOURCE>_TRANSLATORS` dict and `active_<resource>_translator()` in
   `app/connectors/translator_registry.py`, plus a `<Resource>WireTranslator` contract in
   `app/connectors/base.py`.
4. `app/gql/<resource>/` with `types/`, `search_params.py`, `queries.py`, `mutations.py` (mirror
   `app/gql/organization/`).
5. An entry in `RESOURCES` in `app/gql/schema.py`, and the name in `routes.enabled`.

The fhir-server half of "end to end" is in that repo's `CLAUDE.md`.
