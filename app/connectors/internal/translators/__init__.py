"""
Per-connector translation for the internal (this application's own
fhir-server) connector, one module per resource (organization.py, ... as
more get added). See app.connectors.base.OrganizationWireTranslator for the
shared contract and app.gql.organization's package docstring for the
overall idea. Re-exported here so existing imports
(`from app.connectors.internal.translators import InternalOrganizationTranslator`)
keep working unchanged regardless of which resource module a name lives in.
"""

from app.connectors.internal.translators.organization import (
    InternalOrganizationTranslator,
)

__all__ = ["InternalOrganizationTranslator"]
