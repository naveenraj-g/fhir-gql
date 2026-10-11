"""
Core infrastructure DI container — holds providers for shared, long-lived dependencies.

Providers in this container are declared as Singleton so that a single instance
is created on first access and reused for every subsequent injection. This is
important for the FHIR HTTP client because httpx.AsyncClient maintains an internal
connection pool — creating a new client per request would bypass pooling and
cause connection exhaustion under load.

This container is referenced by the root Container (app.di.container) and passed
into domain-level sub-containers so they can depend on the shared client without
importing it directly.
"""

from dependency_injector import containers, providers

from app.connectors.registry import CONNECTORS
from app.core.config import settings
from app.fhir_client.terminology import TerminologyClient


class CoreContainer(containers.DeclarativeContainer):
    """
    Provides shared infrastructure dependencies used across all domain containers.

    Holds process-scoped shared resources that should be constructed once and
    reused across all requests. Add new infrastructure clients here (not in domain
    containers) when they need connection-pool sharing.
    """

    # Singleton provider for the active connector (see app.connectors.base's
    # Connector Protocol and app.connectors.registry) — the one thing every
    # resource client (OrganizationClient, etc.) and service actually
    # depends on for I/O, named `fhir_client` for backward compatibility
    # with every existing `core.fhir_client` reference across the domain
    # containers below.
    #
    # providers.Selector picks the named branch matching
    # settings.connectors.active and constructs ONLY that one (the other
    # branches are never instantiated) — exactly the "config picks which
    # system to connect to" mechanism this is for. Each branch is itself a
    # Singleton, so dependency-injector still constructs it exactly once
    # and preserves its connection pool across requests. Adding a second
    # connector means adding another `providers.Singleton(...)` branch
    # here, keyed by that connector's registry name — nothing else in this
    # file changes.
    fhir_client = providers.Selector(
        lambda: settings.connectors.active,
        fhir_server=providers.Singleton(
            CONNECTORS["fhir_server"],
            base_url=settings.FHIR_SERVER_URL,
        ),
    )

    # Singleton provider for the Terminology HTTP client.
    # Terminology lives at a different base URL (/api/v1/terminology) from FHIR
    # resources (/api/fhir/v1), so it needs its own httpx client. Singleton keeps
    # the connection pool shared across all terminology requests. Not part of
    # the connector abstraction above — terminology is a fhir-server-specific
    # feature, not something every backend necessarily exposes the same way.
    terminology_client = providers.Singleton(
        TerminologyClient,
        base_url=settings.TERMINOLOGY_SERVER_URL,
    )
