"""
The connector interface — the one seam between this gateway's resource
clients/services (app/fhir_client/*.py, app/services/*.py) and whatever
system actually stores the data.

Why this exists: every resource client (OrganizationClient, PatientClient,
...) and every service is written against four HTTP-shaped verbs — but
nothing about them actually depends on the *backend* being our own
fhir-server. They just need something that can POST/GET/PATCH/DELETE a path
and hand back a dict, inject actor identity, and translate a non-2xx
response into an HTTPException. `Connector` names that contract explicitly,
so a resource client's constructor can ask for "a connector" rather than
"our own fhir-server client" — any system satisfying this Protocol is a
legal caller, not just the one concrete implementation we have today.

Today there's exactly one connector: app.connectors.fhir_server.
FhirServerConnector, representing *this* application (our own fhir-server).
Which connector is active is a config choice — see app.connectors.registry
and configs/config.yaml's `connectors.active` — not something any resource
client or service ever needs to know about.

Adding a second connector (e.g. for Medplum, or any other FHIR-R4-shaped
EMR/EHR) later means: write a class satisfying this Protocol, register it
in app.connectors.registry.CONNECTORS, and set connectors.active — no
change to any resource client, service, or schema. Each connector owns its
own URL/path conventions internally (a real FHIR server's canonical REST
paths look nothing like fhir-server's own `/organizations`-style routes),
so the `path` a resource client passes in is only ever meaningful to
*that* connector — nothing above this interface should assume a specific
URL shape.

A `Protocol`, not an ABC: structural typing means FhirServerConnector
doesn't need to inherit from this class at all (and doesn't) — it just
needs to have these methods with these signatures. That keeps the concrete
connector free to also expose extra, connector-specific methods (as
FhirServerConnector does for its own error-detail extraction) without this
interface caring.
"""

from typing import Protocol

from app.auth.models import AuthUser


class Connector(Protocol):
    """Structural interface every connector must satisfy. See module
    docstring for the full rationale."""

    async def post(
        self,
        path: str,
        data: dict,
        actor: AuthUser,
        accept: str | None = None,
        inject_audit: bool = True,
    ) -> dict:
        """Create a resource at `path`."""
        ...

    async def get(
        self,
        path: str,
        params: dict | None = None,
        accept: str | None = None,
        actor: AuthUser | None = None,
    ) -> dict:
        """Read a resource or collection at `path`."""
        ...

    async def patch(
        self,
        path: str,
        data: dict,
        actor: AuthUser,
        accept: str | None = None,
        inject_audit: bool = True,
    ) -> dict:
        """Partially update the resource at `path`."""
        ...

    async def delete(self, path: str, actor: AuthUser | None = None) -> None:
        """Delete the resource at `path`."""
        ...

    async def aclose(self) -> None:
        """Release the connector's underlying connection pool at shutdown."""
        ...
