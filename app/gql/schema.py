"""
Composes the GraphQL schema from per-domain Query/Mutation resolver mixins
and exposes it as a FastAPI-mountable router.

Resources that have migrated into a connector's own package (see
app.connectors.internal.gql — Organization today) are pulled in via
app.connectors.gql_registry.CONNECTOR_GQL, keyed off
`settings.connectors.active`, rather than imported directly here — that's
what makes the active connector's GraphQL surface swap in "dynamically"
(at startup, from config, same as app.connectors.registry.CONNECTORS
already does for the HTTP side) rather than always being the same fixed
set of resource modules. Resources not yet migrated into any connector
package (Patient, Location, ...) are still mixed in directly below, the
same as before — add a resource to CONNECTOR_GQL once it moves, and remove
its direct mixin here.

Adding a new, not-yet-migrated resource to the GraphQL API means: write its
`app/gql/types/<resource>.py` + `app/gql/resolvers/<resource>.py`, then add
its Query/Mutation mixin below.

GraphQL is this service's only transport — the REST routers that used to
live in app/routers/ have been removed (app/schemas/ stays; every type
below is still derived from those same Pydantic models, and REST can be
rebuilt on top of them again later if needed).
"""

import strawberry
from strawberry.fastapi import GraphQLRouter

from app.connectors.gql_registry import CONNECTOR_GQL
from app.core.config import settings
from app.gql.context import get_context
from app.gql.healthcare_service.mutations import HealthcareServiceMutation
from app.gql.healthcare_service.queries import HealthcareServiceQuery
from app.gql.location.mutations import LocationMutation
from app.gql.location.queries import LocationQuery
from app.gql.logging import GqlLoggingExtension
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

# The active connector's own Query/Mutation mixin (today: InternalQuery/
# InternalMutation, covering Organization) — see module docstring.
_active_connector_gql = CONNECTOR_GQL[settings.connectors.active]
_ActiveConnectorQuery = _active_connector_gql["query"]
_ActiveConnectorMutation = _active_connector_gql["mutation"]


@strawberry.type
class Query(
    _ActiveConnectorQuery,
    PatientQuery,
    LocationQuery,
    HealthcareServiceQuery,
    PractitionerQuery,
    PractitionerRoleQuery,
    ScheduleQuery,
    SlotQuery,
):
    """
    Root GraphQL query type — merges every domain's query fields via mixin
    inheritance. Mixes in the active connector's own Query mixin (today
    `InternalQuery`, covering Organization — see
    app.connectors.gql_registry), plus `PatientQuery`, `LocationQuery`,
    `HealthcareServiceQuery`, `PractitionerQuery`, `PractitionerRoleQuery`,
    `ScheduleQuery`, and `SlotQuery` (not yet migrated into a connector
    package) and `PatientLazyQuery` (an EXAMPLE mixin demonstrating
    lazy/parallel/dependent resolver composition — see
    app/gql/examples/patient_lazy_resolvers.py). Add further resources'
    Query mixins here alongside them as they are ported over, until they
    too migrate into a connector package.
    """


@strawberry.type
class Mutation(
    _ActiveConnectorMutation,
    PatientMutation,
    LocationMutation,
    HealthcareServiceMutation,
    PractitionerMutation,
    PractitionerRoleMutation,
    ScheduleMutation,
    SlotMutation,
):
    """Root GraphQL mutation type — merges every domain's mutation fields via mixin inheritance. See Query's docstring for the same connector-vs-not-yet-migrated split."""


@strawberry.type
class Subscription(TestSubscription):
    """"""


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
    # One log line per operation — see app/gql/logging.py's docstring.
    extensions=[GqlLoggingExtension],
)

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
