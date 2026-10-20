"""
FastAPI application factory and startup/shutdown lifecycle for the FHIR middleware service.

This module is the entry point for uvicorn: `uvicorn app.main:app`.

Responsibilities:
  - Bootstrap structured JSON logging before anything else runs.
  - Initialise the dependency-injection container and wire it to the `app` package.
  - Define the application lifespan (startup: Redis ping; shutdown: close connections).
  - Register exception handlers, middleware, and the GraphQL router.
  - Expose a /health liveness endpoint that requires no authentication.

Architecture note: this service is a pure middleware layer — it owns auth/RBAC,
business-rule validation, and workflow orchestration, but never writes to a database
directly. All persistence flows through the downstream FHIR Server via FhirClient.

This is a patient-only slice of the full fhir-gql middleware — see README.md.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.connectors.universal.schema import graphql_router as universal_graphql_router
from app.core.config import settings
from app.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import get_logger, setup_logging
from app.core.middleware import RequestIdMiddleware
from app.core.redis import redis_client
from app.core.security_headers import SecurityHeadersMiddleware
from app.di.container import Container
from app.gql.schema import graphql_router
from app.middleware.access_log import AccessLogMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

setup_logging()
logger = get_logger(__name__)

container = Container()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    ASGI lifespan context manager — runs startup logic before `yield` and
    teardown logic after `yield` (when the server is shutting down).

    Startup:
      - Pings Redis to confirm connectivity. On success, stores the client on
        `app.state.redis` so RateLimitMiddleware can retrieve it per-request.
      - On failure, sets `app.state.redis = None` so the middleware falls back
        to the in-process store (with a degraded-mode warning on every request).

    Teardown:
      - Closes the FhirClient httpx connection pool to drain in-flight requests.
      - Closes the Redis connection pool to release socket resources cleanly.
      Both are closed explicitly rather than relying on garbage collection because
      async resources may not be cleaned up promptly by the GC.
    """
    if not settings.redis.enabled:
        app.state.redis = None
        logger.info(
            "Redis disabled via configs/config.yaml's redis.enabled — "
            "rate limiting will be process-local only"
        )
    else:
        try:
            await redis_client.ping()
            app.state.redis = redis_client
            logger.info("Redis connected", extra={"url": settings.REDIS_URL})
        except Exception as exc:
            app.state.redis = None
            logger.error(
                "Redis unavailable at startup — rate limiting will be process-local only",
                exc_info=exc,
            )

    yield

    fhir_client = container.core.fhir_client()
    await fhir_client.aclose()
    terminology_client = container.core.terminology_client()
    await terminology_client.aclose()
    await redis_client.aclose()


app = FastAPI(
    title=settings.app.title,
    version=settings.app.version,
    description=(
        "Healthcare middleware — business logic and orchestration layer above the FHIR Server, "
        "scoped to the Patient resource. Owns auth/RBAC and use-case validation. "
        "All persistence flows through the FHIR Server — this service never writes directly to the database. "
        "Stamps `created_by` / `updated_by` from the validated JWT subject on every FHIR write."
    ),
    docs_url="/docs" if settings.app.docs_enabled else None,
    redoc_url="/redoc" if settings.app.docs_enabled else None,
    lifespan=lifespan,
)

app.container = container

# ── Exception handlers ─────────────────────────────────────────────────────────
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# ── Middleware (applied in reverse order — last added runs first / outermost) ──
app.add_middleware(
    RateLimitMiddleware,
    read_limit=settings.rate_limit.read_limit,
    write_limit=settings.rate_limit.write_limit,
    window_seconds=settings.rate_limit.window_seconds,
)
# AccessLogMiddleware must be added BEFORE (so it ends up nested inside)
# RequestIdMiddleware, not after. RequestIdMiddleware sets request_id_ctx_var
# before calling its own call_next() — everything that call_next() invokes,
# including AccessLogMiddleware's entire dispatch(), runs inside the child
# task Starlette's BaseHTTPMiddleware spawns at that point, which DOES see
# that value. Added the other way round, AccessLogMiddleware's post-call_next
# logger call would run back in ITS OWN (parent) task — a context the
# RequestIdMiddleware-side child task's ContextVar mutation never propagates
# back up to — and every access log line would be missing request_id. See
# app.core.request_context's module docstring for the general rule.
app.add_middleware(AccessLogMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
# CORS is registered last so it's the outermost middleware — it must wrap every
# other layer (including error responses and preflight OPTIONS requests, which
# never reach RateLimitMiddleware/RequestIdMiddleware/route handlers at all) so
# that CORS headers are present on every response a browser will see. No
# CORSMiddleware is registered at all while cors.enabled is false.
if settings.cors.enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.allow_origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
    )

# ── Routers ────────────────────────────────────────────────────────────────────
# GraphQL is this service's only transport — the REST routers (app/routers/)
# that used to sit alongside it have been removed; app/schemas/ stays, since
# every GraphQL input/output type is still derived from those same Pydantic
# models, and REST can be rebuilt on top of them again later if needed.
#
# auth is NOT a router-level dependency here: GraphiQL's IDE shell is served
# via GET /graphql, and a router-level Depends(get_current_user) would 401 a
# browser's plain navigation before the IDE could ever load. Auth instead
# runs inside app/gql/context.py's get_context() — see that module's
# docstring for why, and why it's still equivalent to gating the whole
# router would have been for every real query/mutation.
app.include_router(
    graphql_router,
    prefix="/graphql",
)

# EXPERIMENTAL — see app/connectors/universal/__init__.py's package
# docstring and dev-docs/18-universal-fhir-graphql-experiment.md. A second,
# independent GraphQL schema (Organization only, full CRUD) proving out
# "one universal, FHIR R4-shaped GraphQL schema, with per-connector
# translation" as an alternative to the main /graphql endpoint above.
# Mounted at its own path so it can be evaluated side-by-side without
# touching the main schema/endpoint at all.
app.include_router(
    universal_graphql_router,
    prefix="/graphql-fhir",
)


# ── OpenAPI schema override ────────────────────────────────────────────────────
# FastAPI does not expose a constructor param for top-level `security` or
# `securitySchemes` — we must override app.openapi() to inject them.
# The schema is generated once and cached on app.openapi_schema for all subsequent
# calls to /openapi.json so there is no per-request overhead.
def _custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    # Register the Bearer JWT security scheme under components so Swagger UI
    # renders the Authorize button and lets users paste their JWT for testing.
    schema.setdefault("components", {})["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT access token (without the 'Bearer ' prefix).",
        }
    }
    # Apply BearerAuth globally — every endpoint shows a lock icon by default.
    # Individual public endpoints (e.g. /health) can override this with security=[].
    schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = _custom_openapi  # type: ignore[method-assign]


# ── Health (no auth) ───────────────────────────────────────────────────────────
@app.get(
    "/health",
    operation_id="health_check",
    summary="Liveness probe",
    description="Returns 200 if the process is running. No authentication required.",
    tags=["Health"],
)
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "req_id": request.state.request_id})
