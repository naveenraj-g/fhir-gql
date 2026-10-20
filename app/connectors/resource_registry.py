"""
Maps `connectors.active` to that connector's own per-resource client and
service classes — the DI counterpart of app.connectors.registry.CONNECTORS
(the connector's base HTTP implementation) and
app.connectors.translator_registry.ORGANIZATION_TRANSLATORS (its GraphQL
wire-translation surface).

DI modules (app/di/modules/<resource>.py) and any service that needs
another resource's client directly (e.g. PractitionerService needing
OrganizationClient) read this instead of importing a resource's
client/service from a fixed connector-specific location — so swapping
connectors.active also swaps which client/service implementation backs
each resource, not just which GraphQL schema is composed (gql_registry.py)
or which base connector is live (registry.py).

Only Organization is registered today. Adding a resource to a connector
package means adding its own {"client": ..., "service": ...} entry under
that connector's key below — the DI module and any cross-resource caller
look it up by resource name, never branching on the connector themselves.
"""

from app.connectors.internal.clients.organization import OrganizationClient
from app.connectors.internal.services.organization_service import OrganizationsService

CONNECTOR_RESOURCES = {
    "internal": {
        "organization": {
            "client": OrganizationClient,
            "service": OrganizationsService,
        },
    },
}
