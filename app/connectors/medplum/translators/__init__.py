"""
Per-connector translation for the Medplum connector, one module per
resource (organization.py, location.py, healthcare_service.py, ... as more
get added). See
app.connectors.base.OrganizationWireTranslator/LocationWireTranslator/
HealthcareServiceWireTranslator for the shared contracts and
app.gql.organization's package docstring for the overall idea. Re-exported
here so existing imports
(`from app.connectors.medplum.translators import MedplumOrganizationTranslator`)
keep working unchanged regardless of which resource module a name lives in.
"""

from app.connectors.medplum.translators.appointment import (
    MedplumAppointmentTranslator,
)
from app.connectors.medplum.translators.appointment_response import (
    MedplumAppointmentResponseTranslator,
)
from app.connectors.medplum.translators.diagnostic_report import (
    MedplumDiagnosticReportTranslator,
)
from app.connectors.medplum.translators.encounter import MedplumEncounterTranslator
from app.connectors.medplum.translators.healthcare_service import (
    MedplumHealthcareServiceTranslator,
)
from app.connectors.medplum.translators.location import MedplumLocationTranslator
from app.connectors.medplum.translators.medication_request import (
    MedplumMedicationRequestTranslator,
)
from app.connectors.medplum.translators.observation import (
    MedplumObservationTranslator,
)
from app.connectors.medplum.translators.organization import (
    MedplumOrganizationTranslator,
)
from app.connectors.medplum.translators.practitioner import (
    MedplumPractitionerTranslator,
)
from app.connectors.medplum.translators.practitioner_role import (
    MedplumPractitionerRoleTranslator,
)
from app.connectors.medplum.translators.questionnaire import (
    MedplumQuestionnaireTranslator,
)
from app.connectors.medplum.translators.questionnaire_response import (
    MedplumQuestionnaireResponseTranslator,
)
from app.connectors.medplum.translators.schedule import MedplumScheduleTranslator
from app.connectors.medplum.translators.service_request import MedplumServiceRequestTranslator
from app.connectors.medplum.translators.slot import MedplumSlotTranslator

__all__ = [
    "MedplumAppointmentTranslator",
    "MedplumAppointmentResponseTranslator",
    "MedplumDiagnosticReportTranslator",
    "MedplumEncounterTranslator",
    "MedplumHealthcareServiceTranslator",
    "MedplumLocationTranslator",
    "MedplumMedicationRequestTranslator",
    "MedplumObservationTranslator",
    "MedplumOrganizationTranslator",
    "MedplumPractitionerTranslator",
    "MedplumPractitionerRoleTranslator",
    "MedplumQuestionnaireTranslator",
    "MedplumQuestionnaireResponseTranslator",
    "MedplumScheduleTranslator",
    "MedplumServiceRequestTranslator",
    "MedplumSlotTranslator",
]
