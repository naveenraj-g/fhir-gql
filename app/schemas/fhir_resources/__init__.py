"""Fully-typed FHIR R4 resource models (generated; see scripts/generate_fhir_resources.py)."""

from app.schemas.fhir_resources.activity_definition import (
    ActivityDefinition,
    ActivityDefinitionPatch,
)
from app.schemas.fhir_resources.allergy_intolerance import (
    AllergyIntolerance,
    AllergyIntolerancePatch,
)
from app.schemas.fhir_resources.appointment import Appointment, AppointmentPatch
from app.schemas.fhir_resources.appointment_response import (
    AppointmentResponse,
    AppointmentResponsePatch,
)
from app.schemas.fhir_resources.care_plan import CarePlan, CarePlanPatch
from app.schemas.fhir_resources.care_team import CareTeam, CareTeamPatch
from app.schemas.fhir_resources.clinical_impression import (
    ClinicalImpression,
    ClinicalImpressionPatch,
)
from app.schemas.fhir_resources.communication import Communication, CommunicationPatch
from app.schemas.fhir_resources.communication_request import (
    CommunicationRequest,
    CommunicationRequestPatch,
)
from app.schemas.fhir_resources.condition import Condition, ConditionPatch
from app.schemas.fhir_resources.consent import Consent, ConsentPatch
from app.schemas.fhir_resources.detected_issue import DetectedIssue, DetectedIssuePatch
from app.schemas.fhir_resources.diagnostic_report import (
    DiagnosticReport,
    DiagnosticReportPatch,
)
from app.schemas.fhir_resources.document_reference import (
    DocumentReference,
    DocumentReferencePatch,
)
from app.schemas.fhir_resources.encounter import Encounter, EncounterPatch
from app.schemas.fhir_resources.endpoint import Endpoint, EndpointPatch
from app.schemas.fhir_resources.episode_of_care import EpisodeOfCare, EpisodeOfCarePatch
from app.schemas.fhir_resources.family_member_history import (
    FamilyMemberHistory,
    FamilyMemberHistoryPatch,
)
from app.schemas.fhir_resources.flag import Flag, FlagPatch
from app.schemas.fhir_resources.goal import Goal, GoalPatch
from app.schemas.fhir_resources.group import Group, GroupPatch
from app.schemas.fhir_resources.healthcare_service import (
    HealthcareService,
    HealthcareServicePatch,
)
from app.schemas.fhir_resources.immunization import Immunization, ImmunizationPatch
from app.schemas.fhir_resources.immunization_evaluation import (
    ImmunizationEvaluation,
    ImmunizationEvaluationPatch,
)
from app.schemas.fhir_resources.immunization_recommendation import (
    ImmunizationRecommendation,
    ImmunizationRecommendationPatch,
)
from app.schemas.fhir_resources.location import Location, LocationPatch
from app.schemas.fhir_resources.measure import Measure, MeasurePatch
from app.schemas.fhir_resources.measure_report import MeasureReport, MeasureReportPatch
from app.schemas.fhir_resources.medication import Medication, MedicationPatch
from app.schemas.fhir_resources.medication_administration import (
    MedicationAdministration,
    MedicationAdministrationPatch,
)
from app.schemas.fhir_resources.medication_dispense import (
    MedicationDispense,
    MedicationDispensePatch,
)
from app.schemas.fhir_resources.medication_knowledge import (
    MedicationKnowledge,
    MedicationKnowledgePatch,
)
from app.schemas.fhir_resources.medication_request import (
    MedicationRequest,
    MedicationRequestPatch,
)
from app.schemas.fhir_resources.medication_statement import (
    MedicationStatement,
    MedicationStatementPatch,
)
from app.schemas.fhir_resources.observation import Observation, ObservationPatch
from app.schemas.fhir_resources.observation_definition import (
    ObservationDefinition,
    ObservationDefinitionPatch,
)
from app.schemas.fhir_resources.organization import Organization, OrganizationPatch
from app.schemas.fhir_resources.patient import Patient, PatientPatch
from app.schemas.fhir_resources.plan_definition import (
    PlanDefinition,
    PlanDefinitionPatch,
)
from app.schemas.fhir_resources.practitioner import Practitioner, PractitionerPatch
from app.schemas.fhir_resources.practitioner_role import (
    PractitionerRole,
    PractitionerRolePatch,
)
from app.schemas.fhir_resources.procedure import Procedure, ProcedurePatch
from app.schemas.fhir_resources.questionnaire import Questionnaire, QuestionnairePatch
from app.schemas.fhir_resources.questionnaire_response import (
    QuestionnaireResponse,
    QuestionnaireResponsePatch,
)
from app.schemas.fhir_resources.related_person import RelatedPerson, RelatedPersonPatch
from app.schemas.fhir_resources.risk_assessment import (
    RiskAssessment,
    RiskAssessmentPatch,
)
from app.schemas.fhir_resources.schedule import Schedule, SchedulePatch
from app.schemas.fhir_resources.service_request import (
    ServiceRequest,
    ServiceRequestPatch,
)
from app.schemas.fhir_resources.slot import Slot, SlotPatch
from app.schemas.fhir_resources.specimen import Specimen, SpecimenPatch
from app.schemas.fhir_resources.specimen_definition import (
    SpecimenDefinition,
    SpecimenDefinitionPatch,
)
from app.schemas.fhir_resources.task import Task, TaskPatch

__all__ = [
    "ActivityDefinition",
    "ActivityDefinitionPatch",
    "AllergyIntolerance",
    "AllergyIntolerancePatch",
    "Appointment",
    "AppointmentPatch",
    "AppointmentResponse",
    "AppointmentResponsePatch",
    "CarePlan",
    "CarePlanPatch",
    "CareTeam",
    "CareTeamPatch",
    "ClinicalImpression",
    "ClinicalImpressionPatch",
    "Communication",
    "CommunicationPatch",
    "CommunicationRequest",
    "CommunicationRequestPatch",
    "Condition",
    "ConditionPatch",
    "Consent",
    "ConsentPatch",
    "DetectedIssue",
    "DetectedIssuePatch",
    "DiagnosticReport",
    "DiagnosticReportPatch",
    "DocumentReference",
    "DocumentReferencePatch",
    "Encounter",
    "EncounterPatch",
    "Endpoint",
    "EndpointPatch",
    "EpisodeOfCare",
    "EpisodeOfCarePatch",
    "FamilyMemberHistory",
    "FamilyMemberHistoryPatch",
    "Flag",
    "FlagPatch",
    "Goal",
    "GoalPatch",
    "Group",
    "GroupPatch",
    "HealthcareService",
    "HealthcareServicePatch",
    "Immunization",
    "ImmunizationEvaluation",
    "ImmunizationEvaluationPatch",
    "ImmunizationPatch",
    "ImmunizationRecommendation",
    "ImmunizationRecommendationPatch",
    "Location",
    "LocationPatch",
    "Measure",
    "MeasurePatch",
    "MeasureReport",
    "MeasureReportPatch",
    "Medication",
    "MedicationAdministration",
    "MedicationAdministrationPatch",
    "MedicationDispense",
    "MedicationDispensePatch",
    "MedicationKnowledge",
    "MedicationKnowledgePatch",
    "MedicationPatch",
    "MedicationRequest",
    "MedicationRequestPatch",
    "MedicationStatement",
    "MedicationStatementPatch",
    "Observation",
    "ObservationDefinition",
    "ObservationDefinitionPatch",
    "ObservationPatch",
    "Organization",
    "OrganizationPatch",
    "Patient",
    "PatientPatch",
    "PlanDefinition",
    "PlanDefinitionPatch",
    "Practitioner",
    "PractitionerPatch",
    "PractitionerRole",
    "PractitionerRolePatch",
    "Procedure",
    "ProcedurePatch",
    "Questionnaire",
    "QuestionnairePatch",
    "QuestionnaireResponse",
    "QuestionnaireResponsePatch",
    "RelatedPerson",
    "RelatedPersonPatch",
    "RiskAssessment",
    "RiskAssessmentPatch",
    "Schedule",
    "SchedulePatch",
    "ServiceRequest",
    "ServiceRequestPatch",
    "Slot",
    "SlotPatch",
    "Specimen",
    "SpecimenDefinition",
    "SpecimenDefinitionPatch",
    "SpecimenPatch",
    "Task",
    "TaskPatch",
]
