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

Which resources are exposed is driven by configs/config.yaml's
`routes.enabled` (mirrors fhir-server). Adding another resource means: write
its `app/gql/<resource>/` package (+ translators, see app.gql.organization's
docstring), add an entry to RESOURCES below, and list its name in
`routes.enabled`.

GraphQL is this service's only transport — there is no REST layer.
"""

import importlib

import strawberry
from strawberry.fastapi import GraphQLRouter

from app.core.config import settings
from app.gql.context import get_context
from app.gql.logging import GqlLoggingExtension
from app.gql.test_subscription import TestQuery, TestSubscription

# resource name (as written in configs/config.yaml's routes.enabled) ->
# (package, Query mixin, Mutation mixin). Modules are imported lazily, only
# for enabled resources. Add a new resource here once its package exists.
RESOURCES: dict[str, tuple[str, str, str]] = {
    "organization": ("organization", "FhirOrganizationQuery", "FhirOrganizationMutation"),
    "location": ("location", "FhirLocationQuery", "FhirLocationMutation"),
    "healthcare_service": ("healthcare_service", "FhirHealthcareServiceQuery", "FhirHealthcareServiceMutation"),
    "practitioner": ("practitioner", "FhirPractitionerQuery", "FhirPractitionerMutation"),
    "practitioner_role": ("practitioner_role", "FhirPractitionerRoleQuery", "FhirPractitionerRoleMutation"),
    "schedule": ("schedule", "FhirScheduleQuery", "FhirScheduleMutation"),
    "slot": ("slot", "FhirSlotQuery", "FhirSlotMutation"),
    "appointment": ("appointment", "FhirAppointmentQuery", "FhirAppointmentMutation"),
    "appointment_response": ("appointment_response", "FhirAppointmentResponseQuery", "FhirAppointmentResponseMutation"),
    "encounter": ("encounter", "FhirEncounterQuery", "FhirEncounterMutation"),
    "questionnaire": ("questionnaire", "FhirQuestionnaireQuery", "FhirQuestionnaireMutation"),
    "questionnaire_response": ("questionnaire_response", "FhirQuestionnaireResponseQuery", "FhirQuestionnaireResponseMutation"),
    "service_request": ("service_request", "FhirServiceRequestQuery", "FhirServiceRequestMutation"),
    "medication_request": ("medication_request", "FhirMedicationRequestQuery", "FhirMedicationRequestMutation"),
    "observation": ("observation", "FhirObservationQuery", "FhirObservationMutation"),
    "diagnostic_report": ("diagnostic_report", "FhirDiagnosticReportQuery", "FhirDiagnosticReportMutation"),
}


def _enabled_resources() -> list[str]:
    enabled = list(dict.fromkeys(settings.routes.enabled))
    unknown = [name for name in enabled if name not in RESOURCES]
    if unknown:
        raise RuntimeError(
            f"routes.enabled contains unknown resource(s) {unknown}; "
            f"valid names: {sorted(RESOURCES)}"
        )
    return enabled


def _compose(enabled: list[str]) -> tuple[type, type | None]:
    query_bases: list[type] = []
    mutation_bases: list[type] = []
    for name in enabled:
        package, query_name, mutation_name = RESOURCES[name]
        query_bases.append(
            getattr(importlib.import_module(f"app.gql.{package}.queries"), query_name)
        )
        mutation_bases.append(
            getattr(importlib.import_module(f"app.gql.{package}.mutations"), mutation_name)
        )

    # GraphQL requires a Query root with at least one field — TestQuery.hello
    # is always present so an empty routes.enabled still yields a valid schema.
    query = strawberry.type(
        type(
            "Query",
            (*query_bases, TestQuery),
            {"__doc__": "Root GraphQL query type — composed from routes.enabled."},
        )
    )
    mutation = (
        strawberry.type(
            type(
                "Mutation",
                tuple(mutation_bases),
                {"__doc__": "Root GraphQL mutation type — composed from routes.enabled."},
            )
        )
        if mutation_bases
        else None
    )
    return query, mutation


Query, Mutation = _compose(_enabled_resources())


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
