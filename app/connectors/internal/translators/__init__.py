"""
Per-connector translation for the internal (this application's own
fhir-server) connector, one module per resource (organization.py,
location.py, healthcare_service.py, ... as more get added). See
app.connectors.base.OrganizationWireTranslator/LocationWireTranslator/
HealthcareServiceWireTranslator for the shared contracts and
app.gql.organization's package docstring for the overall idea. Re-exported
here so existing imports
(`from app.connectors.internal.translators import InternalOrganizationTranslator`)
keep working unchanged regardless of which resource module a name lives in.
"""

from app.connectors.internal.translators.appointment import (
    InternalAppointmentTranslator,
)
from app.connectors.internal.translators.appointment_response import (
    InternalAppointmentResponseTranslator,
)
from app.connectors.internal.translators.diagnostic_report import (
    InternalDiagnosticReportTranslator,
)
from app.connectors.internal.translators.encounter import InternalEncounterTranslator
from app.connectors.internal.translators.healthcare_service import (
    InternalHealthcareServiceTranslator,
)
from app.connectors.internal.translators.location import InternalLocationTranslator
from app.connectors.internal.translators.medication_request import (
    InternalMedicationRequestTranslator,
)
from app.connectors.internal.translators.observation import (
    InternalObservationTranslator,
)
from app.connectors.internal.translators.organization import (
    InternalOrganizationTranslator,
)
from app.connectors.internal.translators.practitioner import (
    InternalPractitionerTranslator,
)
from app.connectors.internal.translators.practitioner_role import (
    InternalPractitionerRoleTranslator,
)
from app.connectors.internal.translators.questionnaire import (
    InternalQuestionnaireTranslator,
)
from app.connectors.internal.translators.questionnaire_response import (
    InternalQuestionnaireResponseTranslator,
)
from app.connectors.internal.translators.schedule import InternalScheduleTranslator
from app.connectors.internal.translators.service_request import InternalServiceRequestTranslator
from app.connectors.internal.translators.slot import InternalSlotTranslator

__all__ = [
    "InternalAppointmentTranslator",
    "InternalAppointmentResponseTranslator",
    "InternalDiagnosticReportTranslator",
    "InternalEncounterTranslator",
    "InternalHealthcareServiceTranslator",
    "InternalLocationTranslator",
    "InternalMedicationRequestTranslator",
    "InternalObservationTranslator",
    "InternalOrganizationTranslator",
    "InternalPractitionerTranslator",
    "InternalPractitionerRoleTranslator",
    "InternalQuestionnaireTranslator",
    "InternalQuestionnaireResponseTranslator",
    "InternalScheduleTranslator",
    "InternalServiceRequestTranslator",
    "InternalSlotTranslator",
]
