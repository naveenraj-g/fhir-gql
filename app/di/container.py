"""
Root dependency-injection container for the entire application.

This module defines the top-level `Container` class using the dependency-injector
library's declarative container pattern. It acts as the composition root.

Wiring:
    WiringConfiguration(packages=["app"]) tells dependency-injector to scan every
    module under the `app` package at startup and inject providers wherever it finds
    the @inject decorator combined with Provide[Container.*] type hints. This avoids
    manually listing every injected module.

Container hierarchy:
    Container (root)
    └── core  →  CoreContainer  (shared infrastructure: the active connector's
                 FHIR HTTP client, and the Terminology HTTP client)

Organization is the only FHIR resource this gateway exposes, and its
GraphQL resolvers (app.gql.organization) don't need a domain sub-container
of their own — they call `core.fhir_client()` directly and translate via
app.connectors.translator_registry.active_organization_translator(), with
no per-resource client/service layer in between. A future resource added
the same way needs no new sub-container either, unless it has real
orchestration logic (validation, cross-resource lookups, ...) that doesn't
belong in a GraphQL resolver — in that case, add a
`providers.Container(...)` the same way the old per-resource containers
used to be wired here, with `core=core` plus any sibling sub-container it
needs directly.
"""

from dependency_injector import containers, providers

from app.di.core import CoreContainer


class Container(containers.DeclarativeContainer):
    """
    Application-wide DI container. Instantiated once in app.main and attached to
    `app.container` so it survives for the full process lifetime.

    Sub-containers are declared as `providers.Container(...)` which creates a
    lazily-initialised child container. Passing `core=core` to each domain container
    wires the shared CoreContainer instance into the child so its providers
    (e.g. fhir_client) can be referenced via `core.fhir_client` inside the child.
    """

    # Scans all modules under the `app` package for @inject-decorated functions
    # and automatically resolves their Provide[Container.*] dependencies at startup.
    wiring_config = containers.WiringConfiguration(packages=["app"])

    # Shared infrastructure container — holds the singleton FHIR HTTP client
    # (the active connector) and the Terminology HTTP client.
    core = providers.Container(CoreContainer)
