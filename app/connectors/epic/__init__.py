"""
Connector package for Epic on FHIR (R4), read-only, authenticating with SMART
Backend Services (signed JWT). See client.py.
"""

from app.connectors.epic.client import EpicConnector

__all__ = ["EpicConnector"]
