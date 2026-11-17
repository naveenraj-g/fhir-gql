"""
Connector package for OpenEMR's standard FHIR R4 API, authenticating with
OAuth2 client_credentials and a signed JWT (system scopes). See client.py and
token_manager.py.
"""

from app.connectors.openemr.client import OpenEmrConnector

__all__ = ["OpenEmrConnector"]
