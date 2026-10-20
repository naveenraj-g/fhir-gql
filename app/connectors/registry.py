"""
Maps `connectors.active` (configs/config.yaml, read via app.core.config) to
the concrete Connector implementation it names.

This is the whole "pick a system to connect to" mechanism: app.di.core.
CoreContainer's `fhir_client` provider is a dependency_injector
`providers.Selector` keyed off `settings.connectors.active`, with one
branch per entry here. Everything above the connector (resource clients,
services) only ever sees the Connector Protocol (app.connectors.base) —
swapping which backend is live is one YAML edit, not a code change.

Adding a second connector (e.g. Medplum): write `app/connectors/medplum/`
(a package, not a single file — see app.connectors.internal's module
docstring) satisfying the Connector Protocol, add
`"medplum": MedplumConnector` below, add `"medplum"` to the `active`
Literal in app/core/config.py's ConnectorsConfig, and add its own
`configs/connectors/medplum.yaml` for checked-in behavior (auth_mode,
etc. — see InternalConnectorConfig for the pattern; real secrets like
client_id/secret are env vars, never committed YAML).
"""

from app.connectors.internal import InternalConnector
from app.connectors.medplum import MedplumConnector

CONNECTORS = {
    # "This application" — our own fhir-server. Named "internal" (not
    # "fhir_server") because every other connector is *also* a FHIR server
    # in the generic sense — what actually distinguishes this one is that
    # it's our own, first-party backend. See
    # app.connectors.internal's module docstring.
    "internal": InternalConnector,
    # A genuinely FHIR-R4-compliant external backend, authenticating via
    # OAuth2 client_credentials rather than internal's token_passthrough —
    # see app.connectors.medplum's module docstring. Registered here but
    # not active by default (see ConnectorsConfig.active's default).
    "medplum": MedplumConnector,
}
