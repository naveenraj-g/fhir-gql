"""
Maps `connectors.active` to that connector's own GraphQL Query/Mutation
mixins — the GraphQL counterpart of app.connectors.registry.CONNECTORS
(which maps the same key to the connector's HTTP implementation instead).

app.gql.schema.py uses this to compose the root Query/Mutation from
whichever connector is active, instead of importing every migrated
resource's mixin from a fixed location directly. Resources not yet
migrated into any connector's own package (Patient, Location, ...) are
still mixed into the root Query/Mutation directly in app/gql/schema.py —
this registry only covers resources that have moved into a connector
package, same as app.connectors.registry.CONNECTORS only covers backends
that have an actual Connector implementation.

Adding a second connector (e.g. Epic) means: build its own
app/connectors/epic/gql/ package the same way
app.connectors.internal.gql does, add `"epic": {"query": EpicQuery,
"mutation": EpicMutation}` below, and extend the `active` Literal in
app/core/config.py's ConnectorsConfig — app/gql/schema.py itself never
needs to change.
"""

from app.connectors.internal.gql import InternalMutation, InternalQuery

CONNECTOR_GQL = {
    "internal": {"query": InternalQuery, "mutation": InternalMutation},
}
