"""
Maps REST-style exceptions raised by the service layer into GraphQL errors.

Service methods (PatientService, OrganizationsService, ...) raise plain
FastAPI `HTTPException`, or the app-wide `AppError` base class, exactly as
they do when called from REST routers (see app/core/errors.py). Mutation
resolvers also call `input.to_pydantic()`, which runs the same Pydantic
validation (`min_length`, custom validators, ...) REST gets from the input
schema directly, and can raise `pydantic.ValidationError`. None of these
exception types mean anything to a GraphQL client on their own — left
unhandled, Strawberry would report every one of them as a generic
"unexpected error" with no status code. `translate_errors` converts them
into `graphql.GraphQLError` carrying the original status code (in
`extensions.code`) and message, so GraphQL clients get the same information
REST clients get via `{"detail": ...}`.
"""

import functools
from typing import Awaitable, Callable, TypeVar

import pydantic
from fastapi import HTTPException
from graphql import GraphQLError

from app.core.errors import AppError

T = TypeVar("T")


def translate_errors(
    resolver: Callable[..., Awaitable[T]],
) -> Callable[..., Awaitable[T]]:
    """
    Decorator for async Strawberry resolver/mutation methods.

    Catches `HTTPException` / `AppError` / `pydantic.ValidationError` raised
    anywhere in the resolver's call chain (RBAC check via
    require_gql_permission, `input.to_pydantic()`, or the service call
    itself) and re-raises as a `GraphQLError`. Any other exception is left
    to propagate unchanged so Strawberry's default handling — and the
    process logs — still surface genuine bugs rather than masking them.
    """

    @functools.wraps(resolver)
    async def wrapper(*args, **kwargs):
        try:
            return await resolver(*args, **kwargs)
        except HTTPException as exc:
            raise GraphQLError(
                str(exc.detail), extensions={"code": exc.status_code}
            ) from exc
        except AppError as exc:
            raise GraphQLError(
                exc.message, extensions={"code": exc.status_code}
            ) from exc
        except pydantic.ValidationError as exc:
            # Same status code and same `.errors()` shape FastAPI's own
            # RequestValidationError handler returns under `detail` in REST
            # (see validation_exception_handler in app/main.py) — carried here
            # under extensions.errors so both transports can share one
            # frontend error-normalizer.
            raise GraphQLError(
                "Validation error", extensions={"code": 422, "errors": exc.errors()}
            ) from exc

    return wrapper
