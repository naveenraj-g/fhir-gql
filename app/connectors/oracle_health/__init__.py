"""
Connector package for Oracle Health (Cerner Millennium) FHIR R4: Organization and
Location read, Organization create, with a configurable client_credentials login
(client secret or signed JWT). See client.py and token_manager.py.
"""

from app.connectors.oracle_health.client import OracleHealthConnector

__all__ = ["OracleHealthConnector"]
