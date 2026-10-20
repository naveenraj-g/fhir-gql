"""
Aggregates every resource's GraphQL Query/Mutation mixin exposed by the
internal connector (this application's own fhir-server) into one pair of
classes.

This exists so app/gql/schema.py can pull in "whichever connector is
active" as a single import (via app.connectors.gql_registry.CONNECTOR_GQL)
instead of importing every resource's mixin from a fixed, connector-
specific location directly. Only Organization lives here today — as
Location, Patient, etc. are migrated into this connector's own package the
same way (see app.connectors.internal.clients/schemas/services), their
Query/Mutation mixins get added to the inheritance list below, and
app/gql/schema.py doesn't need to change at all.

Every mixin here is itself a `@strawberry.type` (see
app.connectors.internal.gql.organization.queries.OrganizationQuery) —
Strawberry supports composing types via ordinary Python multiple
inheritance, which is exactly what app/gql/schema.py already does one
level up to merge every resource into the root Query/Mutation. This is the
same composition, one layer earlier, scoped to one connector's resources.
"""

import strawberry

from app.connectors.internal.gql.organization.mutations import OrganizationMutation
from app.connectors.internal.gql.organization.queries import OrganizationQuery


@strawberry.type(
    description="Query fields for every resource the internal connector (this application's own fhir-server) exposes."
)
class InternalQuery(OrganizationQuery):
    """Root query mixin for the internal connector. Extend with further
    resources' Query mixins (comma-separated in the inheritance list) as
    they migrate into app.connectors.internal."""


@strawberry.type(
    description="Mutation fields for every resource the internal connector (this application's own fhir-server) exposes."
)
class InternalMutation(OrganizationMutation):
    """Root mutation mixin for the internal connector. Extend with further
    resources' Mutation mixins as they migrate into app.connectors.internal."""
