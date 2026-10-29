"""
Composes the GraphQL schema from per-domain Query/Mutation resolver mixins
and exposes it as a FastAPI-mountable router.

Organization, Location, HealthcareService, Practitioner,
PractitionerRole, Schedule, Slot, Appointment, AppointmentResponse,
Encounter, Questionnaire, and QuestionnaireResponse are the FHIR
resources this gateway exposes. All twelve are genuinely FHIR R4-shaped
end-to-end (see app.gql.organization's package docstring, which
app.gql.location, app.gql.healthcare_service, app.gql.practitioner,
app.gql.practitioner_role, app.gql.schedule, app.gql.slot,
app.gql.appointment, app.gql.appointment_response, app.gql.encounter,
app.gql.questionnaire, and app.gql.questionnaire_response all mirror
exactly) — their resolvers call the active connector directly and
translate via
app.connectors.translator_registry.active_organization_translator()/
active_location_translator()/active_healthcare_service_translator()/
active_practitioner_translator()/active_practitioner_role_translator()/
active_schedule_translator()/active_slot_translator()/
active_appointment_translator()/active_appointment_response_translator()/
active_encounter_translator()/active_questionnaire_translator()/
active_questionnaire_response_translator(), keyed off
`settings.connectors.active`, rather than going through a per-resource
service/client layer. QuestionnaireResponse is the one exception to the
"genuinely FHIR R4-shaped, no extra fields" rule on write — see
app.connectors.internal.translators.questionnaire_response's module
docstring for why its own `to_wire_create`/`to_wire_patch` take extra
keyword-only arguments unlike every other resource's translator.

Adding another resource means: write its `app/gql/<resource>/types/` +
`queries.py` + `mutations.py` (and, if it needs its own translation layer,
`app/connectors/<connector>/translators/<resource>.py` + a registry entry
in app.connectors.translator_registry — see app.gql.organization's package
docstring for the full pattern), then mix its Query/Mutation into the root
types below the same way FhirOrganizationQuery/FhirOrganizationMutation,
FhirLocationQuery/FhirLocationMutation,
FhirHealthcareServiceQuery/FhirHealthcareServiceMutation,
FhirPractitionerQuery/FhirPractitionerMutation,
FhirPractitionerRoleQuery/FhirPractitionerRoleMutation,
FhirScheduleQuery/FhirScheduleMutation,
FhirSlotQuery/FhirSlotMutation,
FhirAppointmentQuery/FhirAppointmentMutation,
FhirAppointmentResponseQuery/FhirAppointmentResponseMutation,
FhirEncounterQuery/FhirEncounterMutation,
FhirQuestionnaireQuery/FhirQuestionnaireMutation, and
FhirQuestionnaireResponseQuery/FhirQuestionnaireResponseMutation are.

GraphQL is this service's only transport — there is no REST layer.
"""

import strawberry
from strawberry.fastapi import GraphQLRouter

from app.core.config import settings
from app.gql.appointment.mutations import FhirAppointmentMutation
from app.gql.appointment.queries import FhirAppointmentQuery
from app.gql.appointment_response.mutations import FhirAppointmentResponseMutation
from app.gql.appointment_response.queries import FhirAppointmentResponseQuery
from app.gql.context import get_context
from app.gql.diagnostic_report.mutations import FhirDiagnosticReportMutation
from app.gql.diagnostic_report.queries import FhirDiagnosticReportQuery
from app.gql.encounter.mutations import FhirEncounterMutation
from app.gql.encounter.queries import FhirEncounterQuery
from app.gql.healthcare_service.mutations import FhirHealthcareServiceMutation
from app.gql.healthcare_service.queries import FhirHealthcareServiceQuery
from app.gql.location.mutations import FhirLocationMutation
from app.gql.location.queries import FhirLocationQuery
from app.gql.logging import GqlLoggingExtension
from app.gql.medication_request.mutations import FhirMedicationRequestMutation
from app.gql.medication_request.queries import FhirMedicationRequestQuery
from app.gql.observation.mutations import FhirObservationMutation
from app.gql.observation.queries import FhirObservationQuery
from app.gql.organization.mutations import FhirOrganizationMutation
from app.gql.organization.queries import FhirOrganizationQuery
from app.gql.practitioner.mutations import FhirPractitionerMutation
from app.gql.practitioner.queries import FhirPractitionerQuery
from app.gql.practitioner_role.mutations import FhirPractitionerRoleMutation
from app.gql.practitioner_role.queries import FhirPractitionerRoleQuery
from app.gql.questionnaire.mutations import FhirQuestionnaireMutation
from app.gql.questionnaire.queries import FhirQuestionnaireQuery
from app.gql.questionnaire_response.mutations import FhirQuestionnaireResponseMutation
from app.gql.questionnaire_response.queries import FhirQuestionnaireResponseQuery
from app.gql.schedule.mutations import FhirScheduleMutation
from app.gql.schedule.queries import FhirScheduleQuery
from app.gql.service_request.mutations import FhirServiceRequestMutation
from app.gql.service_request.queries import FhirServiceRequestQuery
from app.gql.slot.mutations import FhirSlotMutation
from app.gql.slot.queries import FhirSlotQuery
from app.gql.test_subscription import TestSubscription


@strawberry.type
class Query(
    FhirOrganizationQuery,
    FhirLocationQuery,
    FhirHealthcareServiceQuery,
    FhirPractitionerQuery,
    FhirPractitionerRoleQuery,
    FhirScheduleQuery,
    FhirSlotQuery,
    FhirAppointmentQuery,
    FhirAppointmentResponseQuery,
    FhirEncounterQuery,
    FhirQuestionnaireQuery,
    FhirQuestionnaireResponseQuery,
    FhirServiceRequestQuery,
    FhirMedicationRequestQuery,
    FhirObservationQuery,
    FhirDiagnosticReportQuery,
):
    """Root GraphQL query type — merges every resource's query fields via
    mixin inheritance. Add a new resource's Query mixin here alongside
    `FhirOrganizationQuery`/`FhirLocationQuery`/`FhirHealthcareServiceQuery`/
    `FhirPractitionerQuery`/`FhirPractitionerRoleQuery`/`FhirScheduleQuery`/
    `FhirSlotQuery`/`FhirAppointmentQuery`/`FhirAppointmentResponseQuery`/
    `FhirEncounterQuery`/`FhirQuestionnaireQuery`/`FhirQuestionnaireResponseQuery`/
    `FhirServiceRequestQuery`/`FhirMedicationRequestQuery`/`FhirObservationQuery` as it's added."""


@strawberry.type
class Mutation(
    FhirOrganizationMutation,
    FhirLocationMutation,
    FhirHealthcareServiceMutation,
    FhirPractitionerMutation,
    FhirPractitionerRoleMutation,
    FhirScheduleMutation,
    FhirSlotMutation,
    FhirAppointmentMutation,
    FhirAppointmentResponseMutation,
    FhirEncounterMutation,
    FhirQuestionnaireMutation,
    FhirQuestionnaireResponseMutation,
    FhirServiceRequestMutation,
    FhirMedicationRequestMutation,
    FhirObservationMutation,
    FhirDiagnosticReportMutation,
):
    """Root GraphQL mutation type — merges every resource's mutation fields via mixin inheritance."""


@strawberry.type
class Subscription(TestSubscription):
    """"""


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
    # One log line per operation — see app/gql/logging.py's docstring.
    extensions=[GqlLoggingExtension],
)

# GraphiQL (the in-browser IDE served on GET /graphql) is convenient for
# local/dev testing but disabled in production to avoid exposing schema
# introspection and a live query console publicly.
#
# allow_queries_via_get=False is required for auth correctness, not just
# style: with it left at Strawberry's default (True), a client could send a
# full GraphQL operation as `GET /graphql?query=...`. Auth is enforced inside
# get_context() (see app/gql/context.py) rather than as a router-level
# FastAPI dependency, specifically so the bare GraphiQL HTML/JS shell can
# still load without an Authorization header — a browser navigating to
# GET /graphql cannot attach one. If GET could also execute operations,
# that path would bypass auth entirely.
graphql_router = GraphQLRouter(
    schema,
    context_getter=get_context,
    graphql_ide="graphiql" if settings.ENVIRONMENT != "production" else None,
    allow_queries_via_get=False,
)
