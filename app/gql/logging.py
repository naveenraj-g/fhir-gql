"""
One log line per GraphQL operation — the GraphQL-level complement to
app.middleware.access_log.AccessLogMiddleware's HTTP-level line.

Registered once on the schema (app/gql/schema.py) via Strawberry's
SchemaExtension mechanism, so it covers every query/mutation/subscription
across every resource automatically — no per-resolver code needed, same
"no per-method logging code" ideal as app.core.logging.trace_methods, just
applied at the GraphQL-operation unit instead of the method unit.

Why this line exists separately from AccessLogMiddleware's: GraphQL returns
HTTP 200 even when a field resolver fails (the client-facing error channel
is `result.errors` in the response body, not the status code) — an
HTTP-only access log would never surface that a request actually failed.

request_id/actor_user_id/actor_org_id are NOT passed explicitly in `extra`
here — app.core.logging's formatters already inject them automatically from
app.core.request_context's ContextVars (set in app.gql.context.get_context(),
which runs before this extension's post-yield half, in the same task).
"""

import time

from strawberry.extensions import SchemaExtension

from app.core.logging import get_logger

logger = get_logger(__name__)


class GqlLoggingExtension(SchemaExtension):
    def on_operation(self):
        started = time.perf_counter()
        yield
        ctx = self.execution_context
        duration_ms = round((time.perf_counter() - started) * 1000, 2)

        # The raw query string is available from the start, but it's only
        # *parsed* into graphql_document by the time this post-yield half
        # runs — and not at all if parsing itself failed, hence the guard.
        operation_type: str | None = None
        operation_name: str | None = None
        if ctx.graphql_document:
            for definition in ctx.graphql_document.definitions:
                # Only OperationDefinitionNode (not FragmentDefinitionNode)
                # carries `.operation` — a document can define fragments too.
                if hasattr(definition, "operation"):
                    operation_type = definition.operation.value
                    operation_name = (
                        definition.name.value if definition.name else None
                    )
                    break

        errors = (ctx.result.errors if ctx.result else None) or []
        level = "warning" if errors else "info"

        getattr(logger, level)(
            f"gql.{operation_type or 'operation'} {operation_name or '<anonymous>'}",
            extra={
                "event": "gql.operation",
                "operation_type": operation_type,
                "operation_name": operation_name,
                "duration_ms": duration_ms,
                "error_count": len(errors),
            },
        )
