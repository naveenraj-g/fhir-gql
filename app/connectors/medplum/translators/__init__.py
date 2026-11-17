"""
Per-connector translation for the medplum connector, one module per
resource (organization.py, location.py). See
app.connectors.base.OrganizationWireTranslator/LocationWireTranslator for
the shared contracts and app.gql.organization's package docstring for the
overall idea. Re-exported here so existing imports
(`from app.connectors.medplum.translators import MedplumOrganizationTranslator`)
keep working unchanged regardless of which resource module a name lives in.
"""

from app.connectors.medplum.translators.location import MedplumLocationTranslator
from app.connectors.medplum.translators.organization import (
    MedplumOrganizationTranslator,
)

__all__ = [
    "MedplumLocationTranslator",
    "MedplumOrganizationTranslator",
]
