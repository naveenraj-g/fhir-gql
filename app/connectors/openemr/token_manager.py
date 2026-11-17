"""OpenEMR's token manager is the shared SMART Backend Services one - see
app.connectors.smart_backend for how the signed-JWT login works."""

from app.connectors.smart_backend import SmartBackendTokenManager as OpenEmrTokenManager

__all__ = ["OpenEmrTokenManager"]
