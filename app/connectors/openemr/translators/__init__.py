"""Per-resource wire translators for the openemr connector."""

from app.connectors.openemr.translators.location import OpenEmrLocationTranslator
from app.connectors.openemr.translators.organization import (
    OpenEmrOrganizationTranslator,
)

__all__ = ["OpenEmrLocationTranslator", "OpenEmrOrganizationTranslator"]
