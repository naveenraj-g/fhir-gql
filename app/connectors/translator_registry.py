"""
Maps `connectors.active` to that connector's own Organization wire
translator — the translation-layer counterpart of
app.connectors.registry.CONNECTORS (the connector's base HTTP
implementation) and app.connectors.resource_registry.CONNECTOR_RESOURCES
(its per-resource client/service classes).

app.gql.organization's queries/mutations use this to pick the right
translator for the currently active connector instead of importing one
connector's translator from a fixed location directly — see
app.connectors.base.OrganizationWireTranslator for the shared contract.

Adding another resource's translator means: write
app/connectors/internal/translators/<resource>.py and
app/connectors/medplum/translators/<resource>.py the same way the
Organization/Location ones are written, then add a corresponding
`<RESOURCE>_TRANSLATORS = {...}` dict + `active_<resource>_translator()`
helper below — this module grows one resource at a time the same way
resource_registry.py does.
"""

from app.connectors.internal.translators import (
    InternalAppointmentResponseTranslator,
    InternalAppointmentTranslator,
    InternalEncounterTranslator,
    InternalHealthcareServiceTranslator,
    InternalLocationTranslator,
    InternalMedicationRequestTranslator,
    InternalOrganizationTranslator,
    InternalPractitionerTranslator,
    InternalPractitionerRoleTranslator,
    InternalQuestionnaireTranslator,
    InternalQuestionnaireResponseTranslator,
    InternalScheduleTranslator,
    InternalServiceRequestTranslator,
    InternalSlotTranslator,
)
from app.connectors.medplum.translators import (
    MedplumAppointmentResponseTranslator,
    MedplumAppointmentTranslator,
    MedplumEncounterTranslator,
    MedplumHealthcareServiceTranslator,
    MedplumLocationTranslator,
    MedplumMedicationRequestTranslator,
    MedplumOrganizationTranslator,
    MedplumPractitionerTranslator,
    MedplumPractitionerRoleTranslator,
    MedplumQuestionnaireTranslator,
    MedplumQuestionnaireResponseTranslator,
    MedplumScheduleTranslator,
    MedplumServiceRequestTranslator,
    MedplumSlotTranslator,
)
from app.core.config import settings

APPOINTMENT_TRANSLATORS = {
    "internal": InternalAppointmentTranslator(),
    "medplum": MedplumAppointmentTranslator(),
}

APPOINTMENT_RESPONSE_TRANSLATORS = {
    "internal": InternalAppointmentResponseTranslator(),
    "medplum": MedplumAppointmentResponseTranslator(),
}

ENCOUNTER_TRANSLATORS = {
    "internal": InternalEncounterTranslator(),
    "medplum": MedplumEncounterTranslator(),
}

ORGANIZATION_TRANSLATORS = {
    "internal": InternalOrganizationTranslator(),
    "medplum": MedplumOrganizationTranslator(),
}

LOCATION_TRANSLATORS = {
    "internal": InternalLocationTranslator(),
    "medplum": MedplumLocationTranslator(),
}

HEALTHCARE_SERVICE_TRANSLATORS = {
    "internal": InternalHealthcareServiceTranslator(),
    "medplum": MedplumHealthcareServiceTranslator(),
}

PRACTITIONER_TRANSLATORS = {
    "internal": InternalPractitionerTranslator(),
    "medplum": MedplumPractitionerTranslator(),
}

PRACTITIONER_ROLE_TRANSLATORS = {
    "internal": InternalPractitionerRoleTranslator(),
    "medplum": MedplumPractitionerRoleTranslator(),
}

SCHEDULE_TRANSLATORS = {
    "internal": InternalScheduleTranslator(),
    "medplum": MedplumScheduleTranslator(),
}

SLOT_TRANSLATORS = {
    "internal": InternalSlotTranslator(),
    "medplum": MedplumSlotTranslator(),
}

QUESTIONNAIRE_TRANSLATORS = {
    "internal": InternalQuestionnaireTranslator(),
    "medplum": MedplumQuestionnaireTranslator(),
}

QUESTIONNAIRE_RESPONSE_TRANSLATORS = {
    "internal": InternalQuestionnaireResponseTranslator(),
    "medplum": MedplumQuestionnaireResponseTranslator(),
}

SERVICE_REQUEST_TRANSLATORS = {
    "internal": InternalServiceRequestTranslator(),
    "medplum": MedplumServiceRequestTranslator(),
}

MEDICATION_REQUEST_TRANSLATORS = {
    "internal": InternalMedicationRequestTranslator(),
    "medplum": MedplumMedicationRequestTranslator(),
}


def active_appointment_translator():
    """The Appointment wire translator for whichever connector
    configs/config.yaml's `connectors.active` currently selects. Shared by
    both app.gql.appointment.queries and .mutations."""
    return APPOINTMENT_TRANSLATORS[settings.connectors.active]


def active_appointment_response_translator():
    """The AppointmentResponse wire translator for whichever connector
    configs/config.yaml's `connectors.active` currently selects. Shared by
    both app.gql.appointment_response.queries and .mutations."""
    return APPOINTMENT_RESPONSE_TRANSLATORS[settings.connectors.active]


def active_encounter_translator():
    """The Encounter wire translator for whichever connector
    configs/config.yaml's `connectors.active` currently selects. Shared by
    both app.gql.encounter.queries and .mutations."""
    return ENCOUNTER_TRANSLATORS[settings.connectors.active]


def active_organization_translator():
    """The Organization wire translator for whichever connector
    configs/config.yaml's `connectors.active` currently selects. Shared by
    both app.gql.organization.queries and .mutations."""
    return ORGANIZATION_TRANSLATORS[settings.connectors.active]


def active_location_translator():
    """The Location wire translator for whichever connector
    configs/config.yaml's `connectors.active` currently selects. Shared by
    both app.gql.location.queries and .mutations."""
    return LOCATION_TRANSLATORS[settings.connectors.active]


def active_healthcare_service_translator():
    """The HealthcareService wire translator for whichever connector
    configs/config.yaml's `connectors.active` currently selects. Shared by
    both app.gql.healthcare_service.queries and .mutations."""
    return HEALTHCARE_SERVICE_TRANSLATORS[settings.connectors.active]


def active_practitioner_translator():
    """The Practitioner wire translator for whichever connector
    configs/config.yaml's `connectors.active` currently selects. Shared by
    both app.gql.practitioner.queries and .mutations."""
    return PRACTITIONER_TRANSLATORS[settings.connectors.active]


def active_practitioner_role_translator():
    """The PractitionerRole wire translator for whichever connector
    configs/config.yaml's `connectors.active` currently selects. Shared by
    both app.gql.practitioner_role.queries and .mutations."""
    return PRACTITIONER_ROLE_TRANSLATORS[settings.connectors.active]


def active_schedule_translator():
    """The Schedule wire translator for whichever connector
    configs/config.yaml's `connectors.active` currently selects. Shared by
    both app.gql.schedule.queries and .mutations."""
    return SCHEDULE_TRANSLATORS[settings.connectors.active]


def active_slot_translator():
    """The Slot wire translator for whichever connector
    configs/config.yaml's `connectors.active` currently selects. Shared by
    both app.gql.slot.queries and .mutations."""
    return SLOT_TRANSLATORS[settings.connectors.active]


def active_questionnaire_translator():
    """The Questionnaire wire translator for whichever connector
    configs/config.yaml's `connectors.active` currently selects. Shared by
    both app.gql.questionnaire.queries and .mutations."""
    return QUESTIONNAIRE_TRANSLATORS[settings.connectors.active]


def active_questionnaire_response_translator():
    """The QuestionnaireResponse wire translator for whichever connector
    configs/config.yaml's `connectors.active` currently selects. Shared by
    both app.gql.questionnaire_response.queries and .mutations."""
    return QUESTIONNAIRE_RESPONSE_TRANSLATORS[settings.connectors.active]


def active_service_request_translator():
    """The ServiceRequest wire translator for whichever connector
    configs/config.yaml's `connectors.active` currently selects. Shared by
    both app.gql.service_request.queries and .mutations."""
    return SERVICE_REQUEST_TRANSLATORS[settings.connectors.active]


def active_medication_request_translator():
    """The MedicationRequest wire translator for whichever connector
    configs/config.yaml's `connectors.active` currently selects. Shared by
    both app.gql.medication_request.queries and .mutations."""
    return MEDICATION_REQUEST_TRANSLATORS[settings.connectors.active]
