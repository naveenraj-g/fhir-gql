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

from app.connectors.internal.translators.healthcare_service import (
    InternalHealthcareServiceTranslator,
)
from app.connectors.internal.translators.location import InternalLocationTranslator
from app.connectors.internal.translators.organization import (
    InternalOrganizationTranslator,
)
from app.connectors.internal.translators.practitioner import (
    InternalPractitionerTranslator,
)
from app.connectors.internal.translators.practitioner_role import (
    InternalPractitionerRoleTranslator,
)
from app.connectors.internal.translators.schedule import InternalScheduleTranslator
from app.connectors.internal.translators.slot import InternalSlotTranslator

__all__ = [
    "InternalHealthcareServiceTranslator",
    "InternalLocationTranslator",
    "InternalOrganizationTranslator",
    "InternalPractitionerTranslator",
    "InternalPractitionerRoleTranslator",
    "InternalScheduleTranslator",
    "InternalSlotTranslator",
]
