"""
Per-connector translation for the Medplum connector, one module per
resource (organization.py, ... as more get added). See
app.connectors.base.OrganizationWireTranslator for the shared contract and
app.gql.organization's package docstring for the overall idea. Re-exported
here so existing imports
(`from app.connectors.medplum.translators import MedplumOrganizationTranslator`)
keep working unchanged regardless of which resource module a name lives in.
"""

from app.connectors.medplum.translators.organization import (
    MedplumOrganizationTranslator,
)

__all__ = ["MedplumOrganizationTranslator"]
