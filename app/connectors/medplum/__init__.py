"""
Connector package for Medplum — a genuinely FHIR-R4-compliant external
backend, registered (not active by default) as this project's reference
oauth_client_credentials connector. See client.py and token_manager.py's
module docstrings.
"""

from app.connectors.medplum.client import MedplumConnector

__all__ = ["MedplumConnector"]
