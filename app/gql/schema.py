"""
Composes the GraphQL schema from per-domain Query/Mutation resolver mixins
and exposes it as a FastAPI-mountable router.

Organization, Location, and HealthcareService are the FHIR resources this
gateway exposes. All three are genuinely FHIR R4-shaped end-to-end (see
app.gql.organization's package docstring, which app.gql.location and
app.gql.healthcare_service both mirror exactly) — their resolvers call the
active connector directly and translate via
app.connectors.translator_registry.active_organization_translator()/
active_location_translator()/active_healthcare_service_translator(), keyed
off `settings.connectors.active`, rather than going through a per-resource
service/client layer.

Adding another resource means: write its `app/gql/<resource>/types/` +
`queries.py` + `mutations.py` (and, if it needs its own translation layer,
`app/connectors/<connector>/translators/<resource>.py` + a registry entry
in app.connectors.translator_registry — see app.gql.organization's package
docstring for the full pattern), then mix its Query/Mutation into the root
types below the same way FhirOrganizationQuery/FhirOrganizationMutation,
FhirLocationQuery/FhirLocationMutation, and
FhirHealthcareServiceQuery/FhirHealthcareServiceMutation are.

GraphQL is this service's only transport — there is no REST layer.
"""

import strawberry
from strawberry.fastapi import GraphQLRouter

from app.core.config import settings
from app.gql.context import get_context
from app.gql.healthcare_service.mutations import FhirHealthcareServiceMutation
from app.gql.healthcare_service.queries import FhirHealthcareServiceQuery
from app.gql.location.mutations import FhirLocationMutation
from app.gql.location.queries import FhirLocationQuery
from app.gql.logging import GqlLoggingExtension
from app.gql.organization.mutations import FhirOrganizationMutation
from app.gql.organization.queries import FhirOrganizationQuery
from app.gql.test_subscription import TestSubscription


@strawberry.type
class Query(FhirOrganizationQuery, FhirLocationQuery, FhirHealthcareServiceQuery):
    """Root GraphQL query type — merges every resource's query fields via
    mixin inheritance. Add a new resource's Query mixin here alongside
    `FhirOrganizationQuery`/`FhirLocationQuery`/`FhirHealthcareServiceQuery`
    as it's added."""


@strawberry.type
class Mutation(
    FhirOrganizationMutation, FhirLocationMutation, FhirHealthcareServiceMutation
):
    """Root GraphQL mutation type — merges every resource's mutation fields via mixin inheritance."""


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
