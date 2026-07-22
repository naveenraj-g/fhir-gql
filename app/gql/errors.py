"""
Maps REST-style exceptions raised by the service layer into GraphQL errors.

Service methods (PatientService, OrganizationsService, ...) raise plain
FastAPI `HTTPException`, or the app-wide `AppError` base class, exactly as
they do when called from REST routers (see app/core/errors.py). Those
exception types mean nothing to a GraphQL client on their own — left
unhandled, Strawberry would report every one of them as a generic
"unexpected error" with no status code. `translate_errors` converts them
into `graphql.GraphQLError` carrying the original status code (in
`extensions.code`) and message, so GraphQL clients get the same information
REST clients get via `{"detail": ...}`.
"""

import functools
from typing import Awaitable, Callable, TypeVar

from fastapi import HTTPException
from graphql import GraphQLError

from app.core.errors import AppError

T = TypeVar("T")


def translate_errors(resolver: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """
    Decorator for async Strawberry resolver/mutation methods.

    Catches `HTTPException` / `AppError` raised anywhere in the resolver's
    call chain (RBAC check via require_gql_permission, or the service call
    itself) and re-raises as a `GraphQLError`. Any other exception is left
    to propagate unchanged so Strawberry's default handling — and the
    process logs — still surface genuine bugs rather than masking them.
    """

    @functools.wraps(resolver)
    async def wrapper(*args, **kwargs):
        try:
            return await resolver(*args, **kwargs)
        except HTTPException as exc:
            raise GraphQLError(str(exc.detail), extensions={"code": exc.status_code}) from exc
        except AppError as exc:
            raise GraphQLError(exc.message, extensions={"code": exc.status_code}) from exc

    return wrapper
