"""
The connector interface — the one seam between this gateway's GraphQL
resolvers (app.gql.organization, ...) and whatever system actually stores
the data.

Why this exists: a resolver is written against four HTTP-shaped verbs —
but nothing about it actually depends on the *backend* being our own
fhir-server. It just needs something that can POST/GET/PATCH/DELETE a path
and hand back a dict, inject actor identity, and translate a non-2xx
response into an HTTPException. `Connector` names that contract explicitly,
so a resolver can ask for "a connector" rather than "our own fhir-server
client" — any system satisfying this Protocol is a legal caller, not just
the one concrete implementation we have today.

Today there are two connectors: app.connectors.internal.InternalConnector,
representing *this* application (our own fhir-server), and
app.connectors.medplum.MedplumConnector. Which connector is active is a
config choice — see app.connectors.registry and configs/config.yaml's
`connectors.active` — not something any resolver ever needs to know about.

Adding a second connector (e.g. for Epic, or any other FHIR-R4-shaped
EMR/EHR) means: write a class satisfying this Protocol, register it in
app.connectors.registry.CONNECTORS, and set connectors.active — no change
to any resolver. Each connector owns its own URL/path conventions
internally (a real FHIR server's canonical REST paths look nothing like
fhir-server's own `/organizations`-style routes), so the `path` a resolver
passes in (via its OrganizationWireTranslator, see below) is only ever
meaningful to *that* connector — nothing above this interface should
assume a specific URL shape.

A `Protocol`, not an ABC: structural typing means InternalConnector
doesn't need to inherit from this class at all (and doesn't) — it just
needs to have these methods with these signatures. That keeps the concrete
connector free to also expose extra, connector-specific methods (as
InternalConnector does for its own error-detail extraction) without this
interface caring.
"""

from typing import Protocol

from app.auth.models import AuthUser


class Connector(Protocol):
    """Structural interface every connector must satisfy. See module
    docstring for the full rationale."""

    async def post(
        self,
        path: str,
        data: dict,
        actor: AuthUser,
        accept: str | None = None,
        inject_audit: bool = True,
    ) -> dict:
        """Create a resource at `path`."""
        ...

    async def get(
        self,
        path: str,
        params: dict | None = None,
        accept: str | None = None,
        actor: AuthUser | None = None,
    ) -> dict:
        """Read a resource or collection at `path`."""
        ...

    async def patch(
        self,
        path: str,
        data: dict | list[dict],
        actor: AuthUser,
        accept: str | None = None,
        inject_audit: bool = True,
    ) -> dict:
        """Partially update the resource at `path`. `data` is whatever
        shape this connector's own PATCH convention needs — a plain
        partial-fields dict (fhir-server's InternalConnector) or an RFC
        6902 JSON Patch array (MedplumConnector) — see each connector's
        own translator's `to_wire_patch()`."""
        ...

    async def delete(self, path: str, actor: AuthUser | None = None) -> None:
        """Delete the resource at `path`."""
        ...

    async def aclose(self) -> None:
        """Release the connector's underlying connection pool at shutdown."""
        ...


class OrganizationWireTranslator(Protocol):
    """
    One connector's read/write wire conventions for the canonical FHIR R4
    Organization shape used by app.gql.organization (see that package's
    __init__.py docstring).

    Structural, same spirit as `Connector` above: each connector
    (app.connectors.internal, app.connectors.medplum, ...) implements this
    with its own class rather than inheriting from it. Which connector's
    translator is active is resolved by
    app.connectors.translator_registry.active_organization_translator(),
    keyed off the same `connectors.active` config value as `Connector`
    itself.

    Both of today's connectors already return genuine FHIR R4 JSON for
    reads — fhir-server via its own `Accept: application/fhir+json` content
    negotiation, Medplum natively — so `from_wire()` is identity for both.
    Writes are NOT symmetric with reads: fhir-server's POST/PATCH only ever
    accept their own flattened plain-JSON shape (see
    app.connectors.internal.translators.organization's module docstring for
    the exact field-level mapping), never genuine FHIR JSON, which is why
    there's a to_wire_create/to_wire_patch pair instead of one to_wire().
    """

    #: Accept header to request FHIR R4 shape from this backend, or None if
    #: the backend only ever speaks FHIR (nothing to negotiate).
    accept: str | None

    def item_path(self, organization_id: str) -> str:
        """Path for GET-by-id/PATCH/DELETE, in this backend's own convention."""
        ...

    def list_path(self) -> str:
        """Path for GET-collection (search) and POST-create, in this
        backend's own convention."""
        ...

    def list_params(
        self,
        name: str | None,
        active: bool | None,
        identifier: str | None,
        org_type: str | None,
        address: str | None,
        address_city: str | None,
        address_state: str | None,
        address_postal_code: str | None,
        address_country: str | None,
        address_use: str | None,
        partof: str | None,
        endpoint: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Canonical filter/pagination args -> this backend's own query param
        names. The filter set mirrors FHIR R4's own Organization search
        parameters (https://hl7.org/fhir/R4/organization.html#search) minus
        `phonetic` — neither backend implements phonetic matching today."""
        ...

    def from_wire(self, raw: dict) -> dict:
        """This backend's raw response dict -> canonical FHIR Organization
        (or Bundle) dict. Identity for both connectors today — see class
        docstring."""
        ...

    def to_wire_create(self, data: dict) -> dict:
        """Canonical FHIR Organization dict (from FhirOrganizationInput) ->
        this backend's own POST-create body shape."""
        ...

    def to_wire_patch(self, data: dict) -> dict | list[dict]:
        """Canonical FHIR Organization dict (from FhirOrganizationInput) ->
        this backend's own PATCH-update body shape."""
        ...


class LocationWireTranslator(Protocol):
    """
    One connector's read/write wire conventions for the canonical FHIR R4
    Location shape used by app.gql.location — same structural pattern as
    OrganizationWireTranslator above, see that class's docstring for the
    overall rationale.

    Which connector's translator is active is resolved by
    app.connectors.translator_registry.active_location_translator(), keyed
    off the same `connectors.active` config value as `Connector` itself.

    Location has no top-level `active` field (unlike Organization), so
    there's no `active` filter in list_params below. There is also no
    `physical_type` filter, deliberately — physicalType is a real Location
    field, but it was never a registered FHIR R4 SearchParameter for
    Location, so it's excluded to keep this filter set exactly the real 15
    R4 search parameters: https://hl7.org/fhir/R4/location.html#search.
    """

    accept: str | None

    def item_path(self, location_id: str) -> str:
        """Path for GET-by-id/PATCH/DELETE, in this backend's own convention."""
        ...

    def list_path(self) -> str:
        """Path for GET-collection (search) and POST-create, in this
        backend's own convention."""
        ...

    def list_params(
        self,
        name: str | None,
        identifier: str | None,
        status: str | None,
        operational_status: str | None,
        location_type: str | None,
        address: str | None,
        address_city: str | None,
        address_state: str | None,
        address_postal_code: str | None,
        address_country: str | None,
        address_use: str | None,
        organization: str | None,
        partof: str | None,
        endpoint: str | None,
        near: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Canonical filter/pagination args -> this backend's own query
        param names. The filter set mirrors FHIR R4's own Location search
        parameters (https://hl7.org/fhir/R4/location.html#search)."""
        ...

    def from_wire(self, raw: dict) -> dict:
        """This backend's raw response dict -> canonical FHIR Location
        (or Bundle) dict. Identity for both connectors today."""
        ...

    def to_wire_create(self, data: dict) -> dict:
        """Canonical FHIR Location dict (from FhirLocationInput) -> this
        backend's own POST-create body shape."""
        ...

    def to_wire_patch(self, data: dict) -> dict | list[dict]:
        """Canonical FHIR Location dict (from FhirLocationInput) -> this
        backend's own PATCH-update body shape."""
        ...


class HealthcareServiceWireTranslator(Protocol):
    """
    One connector's read/write wire conventions for the canonical FHIR R4
    HealthcareService shape used by app.gql.healthcare_service — same
    structural pattern as OrganizationWireTranslator/LocationWireTranslator
    above, see OrganizationWireTranslator's docstring for the overall
    rationale.

    Which connector's translator is active is resolved by
    app.connectors.translator_registry.active_healthcare_service_translator(),
    keyed off the same `connectors.active` config value as `Connector`
    itself.
    """

    accept: str | None

    def item_path(self, healthcare_service_id: str) -> str:
        """Path for GET-by-id/PATCH/DELETE, in this backend's own convention."""
        ...

    def list_path(self) -> str:
        """Path for GET-collection (search) and POST-create, in this
        backend's own convention."""
        ...

    def list_params(
        self,
        name: str | None,
        identifier: str | None,
        active: bool | None,
        category: str | None,
        service_type: str | None,
        specialty: str | None,
        characteristic: str | None,
        program: str | None,
        organization: str | None,
        location: str | None,
        coverage_area: str | None,
        endpoint: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Canonical filter/pagination args -> this backend's own query
        param names. The filter set mirrors FHIR R4's own HealthcareService
        search parameters (https://hl7.org/fhir/R4/healthcareservice.html#search)."""
        ...

    def from_wire(self, raw: dict) -> dict:
        """This backend's raw response dict -> canonical FHIR
        HealthcareService (or Bundle) dict. Identity for both connectors
        today."""
        ...

    def to_wire_create(self, data: dict) -> dict:
        """Canonical FHIR HealthcareService dict (from
        FhirHealthcareServiceInput) -> this backend's own POST-create body
        shape."""
        ...

    def to_wire_patch(self, data: dict) -> dict | list[dict]:
        """Canonical FHIR HealthcareService dict (from
        FhirHealthcareServiceInput) -> this backend's own PATCH-update body
        shape."""
        ...


class PractitionerWireTranslator(Protocol):
    """
    One connector's read/write wire conventions for the canonical FHIR R4
    Practitioner shape used by app.gql.practitioner — same structural
    pattern as OrganizationWireTranslator/LocationWireTranslator/
    HealthcareServiceWireTranslator above, see OrganizationWireTranslator's
    docstring for the overall rationale.

    Which connector's translator is active is resolved by
    app.connectors.translator_registry.active_practitioner_translator(),
    keyed off the same `connectors.active` config value as `Connector`
    itself.
    """

    accept: str | None

    def item_path(self, practitioner_id: str) -> str:
        """Path for GET-by-id/PATCH/DELETE, in this backend's own convention."""
        ...

    def list_path(self) -> str:
        """Path for GET-collection (search) and POST-create, in this
        backend's own convention."""
        ...

    def list_params(
        self,
        name: str | None,
        family: str | None,
        given: str | None,
        identifier: str | None,
        active: bool | None,
        gender: str | None,
        communication: str | None,
        telecom: str | None,
        phone: str | None,
        email: str | None,
        address: str | None,
        address_city: str | None,
        address_state: str | None,
        address_postal_code: str | None,
        address_country: str | None,
        address_use: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Canonical filter/pagination args -> this backend's own query
        param names. The filter set mirrors FHIR R4's own Practitioner
        search parameters (https://hl7.org/fhir/R4/practitioner.html#search)
        minus `phonetic` — neither backend implements phonetic matching
        today, same exclusion as OrganizationWireTranslator's."""
        ...

    def from_wire(self, raw: dict) -> dict:
        """This backend's raw response dict -> canonical FHIR Practitioner
        (or Bundle) dict. Identity for both connectors today."""
        ...

    def to_wire_create(self, data: dict) -> dict:
        """Canonical FHIR Practitioner dict (from FhirPractitionerInput) ->
        this backend's own POST-create body shape."""
        ...

    def to_wire_patch(self, data: dict) -> dict | list[dict]:
        """Canonical FHIR Practitioner dict (from FhirPractitionerInput) ->
        this backend's own PATCH-update body shape."""
        ...


class PractitionerRoleWireTranslator(Protocol):
    """
    One connector's read/write wire conventions for the canonical FHIR R4
    PractitionerRole shape used by app.gql.practitioner_role — same
    structural pattern as OrganizationWireTranslator/LocationWireTranslator/
    HealthcareServiceWireTranslator/PractitionerWireTranslator above, see
    OrganizationWireTranslator's docstring for the overall rationale.

    Which connector's translator is active is resolved by
    app.connectors.translator_registry.active_practitioner_role_translator(),
    keyed off the same `connectors.active` config value as `Connector`
    itself.
    """

    accept: str | None

    def item_path(self, practitioner_role_id: str) -> str:
        """Path for GET-by-id/PATCH/DELETE, in this backend's own convention."""
        ...

    def list_path(self) -> str:
        """Path for GET-collection (search) and POST-create, in this
        backend's own convention."""
        ...

    def list_params(
        self,
        active: bool | None,
        identifier: str | None,
        code: str | None,
        specialty: str | None,
        practitioner: str | None,
        organization: str | None,
        location: str | None,
        healthcare_service: str | None,
        endpoint: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Canonical filter/pagination args -> this backend's own query
        param names. The filter set mirrors FHIR R4's own PractitionerRole
        search parameters
        (https://hl7.org/fhir/R4/practitionerrole.html#search) minus `date`
        — neither backend implements an `active`-period-range search today,
        and PractitionerRole's own `period` already carries that via
        `active` + the resource's own start/end."""
        ...

    def from_wire(self, raw: dict) -> dict:
        """This backend's raw response dict -> canonical FHIR
        PractitionerRole (or Bundle) dict. Identity for both connectors
        today."""
        ...

    def to_wire_create(self, data: dict) -> dict:
        """Canonical FHIR PractitionerRole dict (from
        FhirPractitionerRoleInput) -> this backend's own POST-create body
        shape."""
        ...

    def to_wire_patch(self, data: dict) -> dict | list[dict]:
        """Canonical FHIR PractitionerRole dict (from
        FhirPractitionerRoleInput) -> this backend's own PATCH-update body
        shape."""
        ...


class ScheduleWireTranslator(Protocol):
    """
    One connector's read/write wire conventions for the canonical FHIR R4
    Schedule shape used by app.gql.schedule — same structural pattern as
    OrganizationWireTranslator/LocationWireTranslator/
    HealthcareServiceWireTranslator/PractitionerWireTranslator/
    PractitionerRoleWireTranslator above, see OrganizationWireTranslator's
    docstring for the overall rationale.

    Which connector's translator is active is resolved by
    app.connectors.translator_registry.active_schedule_translator(), keyed
    off the same `connectors.active` config value as `Connector` itself.
    """

    accept: str | None

    def item_path(self, schedule_id: str) -> str:
        """Path for GET-by-id/PATCH/DELETE, in this backend's own convention."""
        ...

    def list_path(self) -> str:
        """Path for GET-collection (search) and POST-create, in this
        backend's own convention."""
        ...

    def list_params(
        self,
        active: bool | None,
        identifier: str | None,
        service_category: str | None,
        service_type: str | None,
        specialty: str | None,
        actor: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Canonical filter/pagination args -> this backend's own query
        param names. The filter set mirrors FHIR R4's own Schedule search
        parameters (https://hl7.org/fhir/R4/schedule.html#search) minus
        `date` — neither backend implements an `active`-period-range
        search today."""
        ...

    def from_wire(self, raw: dict) -> dict:
        """This backend's raw response dict -> canonical FHIR Schedule (or
        Bundle) dict. Identity for both connectors today."""
        ...

    def to_wire_create(self, data: dict) -> dict:
        """Canonical FHIR Schedule dict (from FhirScheduleInput) -> this
        backend's own POST-create body shape."""
        ...

    def to_wire_patch(self, data: dict) -> dict | list[dict]:
        """Canonical FHIR Schedule dict (from FhirScheduleInput) -> this
        backend's own PATCH-update body shape."""
        ...


class SlotWireTranslator(Protocol):
    """
    One connector's read/write wire conventions for the canonical FHIR R4
    Slot shape used by app.gql.slot — same structural pattern as
    OrganizationWireTranslator/LocationWireTranslator/
    HealthcareServiceWireTranslator/PractitionerWireTranslator/
    PractitionerRoleWireTranslator/ScheduleWireTranslator above, see
    OrganizationWireTranslator's docstring for the overall rationale.

    Which connector's translator is active is resolved by
    app.connectors.translator_registry.active_slot_translator(), keyed
    off the same `connectors.active` config value as `Connector` itself.
    """

    accept: str | None

    def item_path(self, slot_id: str) -> str:
        """Path for GET-by-id/PATCH/DELETE, in this backend's own convention."""
        ...

    def list_path(self) -> str:
        """Path for GET-collection (search) and POST-create, in this
        backend's own convention."""
        ...

    def list_params(
        self,
        status: str | None,
        identifier: str | None,
        service_category: str | None,
        service_type: str | None,
        specialty: str | None,
        schedule: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Canonical filter/pagination args -> this backend's own query
        param names. The filter set mirrors FHIR R4's own Slot search
        parameters (https://hl7.org/fhir/R4/slot.html#search) minus
        `start` — neither backend implements a date-range search on this
        today."""
        ...

    def from_wire(self, raw: dict) -> dict:
        """This backend's raw response dict -> canonical FHIR Slot (or
        Bundle) dict. Identity for both connectors today."""
        ...

    def to_wire_create(self, data: dict) -> dict:
        """Canonical FHIR Slot dict (from FhirSlotInput) -> this backend's
        own POST-create body shape."""
        ...

    def to_wire_patch(self, data: dict) -> dict | list[dict]:
        """Canonical FHIR Slot dict (from FhirSlotInput) -> this backend's
        own PATCH-update body shape."""
        ...


class AppointmentWireTranslator(Protocol):
    """
    One connector's read/write wire conventions for the canonical FHIR R4
    Appointment shape used by app.gql.appointment — same structural pattern
    as OrganizationWireTranslator/.../SlotWireTranslator above, see
    OrganizationWireTranslator's docstring for the overall rationale.

    Which connector's translator is active is resolved by
    app.connectors.translator_registry.active_appointment_translator(),
    keyed off the same `connectors.active` config value as `Connector`
    itself.
    """

    accept: str | None

    def item_path(self, appointment_id: str) -> str:
        """Path for GET-by-id/PATCH/DELETE, in this backend's own convention."""
        ...

    def list_path(self) -> str:
        """Path for GET-collection (search) and POST-create, in this
        backend's own convention."""
        ...

    def list_params(
        self,
        status: str | None,
        identifier: str | None,
        service_category: str | None,
        service_type: str | None,
        specialty: str | None,
        actor: str | None,
        slot: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Canonical filter/pagination args -> this backend's own query
        param names. The filter set mirrors a subset of FHIR R4's own
        Appointment search parameters
        (https://hl7.org/fhir/R4/appointment.html#search) — the same
        subset fhir-server's own router implements today."""
        ...

    def from_wire(self, raw: dict) -> dict:
        """This backend's raw response dict -> canonical FHIR Appointment
        (or Bundle) dict. Identity for both connectors today."""
        ...

    def to_wire_create(self, data: dict) -> dict:
        """Canonical FHIR Appointment dict (from FhirAppointmentInput) ->
        this backend's own POST-create body shape."""
        ...

    def to_wire_patch(self, data: dict) -> dict | list[dict]:
        """Canonical FHIR Appointment dict (from FhirAppointmentInput) ->
        this backend's own PATCH-update body shape."""
        ...


class AppointmentResponseWireTranslator(Protocol):
    """
    One connector's read/write wire conventions for the canonical FHIR R4
    AppointmentResponse shape used by app.gql.appointment_response — same
    structural pattern as OrganizationWireTranslator/.../
    AppointmentWireTranslator above, see OrganizationWireTranslator's
    docstring for the overall rationale.

    Which connector's translator is active is resolved by
    app.connectors.translator_registry.active_appointment_response_translator(),
    keyed off the same `connectors.active` config value as `Connector`
    itself.
    """

    accept: str | None

    def item_path(self, appointment_response_id: str) -> str:
        """Path for GET-by-id/PATCH/DELETE, in this backend's own convention."""
        ...

    def list_path(self) -> str:
        """Path for GET-collection (search) and POST-create, in this
        backend's own convention."""
        ...

    def list_params(
        self,
        identifier: str | None,
        appointment: str | None,
        actor: str | None,
        part_status: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Canonical filter/pagination args -> this backend's own query
        param names. The filter set mirrors a subset of FHIR R4's own
        AppointmentResponse search parameters
        (https://hl7.org/fhir/R4/appointmentresponse.html#search) — the
        same subset fhir-server's own router implements today."""
        ...

    def from_wire(self, raw: dict) -> dict:
        """This backend's raw response dict -> canonical FHIR
        AppointmentResponse (or Bundle) dict. Identity for both connectors
        today."""
        ...

    def to_wire_create(self, data: dict) -> dict:
        """Canonical FHIR AppointmentResponse dict (from
        FhirAppointmentResponseInput) -> this backend's own POST-create
        body shape."""
        ...

    def to_wire_patch(self, data: dict) -> dict | list[dict]:
        """Canonical FHIR AppointmentResponse dict (from
        FhirAppointmentResponseInput) -> this backend's own PATCH-update
        body shape."""
        ...


class EncounterWireTranslator(Protocol):
    """
    One connector's read/write wire conventions for the canonical FHIR R4
    Encounter shape used by app.gql.encounter — same structural pattern as
    OrganizationWireTranslator/.../AppointmentResponseWireTranslator above,
    see OrganizationWireTranslator's docstring for the overall rationale.

    Which connector's translator is active is resolved by
    app.connectors.translator_registry.active_encounter_translator(),
    keyed off the same `connectors.active` config value as `Connector`
    itself.
    """

    accept: str | None

    def item_path(self, encounter_id: str) -> str:
        """Path for GET-by-id/PATCH/DELETE, in this backend's own convention."""
        ...

    def list_path(self) -> str:
        """Path for GET-collection (search) and POST-create, in this
        backend's own convention."""
        ...

    def list_params(
        self,
        status: str | None,
        identifier: str | None,
        subject: str | None,
        class_code: str | None,
        type_code: str | None,
        service_provider: str | None,
        part_of: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Canonical filter/pagination args -> this backend's own query
        param names. The filter set mirrors a subset of FHIR R4's own
        Encounter search parameters
        (https://hl7.org/fhir/R4/encounter.html#search) — the same subset
        fhir-server's own router implements today."""
        ...

    def from_wire(self, raw: dict) -> dict:
        """This backend's raw response dict -> canonical FHIR Encounter
        (or Bundle) dict. Identity for both connectors today."""
        ...

    def to_wire_create(self, data: dict) -> dict:
        """Canonical FHIR Encounter dict (from FhirEncounterInput) -> this
        backend's own POST-create body shape."""
        ...

    def to_wire_patch(self, data: dict) -> dict | list[dict]:
        """Canonical FHIR Encounter dict (from FhirEncounterInput) -> this
        backend's own PATCH-update body shape."""
        ...


class QuestionnaireWireTranslator(Protocol):
    """
    One connector's read/write wire conventions for the canonical FHIR R4
    Questionnaire shape used by app.gql.questionnaire — same structural
    pattern as OrganizationWireTranslator/.../EncounterWireTranslator
    above, see OrganizationWireTranslator's docstring for the overall
    rationale.

    fhir-server's own Questionnaire is now one of its JWT-auth-rollout
    resources (same as Organization/Practitioner/etc.) — it derives
    `org_id`/`created_by`/`updated_by` from the forwarded JWT itself, so
    `to_wire_create`/`to_wire_patch` take no extra keyword-only arguments,
    same shape as every other resource's Protocol in this file.
    `user_id` is still a plain fhir-server field (like Practitioner's),
    but has no canonical-FHIR source to translate from, so it's simply
    never populated by either connector's translator — same narrower gap
    as PractitionerWireTranslator's own `user_id`.

    Which connector's translator is active is resolved by
    app.connectors.translator_registry.active_questionnaire_translator(),
    keyed off the same `connectors.active` config value as `Connector`
    itself.
    """

    accept: str | None

    def item_path(self, questionnaire_id: str) -> str:
        """Path for GET-by-id/PATCH/DELETE, in this backend's own convention."""
        ...

    def list_path(self) -> str:
        """Path for GET-collection (search) and POST-create, in this
        backend's own convention."""
        ...

    def list_params(
        self,
        status: str | None,
        url: str | None,
        name: str | None,
        title: str | None,
        publisher: str | None,
        identifier: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        """Canonical filter/pagination args -> this backend's own query
        param names. The filter set mirrors a subset of FHIR R4's own
        Questionnaire search parameters
        (https://hl7.org/fhir/R4/questionnaire.html#search) — the same
        subset fhir-server's own router implements today. No `tenant_id`
        filter — like every other auth-rollout resource, fhir-server
        always scopes the search to the caller's own org, derived from
        the forwarded JWT, never a client-suppliable query param."""
        ...

    def from_wire(self, raw: dict) -> dict:
        """This backend's raw response dict -> canonical FHIR Questionnaire
        (or Bundle) dict. Identity for both connectors today."""
        ...

    def to_wire_create(self, data: dict) -> dict:
        """Canonical FHIR Questionnaire dict (from FhirQuestionnaireInput)
        -> this backend's own POST-create body shape."""
        ...

    def to_wire_patch(self, data: dict) -> dict | list[dict]:
        """Canonical FHIR Questionnaire dict (from FhirQuestionnaireInput)
        -> this backend's own PATCH-update body shape."""
        ...
