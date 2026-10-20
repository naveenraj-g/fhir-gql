"""
EXPERIMENTAL — a second, independent GraphQL schema + router proving out
"one universal, FHIR R4-shaped GraphQL schema, with per-connector
translation", as an alternative to this project's existing per-connector
GQL architecture. See app.connectors.universal's package docstring.

Deliberately NOT mixed into the main Query/Mutation in app/gql/schema.py —
this is its own strawberry.Schema, mounted at its own path (see
app/main.py), so it can be evaluated side-by-side with the existing
architecture without touching it at all. Organization only, for now — see
dev-docs/18-universal-fhir-graphql-experiment.md.
"""

import strawberry
from strawberry.fastapi import GraphQLRouter

from app.connectors.universal.gql.mutations import FhirOrganizationMutation
from app.connectors.universal.gql.queries import FhirOrganizationQuery
from app.core.config import settings
from app.gql.context import get_context


@strawberry.type
class Query(FhirOrganizationQuery):
    """Root query type for the universal-FHIR-GraphQL experiment — Organization only, for now."""


@strawberry.type
class Mutation(FhirOrganizationMutation):
    """Root mutation type for the universal-FHIR-GraphQL experiment — Organization only, for now."""


schema = strawberry.Schema(query=Query, mutation=Mutation)

# Same auth/IDE semantics as the main /graphql endpoint — see
# app/gql/schema.py's graphql_router for the full rationale (reused
# unchanged here, not reimplemented).
graphql_router = GraphQLRouter(
    schema,
    context_getter=get_context,
    graphql_ide="graphiql" if settings.ENVIRONMENT != "production" else None,
    allow_queries_via_get=False,
)
