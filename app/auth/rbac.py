from fastapi import HTTPException, Request, status

from app.auth.models import AuthUser


def check_permission(user: dict, resource: str, action: str) -> AuthUser:
    """
    Core RBAC rule — the single source of truth for `resource:action` checks.

    Shared by both transports: `require_permission()` below wraps this for REST
    (FastAPI Depends()), and `app.gql.permissions.require_gql_permission` wraps
    this for GraphQL resolvers. Keeping the rule here means both transports stay
    in sync automatically instead of drifting via copy-paste.

    Args:
        user:     The decoded JWT payload (request.state.user).
        resource: Permission resource name, e.g. "patient".
        action:   Permission action, e.g. "read" | "create" | "update" | "delete".

    Returns:
        A typed AuthUser built from the JWT's `sub` / `activeOrganizationId` claims.

    Raises:
        HTTPException(403): If `resource:action` is not in the JWT's permissions claim.
    """
    permissions: list[str] = user.get("permissions", [])

    if f"{resource}:{action}" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {resource}:{action}",
        )

    return AuthUser(
        sub=user.get("sub", ""),
        org_id=user.get("activeOrganizationId"),
    )


def require_permission(resource: str, action: str):
    """
    FastAPI dependency factory — checks the caller has `resource:action` in their
    JWT permissions and returns a typed AuthUser built from request.state.user.

    Requires get_current_user to have already run (applied at router level).
    Thin wrapper around check_permission(); see that function for the actual rule.
    """

    async def _check(request: Request) -> AuthUser:
        return check_permission(request.state.user, resource, action)

    _check.required_permission = f"{resource}:{action}"
    return _check
