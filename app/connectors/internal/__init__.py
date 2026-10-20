"""
Connector package for *this application* — our own fhir-server. Named
"internal" rather than "fhir_server" — see client.py's module docstring
for why.

Per-connector packages (not single files) are this project's convention
going forward — the same "module outgrows one file -> same-named package"
move fhir-server's own CLAUDE.md documents for its schemas. internal/
holds only client.py today because its auth mode (see
configs/connectors/internal.yaml) is token passthrough, so it has no
separate token-acquisition module of its own. An OAuth-credential connector
(Epic, Cerner, ...) added later would likely need more than one file here
(e.g. a client.py plus a token-acquisition module) — see
dev-docs/17-static-architecture-and-generic-fhir-payloads.md.
"""

from app.connectors.internal.client import InternalConnector

__all__ = ["InternalConnector"]
