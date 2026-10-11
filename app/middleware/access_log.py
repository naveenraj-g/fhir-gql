"""One log line per GraphQL HTTP request — the record that a request
happened at all, mirroring fhir-server's app/middleware/access_log.py.

Deliberately scoped to `/graphql` only, not every path this service serves.
Bringing fhir-server's logging architecture over was asked for the GraphQL
layer specifically — REST's own routers (app/routers/*.py) get no new
logging here; that's a separate decision for later.

Deliberately metadata-only: no request/response bodies. Operation-level
detail (operation type/name, GraphQL error count) is logged separately by
app.gql.logging.GqlLoggingExtension, which has the GraphQL execution context
this middleware doesn't.

request_id comes from the formatter (ContextVar). actor_user_id/actor_org_id
can't: they're bound in app.gql.context.get_context(), which runs inside the
GraphQLRouter's own route handler — a child task whose context never
propagates back up here — so they're read off request.state instead. See
app.core.request_context.bind_actor().
"""

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger
from app.core.request_context import get_request_actor

logger = get_logger(__name__)


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if not path.startswith("/graphql"):
            return await call_next(request)

        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            # The exception handlers log the failure in detail; this line
            # exists so the request still gets an access record with timing
            # rather than vanishing from the request stream entirely.
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.error(
                f"{request.method} {path} -> 500",
                extra={
                    "event": "http.request",
                    "method": request.method,
                    "path": path,
                    "status": 500,
                    "duration_ms": duration_ms,
                    **get_request_actor(request),
                },
            )
            raise

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        status = response.status_code

        # 5xx is our fault, 4xx is the caller's, everything else is routine.
        if status >= 500:
            level = "error"
        elif status >= 400:
            level = "warning"
        else:
            level = "info"

        getattr(logger, level)(
            f"{request.method} {path} -> {status}",
            extra={
                "event": "http.request",
                "method": request.method,
                "path": path,
                "status": status,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else None,
                # Read off request.state, NOT the ContextVars — the actor is
                # bound inside get_context(), which runs in a child task
                # whose context never propagates back up to here.
                **get_request_actor(request),
            },
        )

        return response
