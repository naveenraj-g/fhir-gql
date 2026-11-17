"""
Connector package for Medplum — a genuinely FHIR-R4-compliant external
backend, registered (not active by default) as this project's reference
client-credentials connector. See client.py and app/connectors/token_manager.py's
module docstrings.
"""

from app.connectors.medplum.client import MedplumConnector

__all__ = ["MedplumConnector"]
