"""Per-request context, carried in ContextVars rather than threaded through
function signatures — mirrors fhir-server's own app/core/request_context.py.

Why ContextVars: a GraphQL resolver calls into a service, which calls into a
client, which calls into FhirClient — none of those layers have a `Request`
object (and never will; passing request_id/actor down through every method
signature in that chain is not viable). `app.core.logging`'s formatters read
these directly, so any log line emitted anywhere in that chain automatically
carries the request's correlation fields with zero plumbing at the call site.

Each asyncio task gets its own copy, so concurrent requests never bleed into
each other.

Set by:
  - request_id              -> app.core.middleware.RequestIdMiddleware
  - actor_user_id/actor_org_id -> app.gql.context.get_context(), once
    get_current_user() has verified the JWT (GraphQL layer only, for now —
    REST's own get_current_user() doesn't call bind_actor() yet).

This module holds the ContextVars only.
"""

from contextvars import ContextVar

request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Acting user's `sub` claim — only populated once a GraphQL operation (not
# the bare GraphiQL IDE page load) has passed auth.
#
# Deliberately named `actor_*`, not `user_id`/`org_id`: FHIR resources and
# request payloads carry their OWN user_id/org_id fields, so an unqualified
# `user_id` in a log line would be ambiguous — the caller, or the record
# being operated on? `actor_` always means "who made this request".
actor_user_id_ctx_var: ContextVar[str | None] = ContextVar("actor_user_id", default=None)

# Acting user's `org_id` claim — the tenant the request is scoped to.
actor_org_id_ctx_var: ContextVar[str | None] = ContextVar("actor_org_id", default=None)


def bind_actor(request, user_id: str | None, org_id: str | None) -> None:
    """Attach the verified actor to the request's logging context. Called
    from app.gql.context.get_context() once get_current_user() has verified
    the JWT — the single place every real GraphQL operation passes through.

    Writes to BOTH the ContextVars and request.state, because they
    propagate in opposite directions:

    - ContextVars flow **downward** only. Starlette's BaseHTTPMiddleware
      runs the downstream app in a child anyio task, which copies the
      context at creation — so a value set here (inside get_context(),
      itself called from within the GraphQLRouter's own route handler) is
      visible to every service/client call a resolver makes afterward, but
      is INVISIBLE to any BaseHTTPMiddleware sitting above the route
      handler, which is still holding the parent context from before
      call_next() was invoked.
    - request.state is backed by the shared `scope` dict, the same object
      all the way up and down the stack — so AccessLogMiddleware (which
      sits above the route handler) can still read it after call_next()
      returns.
    """
    actor_user_id_ctx_var.set(user_id)
    actor_org_id_ctx_var.set(org_id)
    request.state.actor_user_id = user_id
    request.state.actor_org_id = org_id


def get_request_actor(request) -> dict[str, str]:
    """Actor fields off request.state — for middleware, which runs outside
    the task where the ContextVars were set. See bind_actor()."""
    actor = {
        "actor_user_id": getattr(request.state, "actor_user_id", None),
        "actor_org_id": getattr(request.state, "actor_org_id", None),
    }
    return {k: v for k, v in actor.items() if v is not None}


def get_log_context() -> dict[str, str]:
    """Snapshot of the non-None context fields, for injection into a log
    record. Used by both the JSON and console formatters.

    Keys are `actor_user_id`/`actor_org_id`, never bare `user_id`/`org_id` —
    see the module docstring for why.
    """
    ctx = {
        "request_id": request_id_ctx_var.get(),
        "actor_user_id": actor_user_id_ctx_var.get(),
        "actor_org_id": actor_org_id_ctx_var.get(),
    }
    return {k: v for k, v in ctx.items() if v is not None}
