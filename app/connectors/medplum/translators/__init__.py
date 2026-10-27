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

from app.connectors.medplum.translators.healthcare_service import (
    MedplumHealthcareServiceTranslator,
)
from app.connectors.medplum.translators.location import MedplumLocationTranslator
from app.connectors.medplum.translators.organization import (
    MedplumOrganizationTranslator,
)
from app.connectors.medplum.translators.practitioner import (
    MedplumPractitionerTranslator,
)
from app.connectors.medplum.translators.practitioner_role import (
    MedplumPractitionerRoleTranslator,
)
from app.connectors.medplum.translators.schedule import MedplumScheduleTranslator
from app.connectors.medplum.translators.slot import MedplumSlotTranslator

__all__ = [
    "MedplumHealthcareServiceTranslator",
    "MedplumLocationTranslator",
    "MedplumOrganizationTranslator",
    "MedplumPractitionerTranslator",
    "MedplumPractitionerRoleTranslator",
    "MedplumScheduleTranslator",
    "MedplumSlotTranslator",
]
