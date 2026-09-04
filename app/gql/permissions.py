"""
GraphQL adapter for RBAC.

REST enforces permissions per-route via `require_permission()`, a FastAPI
Depends() factory (app/auth/rbac.py). GraphQL fields are not routes, so there
is no per-field Depends() equivalent — each resolver instead calls
`require_gql_permission(info, resource, action)` explicitly as its first
line, exactly mirroring the `resource:action` check REST performs. Both
paths funnel through `check_permission()` so there is exactly one place the
permission rule itself is defined.

Subscriptions need a second, separate entry point — `authenticate_gql_subscription()`
below — because they run over WebSocket, not HTTP. See that function's
docstring and app/gql/context.py's get_context() for why a WebSocket
connection can never carry the same `request.state.user` HTTP requests do.
"""

import jwt
import strawberry

from app.auth.dependencies import decode_token
from app.auth.models import AuthUser
from app.auth.rbac import check_permission
from app.errors.auth import AuthenticationError


def require_gql_permission(
    info: strawberry.types.Info, resource: str, action: str
) -> AuthUser:
    """
    Check that the caller has `resource:action` and return their AuthUser.

    Reads the JWT payload from `request.state.user`, populated by
    `get_current_user` before the GraphQL router ever runs (see the
    `dependencies=[Depends(get_current_user)]` on the `/graphql` mount in
    app/main.py). Raises HTTPException(403) on failure — the resolver's
    `@translate_errors` decorator (app.gql.errors) converts that into a
    GraphQLError so the client sees the same 403 semantics REST would give.

    Args:
        info:     Strawberry's resolver info object — carries `info.context`.
        resource: Permission resource name, e.g. "patient".
        action:   Permission action, e.g. "read" | "create" | "update" | "delete".

    Returns:
        A typed AuthUser for the authenticated caller.
    """
    request = info.context.request
    user: dict = request.state.user
    return check_permission(user, resource, action, request.state.token)


def authenticate_gql_subscription(
    info: strawberry.types.Info, resource: str, action: str
) -> AuthUser:
    """
    Subscription equivalent of require_gql_permission() — call this as the
    first line of any `@strawberry.subscription` resolver that needs an
    authenticated actor.

    Why this can't just be require_gql_permission(): that function reads
    `request.state.user`, which is populated from an `Authorization` HTTP
    header — but a browser's native WebSocket API cannot send custom headers
    on the connection at all, so a WS request never carries one (see
    app/gql/context.py's get_context() docstring for the full explanation).
    The graphql-transport-ws/graphql-ws protocols solve this differently:
    the client sends its token inside the `connection_init` message's
    payload, *after* the socket is already open. Strawberry captures that
    payload onto `info.context.connection_params` once it arrives, so this
    function reads the token from there instead — same shape REST/HTTP
    expects (`{"Authorization": "Bearer <token>"}`), just sourced from a
    different place.

    Deliberately re-implements the header-splitting logic
    `get_current_user()` (app/auth/dependencies.py) uses, rather than
    calling that function directly — it expects a `Request` and reads
    `request.headers`, but a subscription resolver only has
    `connection_params`, a plain dict the client controls, not a Request.
    `decode_token()` and `check_permission()` are reused as-is since they
    only operate on the already-extracted token string / decoded payload.

    Args:
        info:     Strawberry's resolver info object — carries `info.context`.
        resource: Permission resource name, e.g. "patient".
        action:   Permission action, e.g. "read" | "create" | "update" | "delete".

    Returns:
        A typed AuthUser for the authenticated caller.

    Raises:
        AuthenticationError: Missing, malformed, expired, or invalid token —
            raised from inside the resolver, so Strawberry reports it as a
            normal GraphQL error on the subscription's error channel instead
            of the connection dying ungracefully.
        HTTPException(403): Valid token, but missing `resource:action`
            (raised by check_permission(), same rule REST/queries use).
    """
    connection_params: dict = info.context.connection_params or {}
    auth_header = connection_params.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthenticationError("Missing authentication token")

    token = auth_header.split(" ")[1]

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")
    except Exception:
        raise AuthenticationError("Invalid or expired token")

    return check_permission(payload, resource, action, token)
