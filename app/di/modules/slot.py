"""
Dependency-injection sub-container for the Slot domain.

SlotService needs ScheduleClient (to validate `schedule` references, read
planning_horizon/actor data, and default service_category/service_type/
specialty) and PractitionerRoleClient (to read the Schedule's provider
actor's availability for generate()) — see
app/services/slot_service.py's docstring.
"""

from dependency_injector import containers, providers

from app.fhir_client.slot import SlotClient
from app.services.slot_service import SlotService


class SlotContainer(containers.DeclarativeContainer):
    """
    DI sub-container for the Slot resource domain.

    Receives CoreContainer (via `core`), ScheduleContainer (via
    `schedule`), and PractitionerRoleContainer (via `practitioner_role`)
    from the root Container at wiring time.
    """

    core = providers.DependenciesContainer()
    schedule = providers.DependenciesContainer()
    practitioner_role = providers.DependenciesContainer()

    # SlotClient wraps FhirClient with Slot-specific paths.
    slot_client = providers.Factory(
        SlotClient,
        fhir=core.fhir_client,
    )

    # SlotService owns all business logic for Slot CRUD and availability-aware generation.
    slot_service = providers.Factory(
        SlotService,
        client=slot_client,
        schedule_client=schedule.schedule_client,
        practitioner_role_client=practitioner_role.practitioner_role_client,
    )
