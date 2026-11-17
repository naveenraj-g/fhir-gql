"""Per-resource wire translators for the epic connector."""

from app.connectors.epic.translators.location import EpicLocationTranslator
from app.connectors.epic.translators.organization import EpicOrganizationTranslator

__all__ = ["EpicLocationTranslator", "EpicOrganizationTranslator"]
