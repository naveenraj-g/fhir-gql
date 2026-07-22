"""
Root dependency-injection container for the entire application.

This module defines the top-level `Container` class using the dependency-injector
library's declarative container pattern. It acts as the composition root — every
service, repository, and client in the application is wired here so that:
  - Dependencies are assembled once at startup rather than on every request.
  - The dependency graph is explicit and testable: replacing a provider (e.g. with
    a mock) requires changing one line here rather than hunting call sites.
  - FastAPI route handlers receive pre-built service instances via Depends() without
    knowing how those instances are constructed.

Wiring:
    WiringConfiguration(packages=["app"]) tells dependency-injector to scan every
    module under the `app` package at startup and inject providers wherever it finds
    the @inject decorator combined with Provide[Container.*] type hints. This avoids
    manually listing every injected module.

Container hierarchy:
    Container (root)
    ├── core    →  CoreContainer     (shared infrastructure: FHIR HTTP client)
    └── patient →  PatientContainer  (Patient CRUD + 9 sub-resource clients)

This is a patient-only slice of the full fhir-gql middleware — see README.md.
Additional resources (organization, encounter, ...) can be added the same way
Patient was: a new app/di/modules/<resource>.py container, wired here with
`core=core`, then added to app/routers/__init__.py and app/gql/schema.py.
"""

from dependency_injector import containers, providers

from app.di.core import CoreContainer
from app.di.modules import PatientContainer


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

    # Shared infrastructure container — holds the singleton FHIR HTTP client.
    core = providers.Container(CoreContainer)

    # Domain container for Patient resources.
    # A Patient is a person receiving care or other health-related services.
    # Includes sub-resource clients for names, identifiers, telecom, addresses,
    # photos, contacts, communications, general practitioners, and links.
    patient = providers.Container(
        PatientContainer,
        core=core,
    )
