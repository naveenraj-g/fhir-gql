"""
Maps `connectors.active` (configs/config.yaml, read via app.core.config) to
the concrete Connector implementation it names.

This is the whole "pick a system to connect to" mechanism: app.di.core.
CoreContainer's `fhir_client` provider is a dependency_injector
`providers.Selector` keyed off `settings.connectors.active`, with one
branch per entry here. Everything above the connector (resource clients,
services) only ever sees the Connector Protocol (app.connectors.base) —
swapping which backend is live is one YAML edit, not a code change.

Adding a second connector (e.g. Medplum): write `app/connectors/medplum.py`
satisfying the Connector Protocol, add `"medplum": MedplumConnector` below,
and add `"medplum"` to ConnectorName's Literal in app/core/config.py.
"""

from app.connectors.fhir_server import FhirServerConnector

CONNECTORS = {
    # "This application" — our own fhir-server. See
    # app.connectors.fhir_server's module docstring.
    "fhir_server": FhirServerConnector,
}
