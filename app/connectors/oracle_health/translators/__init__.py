"""Per-resource wire translators for the oracle_health connector."""

from app.connectors.oracle_health.translators.location import (
    OracleHealthLocationTranslator,
)
from app.connectors.oracle_health.translators.organization import (
    OracleHealthOrganizationTranslator,
)

__all__ = ["OracleHealthLocationTranslator", "OracleHealthOrganizationTranslator"]
