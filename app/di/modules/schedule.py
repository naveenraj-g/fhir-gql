"""
Dependency-injection sub-container for the Schedule domain.

The deepest cross-container fan-out yet: ScheduleService needs
PractitionerClient, PractitionerRoleClient, LocationClient,
HealthcareServiceClient, and PatientClient to validate its actor
references and derive service_category/service_type/specialty from
PractitionerRole/HealthcareService actors — see
app/services/schedule_service.py's docstring.
"""

from dependency_injector import containers, providers

from app.fhir_client.schedule import ScheduleClient
from app.services.schedule_service import ScheduleService


class ScheduleContainer(containers.DeclarativeContainer):
    """
    DI sub-container for the Schedule resource domain.

    Receives CoreContainer (via `core`), PractitionerContainer (via
    `practitioner`), PractitionerRoleContainer (via `practitioner_role`),
    LocationContainer (via `location`), HealthcareServiceContainer (via
    `healthcare_service`), and PatientContainer (via `patient`) from the
    root Container at wiring time.
    """

    core = providers.DependenciesContainer()
    practitioner = providers.DependenciesContainer()
    practitioner_role = providers.DependenciesContainer()
    location = providers.DependenciesContainer()
    healthcare_service = providers.DependenciesContainer()
    patient = providers.DependenciesContainer()

    # ScheduleClient wraps FhirClient with Schedule-specific paths.
    schedule_client = providers.Factory(
        ScheduleClient,
        fhir=core.fhir_client,
    )

    # ScheduleService owns all business logic for Schedule CRUD, including
    # actor validation, cardinality rules, and service field derivation.
    schedule_service = providers.Factory(
        ScheduleService,
        client=schedule_client,
        practitioner_client=practitioner.practitioner_client,
        practitioner_role_client=practitioner_role.practitioner_role_client,
        location_client=location.location_client,
        healthcare_service_client=healthcare_service.healthcare_service_client,
        patient_client=patient.patient_client,
    )
