"""
Per-resource HTTP clients for the internal connector (this application's
own fhir-server). One module per resource, each a thin wrapper around the
shared Connector (app.connectors.base) that knows that resource's own
fhir-server path — see organization.py for the pattern.
"""
