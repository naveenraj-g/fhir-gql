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

Adding another resource's translator means: write
app/connectors/internal/translators/<resource>.py and
app/connectors/medplum/translators/<resource>.py the same way the
Organization/Location ones are written, then add a corresponding
`<RESOURCE>_TRANSLATORS = {...}` dict + `active_<resource>_translator()`
helper below — this module grows one resource at a time the same way
resource_registry.py does.
"""

from app.connectors.internal.translators import (
    InternalHealthcareServiceTranslator,
    InternalLocationTranslator,
    InternalOrganizationTranslator,
)
from app.connectors.medplum.translators import (
    MedplumHealthcareServiceTranslator,
    MedplumLocationTranslator,
    MedplumOrganizationTranslator,
)
from app.core.config import settings

ORGANIZATION_TRANSLATORS = {
    "internal": InternalOrganizationTranslator(),
    "medplum": MedplumOrganizationTranslator(),
}

LOCATION_TRANSLATORS = {
    "internal": InternalLocationTranslator(),
    "medplum": MedplumLocationTranslator(),
}

HEALTHCARE_SERVICE_TRANSLATORS = {
    "internal": InternalHealthcareServiceTranslator(),
    "medplum": MedplumHealthcareServiceTranslator(),
}


def active_organization_translator():
    """The Organization wire translator for whichever connector
    configs/config.yaml's `connectors.active` currently selects. Shared by
    both app.gql.organization.queries and .mutations."""
    return ORGANIZATION_TRANSLATORS[settings.connectors.active]


def active_location_translator():
    """The Location wire translator for whichever connector
    configs/config.yaml's `connectors.active` currently selects. Shared by
    both app.gql.location.queries and .mutations."""
    return LOCATION_TRANSLATORS[settings.connectors.active]


def active_healthcare_service_translator():
    """The HealthcareService wire translator for whichever connector
    configs/config.yaml's `connectors.active` currently selects. Shared by
    both app.gql.healthcare_service.queries and .mutations."""
    return HEALTHCARE_SERVICE_TRANSLATORS[settings.connectors.active]
