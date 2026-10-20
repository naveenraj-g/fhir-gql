"""
The connector interface — the one seam between this gateway's GraphQL
resolvers (app.gql.organization, ...) and whatever system actually stores
the data.

Why this exists: a resolver is written against four HTTP-shaped verbs —
but nothing about it actually depends on the *backend* being our own
fhir-server. It just needs something that can POST/GET/PATCH/DELETE a path
and hand back a dict, inject actor identity, and translate a non-2xx
response into an HTTPException. `Connector` names that contract explicitly,
so a resolver can ask for "a connector" rather than "our own fhir-server
client" — any system satisfying this Protocol is a legal caller, not just
the one concrete implementation we have today.

Today there are two connectors: app.connectors.internal.InternalConnector,
representing *this* application (our own fhir-server), and
app.connectors.medplum.MedplumConnector. Which connector is active is a
config choice — see app.connectors.registry and configs/config.yaml's
`connectors.active` — not something any resolver ever needs to know about.

Adding a second connector (e.g. for Epic, or any other FHIR-R4-shaped
EMR/EHR) means: write a class satisfying this Protocol, register it in
app.connectors.registry.CONNECTORS, and set connectors.active — no change
to any resolver. Each connector owns its own URL/path conventions
internally (a real FHIR server's canonical REST paths look nothing like
fhir-server's own `/organizations`-style routes), so the `path` a resolver
passes in (via its OrganizationWireTranslator, see below) is only ever
meaningful to *that* connector — nothing above this interface should
assume a specific URL shape.

A `Protocol`, not an ABC: structural typing means InternalConnector
doesn't need to inherit from this class at all (and doesn't) — it just
needs to have these methods with these signatures. That keeps the concrete
connector free to also expose extra, connector-specific methods (as
InternalConnector does for its own error-detail extraction) without this
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


class OrganizationWireTranslator(Protocol):
    """
    One connector's read/write wire conventions for the canonical FHIR R4
    Organization shape used by app.gql.organization (see that package's
    __init__.py docstring).

    Structural, same spirit as `Connector` above: each connector
    (app.connectors.internal, app.connectors.medplum, ...) implements this
    with its own class rather than inheriting from it. Which connector's
    translator is active is resolved by
    app.connectors.translator_registry.active_organization_translator(),
    keyed off the same `connectors.active` config value as `Connector`
    itself.

    Both of today's connectors already return genuine FHIR R4 JSON for
    reads — fhir-server via its own `Accept: application/fhir+json` content
    negotiation, Medplum natively — so `from_wire()` is identity for both.
    Writes are NOT symmetric with reads: fhir-server's POST/PATCH only ever
    accept their own flattened plain-JSON shape (see
    app.connectors.internal.translators.organization's module docstring for
    the exact field-level mapping), never genuine FHIR JSON, which is why
    there's a to_wire_create/to_wire_patch pair instead of one to_wire().
    """

    #: Accept header to request FHIR R4 shape from this backend, or None if
    #: the backend only ever speaks FHIR (nothing to negotiate).
    accept: str | None

    def item_path(self, organization_id: str) -> str:
        """Path for GET-by-id/PATCH/DELETE, in this backend's own convention."""
        ...

    def list_path(self) -> str:
        """Path for GET-collection (search) and POST-create, in this
        backend's own convention."""
        ...

    def list_params(
        self, name: str | None, active: bool | None, limit: int, offset: int
    ) -> dict:
        """Canonical filter/pagination args -> this backend's own query param names."""
        ...

    def from_wire(self, raw: dict) -> dict:
        """This backend's raw response dict -> canonical FHIR Organization
        (or Bundle) dict. Identity for both connectors today — see class
        docstring."""
        ...

    def to_wire_create(self, data: dict) -> dict:
        """Canonical FHIR Organization dict (from FhirOrganizationInput) ->
        this backend's own POST-create body shape."""
        ...

    def to_wire_patch(self, data: dict) -> dict:
        """Canonical FHIR Organization dict (from FhirOrganizationInput) ->
        this backend's own PATCH-update body shape."""
        ...
