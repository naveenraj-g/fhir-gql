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
    ├── core              →  CoreContainer          (shared infrastructure: FHIR HTTP client)
    ├── patient           →  PatientContainer       (Patient CRUD + 9 sub-resource clients)
    ├── organization      →  OrganizationContainer  (Organization CRUD)
    ├── location          →  LocationContainer      (Location CRUD; also depends on `organization`
    │                                                 for managing_organization reference validation)
    ├── healthcare_service →  HealthcareServiceContainer (HealthcareService CRUD; also depends on
    │                                            `organization` and `location` for provided_by/
    │                                            location/coverage_area reference validation)
    ├── practitioner       →  PractitionerContainer (Practitioner CRUD + 7 sub-resource clients;
    │                                            also depends on `organization` for
    │                                            qualification.issuer reference validation)
    ├── practitioner_role  →  PractitionerRoleContainer (PractitionerRole CRUD; depends on
    │                                            `practitioner`, `organization`, `location`, and
    │                                            `healthcare_service` for its four cross-resource
    │                                            reference validations)
    ├── schedule           →  ScheduleContainer (Schedule CRUD; depends on `practitioner`,
    │                                            `practitioner_role`, `location`,
    │                                            `healthcare_service`, and `patient` to validate
    │                                            actor references and derive service_category/
    │                                            service_type/specialty)
    └── slot               →  SlotContainer (Slot CRUD + availability-aware bulk generation;
                                                 depends on `schedule` and `practitioner_role`)

Additional resources (encounter, ...) can be added the same way Patient,
Organization, Location, HealthcareService, Practitioner, PractitionerRole,
Schedule, and Slot were: a new app/di/modules/<resource>.py container,
wired here with `core=core` (plus any sibling sub-container it needs
directly, as Location needs `organization`, HealthcareService needs both
`organization` and `location`, Practitioner needs `organization`,
PractitionerRole needs `practitioner`+`organization`+`location`+`healthcare_service`,
Schedule needs `practitioner`+`practitioner_role`+`location`+`healthcare_service`+`patient`,
and Slot needs `schedule`+`practitioner_role`), then added to
app/routers/__init__.py and app/gql/schema.py.
"""

from dependency_injector import containers, providers

from app.di.core import CoreContainer
from app.di.modules import (
    HealthcareServiceContainer,
    LocationContainer,
    OrganizationContainer,
    PatientContainer,
    PractitionerContainer,
    PractitionerRoleContainer,
    ScheduleContainer,
    SlotContainer,
)


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

    # Domain container for Organization resources.
    organization = providers.Container(
        OrganizationContainer,
        core=core,
    )

    # Domain container for Location resources. Must be declared after
    # `organization` above since it references that provider by name —
    # LocationService validates managing_organization references via
    # OrganizationClient (see app/di/modules/location.py).
    location = providers.Container(
        LocationContainer,
        core=core,
        organization=organization,
    )

    # Domain container for HealthcareService resources. Must be declared
    # after both `organization` and `location` above since it references
    # both providers by name — HealthcareServiceService validates
    # provided_by (Organization) and location/coverage_area (Location)
    # references (see app/di/modules/healthcare_service.py).
    healthcare_service = providers.Container(
        HealthcareServiceContainer,
        core=core,
        organization=organization,
        location=location,
    )

    # Domain container for Practitioner resources. Must be declared after
    # `organization` above since it references that provider by name —
    # PractitionerService validates qualification.issuer references via
    # OrganizationClient (see app/di/modules/practitioner.py).
    practitioner = providers.Container(
        PractitionerContainer,
        core=core,
        organization=organization,
    )

    # Domain container for PractitionerRole resources. Must be declared
    # after `practitioner`, `organization`, `location`, and
    # `healthcare_service` above since it references all four providers by
    # name — PractitionerRoleService validates practitioner/organization/
    # location/healthcare_service references (see
    # app/di/modules/practitioner_role.py).
    practitioner_role = providers.Container(
        PractitionerRoleContainer,
        core=core,
        practitioner=practitioner,
        organization=organization,
        location=location,
        healthcare_service=healthcare_service,
    )

    # Domain container for Schedule resources. Must be declared last —
    # it references `practitioner`, `practitioner_role`, `location`,
    # `healthcare_service`, and `patient` by name — ScheduleService
    # validates actor references against all five and derives
    # service_category/service_type/specialty from the PractitionerRole/
    # HealthcareService actors (see app/di/modules/schedule.py).
    schedule = providers.Container(
        ScheduleContainer,
        core=core,
        practitioner=practitioner,
        practitioner_role=practitioner_role,
        location=location,
        healthcare_service=healthcare_service,
        patient=patient,
    )

    # Domain container for Slot resources. Must be declared after
    # `schedule` and `practitioner_role` above since it references both
    # providers by name — SlotService validates `schedule` references and
    # reads the Schedule's PractitionerRole actor's availability for
    # generate() (see app/di/modules/slot.py).
    slot = providers.Container(
        SlotContainer,
        core=core,
        schedule=schedule,
        practitioner_role=practitioner_role,
    )
