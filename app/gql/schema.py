"""
Composes the GraphQL schema from per-domain Query/Mutation resolver mixins
and exposes it as a FastAPI-mountable router.

Every resource's Query/Mutation mixin is imported directly from its own
`app/gql/<resource>/` package and mixed into the root Query/Mutation below.
Organization is genuinely FHIR R4-shaped end-to-end (see
app.gql.organization's package docstring) — its resolvers call the active
connector directly and translate via
app.connectors.translator_registry.active_organization_translator(), keyed
off `settings.connectors.active`, rather than going through a per-connector
service/client layer the way the other resources below do. That's an
internal implementation detail of app.gql.organization; from this module's
point of view it's mixed in exactly the same way as every other resource.

Adding a new resource to the GraphQL API means: write its
`app/gql/<resource>/types/` + `queries.py` + `mutations.py`, then add its
Query/Mutation mixin below.

GraphQL is this service's only transport — the REST routers that used to
live in app/routers/ have been removed (app/schemas/ stays; every type
below is still derived from those same Pydantic models, and REST can be
rebuilt on top of them again later if needed).
"""

import strawberry
from strawberry.fastapi import GraphQLRouter

from app.core.config import settings
from app.gql.context import get_context
from app.gql.healthcare_service.mutations import HealthcareServiceMutation
from app.gql.healthcare_service.queries import HealthcareServiceQuery
from app.gql.location.mutations import LocationMutation
from app.gql.location.queries import LocationQuery
from app.gql.logging import GqlLoggingExtension
from app.gql.organization.mutations import FhirOrganizationMutation
from app.gql.organization.queries import FhirOrganizationQuery
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
    FhirOrganizationQuery,
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
    inheritance: `FhirOrganizationQuery`, `PatientQuery`, `LocationQuery`,
    `HealthcareServiceQuery`, `PractitionerQuery`, `PractitionerRoleQuery`,
    `ScheduleQuery`, and `SlotQuery`. Add further resources' Query mixins
    here alongside them as they're added.
    """


@strawberry.type
class Mutation(
    FhirOrganizationMutation,
    PatientMutation,
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
