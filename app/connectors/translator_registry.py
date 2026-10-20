"""
Maps `connectors.active` to that connector's own Organization wire
translator — the translation-layer counterpart of
app.connectors.registry.CONNECTORS (the connector's base HTTP
implementation) and app.connectors.resource_registry.CONNECTOR_RESOURCES
(its per-resource client/service classes).

app.gql.organization's queries/mutations use this to pick the right
translator for the currently active connector instead of importing one
connector's translator from a fixed location directly — see
app.connectors.base.OrganizationWireTranslator for the shared contract.

Adding a second resource's translator (e.g. Location) means: write
app/connectors/internal/translators/location.py and
app/connectors/medplum/translators/location.py the same way the
Organization ones are written, then add a second
`LOCATION_TRANSLATORS = {...}` dict + `active_location_translator()` helper
below — this module grows one resource at a time the same way
resource_registry.py does.
"""

from app.connectors.internal.translators import InternalOrganizationTranslator
from app.connectors.medplum.translators import MedplumOrganizationTranslator
from app.core.config import settings

ORGANIZATION_TRANSLATORS = {
    "internal": InternalOrganizationTranslator(),
    "medplum": MedplumOrganizationTranslator(),
}


def active_organization_translator():
    """The Organization wire translator for whichever connector
    configs/config.yaml's `connectors.active` currently selects. Shared by
    both app.gql.organization.queries and .mutations."""
    return ORGANIZATION_TRANSLATORS[settings.connectors.active]
