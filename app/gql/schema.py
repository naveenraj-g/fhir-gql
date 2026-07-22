"""
Composes the GraphQL schema from per-domain Query/Mutation resolver mixins
and exposes it as a FastAPI-mountable router.

Adding a new resource to the GraphQL API means: write its
`app/gql/types/<resource>.py` + `app/gql/resolvers/<resource>.py`, then add
its Query/Mutation mixin below — this mirrors how `app/routers/__init__.py`
aggregates REST routers into one `api_router`.
"""

import strawberry
from strawberry.fastapi import GraphQLRouter

from app.config import settings
from app.gql.context import get_context
from app.gql.patient.mutations import PatientMutation
from app.gql.patient.queries import PatientQuery
from app.gql.test_subscription import TestSubscription


@strawberry.type
class Query(PatientQuery):
    """
    Root GraphQL query type — merges every domain's query fields via mixin
    inheritance. This patient-only slice mixes in `PatientQuery` (the real
    API) plus `PatientLazyQuery` (an EXAMPLE mixin demonstrating lazy/
    parallel/dependent resolver composition — see
    app/gql/examples/patient_lazy_resolvers.py). Add further resources' Query
    mixins here alongside them as they are ported over.
    """


@strawberry.type
class Mutation(PatientMutation):
    """Root GraphQL mutation type — merges every domain's mutation fields via mixin inheritance."""


@strawberry.type
class Subscription(TestSubscription):
    """"""


schema = strawberry.Schema(query=Query, mutation=Mutation, subscription=Subscription)

# GraphiQL (the in-browser IDE served on GET /graphql) is convenient for
# local/dev testing but disabled in production to avoid exposing schema
# introspection and a live query console publicly.
#
# allow_queries_via_get=False is required for auth correctness, not just
# style: with it left at Strawberry's default (True), a client could send a
# full GraphQL operation as `GET /graphql?query=...`. Auth is enforced inside
# get_context() (see app/gql/context.py) rather than as a router-level
# FastAPI dependency, specifically so the bare GraphiQL HTML/JS shell can
# still load without an Authorization header — a browser navigating to
# GET /graphql cannot attach one. If GET could also execute operations,
# that path would bypass auth entirely.
graphql_router = GraphQLRouter(
    schema,
    context_getter=get_context,
    graphql_ide="graphiql" if settings.ENVIRONMENT != "production" else None,
    allow_queries_via_get=False,
)
