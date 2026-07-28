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
from app.gql.healthcare_service.mutations import HealthcareServiceMutation
from app.gql.healthcare_service.queries import HealthcareServiceQuery
from app.gql.location.mutations import LocationMutation
from app.gql.location.queries import LocationQuery
from app.gql.organization.mutations import OrganizationMutation
from app.gql.organization.queries import OrganizationQuery
from app.gql.patient.mutations import PatientMutation
from app.gql.patient.queries import PatientQuery
from app.gql.practitioner.mutations import PractitionerMutation
from app.gql.practitioner.queries import PractitionerQuery
from app.gql.practitioner_role.mutations import PractitionerRoleMutation
from app.gql.practitioner_role.queries import PractitionerRoleQuery
from app.gql.schedule.mutations import ScheduleMutation
from app.gql.schedule.queries import ScheduleQuery
from app.gql.slot.mutations import SlotMutation
from app.gql.slot.queries import SlotQuery
from app.gql.test_subscription import TestSubscription


@strawberry.type
class Query(
    PatientQuery,
    OrganizationQuery,
    LocationQuery,
    HealthcareServiceQuery,
    PractitionerQuery,
    PractitionerRoleQuery,
    ScheduleQuery,
    SlotQuery,
):
    """
    Root GraphQL query type — merges every domain's query fields via mixin
    inheritance. Mixes in `PatientQuery`, `OrganizationQuery`,
    `LocationQuery`, `HealthcareServiceQuery`, `PractitionerQuery`,
    `PractitionerRoleQuery`, `ScheduleQuery`, and `SlotQuery` (the real
    APIs) plus `PatientLazyQuery` (an EXAMPLE mixin demonstrating
    lazy/parallel/dependent resolver composition — see
    app/gql/examples/patient_lazy_resolvers.py). Add further resources'
    Query mixins here alongside them as they are ported over.
    """


@strawberry.type
class Mutation(
    PatientMutation,
    OrganizationMutation,
    LocationMutation,
    HealthcareServiceMutation,
    PractitionerMutation,
    PractitionerRoleMutation,
    ScheduleMutation,
    SlotMutation,
):
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
