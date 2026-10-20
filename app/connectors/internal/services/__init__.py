"""
Per-resource business-logic services for the internal connector (this
application's own fhir-server). One module per resource, each owning
validation/orchestration on top of that resource's client
(app.connectors.internal.clients) — see organization_service.py for the
pattern.
"""
