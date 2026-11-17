"""
Maps `connectors.active` to that connector's own wire translator for each
resource — the translation-layer counterpart of
app.connectors.registry.CONNECTORS (the connector's base HTTP
implementation).

app.gql.organization / app.gql.location queries and mutations use this to
pick the right translator for the currently active connector instead of
importing one connector's translator from a fixed location directly — see
app.connectors.base.OrganizationWireTranslator / LocationWireTranslator for
the shared contracts.

Adding another resource's translator means: write
app/connectors/internal/translators/<resource>.py and
app/connectors/medplum/translators/<resource>.py the same way the
Organization/Location ones are written, then add a corresponding
`<RESOURCE>_TRANSLATORS = {...}` dict + `active_<resource>_translator()`
helper below.
"""

from app.connectors.epic.translators import (
    EpicLocationTranslator,
    EpicOrganizationTranslator,
)
from app.connectors.internal.translators import (
    InternalLocationTranslator,
    InternalOrganizationTranslator,
)
from app.connectors.medplum.translators import (
    MedplumLocationTranslator,
    MedplumOrganizationTranslator,
)
from app.connectors.openemr.translators import (
    OpenEmrLocationTranslator,
    OpenEmrOrganizationTranslator,
)
from app.connectors.oracle_health.translators import (
    OracleHealthLocationTranslator,
    OracleHealthOrganizationTranslator,
)
from app.core.config import settings

ORGANIZATION_TRANSLATORS = {
    "internal": InternalOrganizationTranslator(),
    "medplum": MedplumOrganizationTranslator(),
    "openemr": OpenEmrOrganizationTranslator(),
    "epic": EpicOrganizationTranslator(),
    "oracle_health": OracleHealthOrganizationTranslator(),
}

LOCATION_TRANSLATORS = {
    "internal": InternalLocationTranslator(),
    "medplum": MedplumLocationTranslator(),
    "openemr": OpenEmrLocationTranslator(),
    "epic": EpicLocationTranslator(),
    "oracle_health": OracleHealthLocationTranslator(),
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
