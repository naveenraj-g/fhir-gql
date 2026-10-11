"""
Scratch/demo Query and Subscription used to smoke-test the GraphQL WebSocket
transport in isolation from the real Patient resolvers — not part of the
actual API surface, just a place to verify subscriptions work end-to-end
(connection, auth, streaming) before wiring up a real one.
"""

import asyncio
from collections.abc import AsyncGenerator

import strawberry

from app.gql.permissions import authenticate_gql_subscription


@strawberry.type
class TestQuery:
    @strawberry.field
    def hello(self) -> str:
        return "world"


@strawberry.type
class TestSubscription:
    @strawberry.subscription
    async def count(
        self, info: strawberry.types.Info, target: int = 100
    ) -> AsyncGenerator[int]:
        """
        Yield 0..target-1, one value every 0.5s — a minimal streaming demo.

        Demonstrates the subscription auth pattern: authenticate_gql_permission()
        can't be used here (it reads request.state.user, which only exists for
        HTTP requests) — authenticate_gql_subscription() instead reads the
        token from info.context.connection_params, populated from the client's
        connection_init payload after the WebSocket is already open. See that
        function's docstring (app/gql/permissions.py) for the full reasoning.
        Requires `patient:read` purely to exercise the same permission the
        real Patient subscriptions will eventually need.
        """
        authenticate_gql_subscription(info, "patient", "read")
        for i in range(target):
            yield i
            await asyncio.sleep(0.5)
