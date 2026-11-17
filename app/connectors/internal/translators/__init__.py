"""
Per-connector translation for the internal connector, one module per
resource (organization.py, location.py). See
app.connectors.base.OrganizationWireTranslator/LocationWireTranslator for
the shared contracts and app.gql.organization's package docstring for the
overall idea. Re-exported here so existing imports
(`from app.connectors.internal.translators import InternalOrganizationTranslator`)
keep working unchanged regardless of which resource module a name lives in.
"""

from app.connectors.internal.translators.location import InternalLocationTranslator
from app.connectors.internal.translators.organization import (
    InternalOrganizationTranslator,
)

__all__ = [
    "InternalLocationTranslator",
    "InternalOrganizationTranslator",
]
