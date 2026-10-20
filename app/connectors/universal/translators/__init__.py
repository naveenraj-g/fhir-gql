"""
Per-connector, per-resource translation for the universal-FHIR-GraphQL
experiment, one module per resource (organization.py, ... as more get
added) — see app.connectors.universal's package docstring for the overall
idea. Re-exported here so existing imports
(`from app.connectors.universal.translators import active_organization_translator`,
etc.) keep working unchanged regardless of which resource module a name
lives in.
"""

from app.connectors.universal.translators.organization import (
    ORGANIZATION_TRANSLATORS,
    InternalOrganizationTranslator,
    MedplumOrganizationTranslator,
    OrganizationWireTranslator,
    active_organization_translator,
)

__all__ = [
    "ORGANIZATION_TRANSLATORS",
    "InternalOrganizationTranslator",
    "MedplumOrganizationTranslator",
    "OrganizationWireTranslator",
    "active_organization_translator",
]
