from app.di.modules.healthcare_service import HealthcareServiceContainer
from app.di.modules.location import LocationContainer
from app.di.modules.organization import OrganizationContainer
from app.di.modules.patient import PatientContainer
from app.di.modules.practitioner import PractitionerContainer
from app.di.modules.practitioner_role import PractitionerRoleContainer
from app.di.modules.schedule import ScheduleContainer
from app.di.modules.slot import SlotContainer

__all__ = [
    "PatientContainer",
    "OrganizationContainer",
    "LocationContainer",
    "HealthcareServiceContainer",
    "PractitionerContainer",
    "PractitionerRoleContainer",
    "ScheduleContainer",
    "SlotContainer",
]
