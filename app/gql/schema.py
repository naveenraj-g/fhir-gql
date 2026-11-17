"""
Composes the GraphQL schema from per-domain Query/Mutation resolver mixins
and exposes it as a FastAPI-mountable router.

Organization and Location are the FHIR resources this gateway exposes. Both
are genuinely FHIR R4-shaped end-to-end (see app.gql.organization's package
docstring, which app.gql.location mirrors exactly) — their resolvers call the
active connector directly and translate via
app.connectors.translator_registry.active_organization_translator()/
active_location_translator(), keyed off `settings.connectors.active`, rather
than going through a per-resource service/client layer.

Which resources are exposed is driven by configs/config.yaml's
`routes.enabled` (mirrors fhir-server). Adding another resource means: write
its `app/gql/<resource>/` package (+ translators, see app.gql.organization's
docstring), add an entry to RESOURCES below, and list its name in
`routes.enabled`.

GraphQL is this service's only transport — there is no REST layer.
"""

import importlib

import strawberry
from strawberry.fastapi import GraphQLRouter

from app.core.config import settings
from app.gql.context import get_context
from app.gql.logging import GqlLoggingExtension
from app.gql.test_subscription import TestQuery, TestSubscription

# resource name (as written in configs/config.yaml's routes.enabled) ->
# (package, Query mixin, Mutation mixin). Modules are imported lazily, only
# for enabled resources. Add a new resource here once its package exists.
RESOURCES: dict[str, tuple[str, str, str]] = {
    "organization": (
        "organization",
        "FhirOrganizationQuery",
        "FhirOrganizationMutation",
    ),
    "location": ("location", "FhirLocationQuery", "FhirLocationMutation"),
}


def _enabled_resources() -> list[str]:
    enabled = list(dict.fromkeys(settings.routes.enabled))
    unknown = [name for name in enabled if name not in RESOURCES]
    if unknown:
        raise RuntimeError(
            f"routes.enabled contains unknown resource(s) {unknown}; "
            f"valid names: {sorted(RESOURCES)}"
        )
    return enabled


def _compose(enabled: list[str]) -> tuple[type, type | None]:
    query_bases: list[type] = []
    mutation_bases: list[type] = []
    for name in enabled:
        package, query_name, mutation_name = RESOURCES[name]
        query_bases.append(
            getattr(importlib.import_module(f"app.gql.{package}.queries"), query_name)
        )
        mutation_bases.append(
            getattr(
                importlib.import_module(f"app.gql.{package}.mutations"), mutation_name
            )
        )

    # GraphQL requires a Query root with at least one field — TestQuery.hello
    # is always present so an empty routes.enabled still yields a valid schema.
    query = strawberry.type(
        type(
            "Query",
            (*query_bases, TestQuery),
            {"__doc__": "Root GraphQL query type — composed from routes.enabled."},
        )
    )
    mutation = (
        strawberry.type(
            type(
                "Mutation",
                tuple(mutation_bases),
                {
                    "__doc__": "Root GraphQL mutation type — composed from routes.enabled."
                },
            )
        )
        if mutation_bases
        else None
    )
    return query, mutation


Query, Mutation = _compose(_enabled_resources())


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
