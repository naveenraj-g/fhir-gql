"""
EXAMPLE / reference file — demonstrates GraphQL field-level lazy resolution
and independent (parallel) sibling resolvers for the Patient resource.

This is a companion to app/gql/types/patient.py, not a replacement for it.
That file's `PatientType` derives every field — including all nine
sub-resource arrays — from one `PatientResponse` dict via
`strawberry.experimental.pydantic`, so the arrays are populated eagerly
regardless of what the client's GraphQL query actually selects. Fine for the
pilot; doesn't scale once a Patient's sub-resource data is large:
`patient(id) { name }` still pays for telecom/address/photo/contact/
communication/generalPractitioner/link every time, because the whole object
is built from one big dict up front.

`PatientLazyType` fixes that by making every sub-resource array its own
`@strawberry.field` resolver *method* instead of a plain dataclass field.
Strawberry (via graphql-core) only invokes a field's resolver if the
client's query actually selects that field: ask for `name`, only `name`'s
resolver runs and only `list_names()` gets called; skip `contact`,
`list_contacts()` never fires. This is why the business-logic import that
every other `app/gql/types/*.py` file avoids (get_container,
require_gql_permission — normally resolver-only concerns) shows up here:
a lazy field's resolver has to run the same RBAC-check-then-call-service
sequence a real resolver does, since it IS a resolver, just attached to a
type instead of to Query/Mutation directly.

INDEPENDENT / parallel execution falls out of this for free, with no manual
orchestration code written anywhere: `name`, `identifier`, `telecom`, etc.
below are async resolvers, none reading another's result — only `self.id`,
set once from the core fetch. Request `{ name identifier telecom }` together
and graphql-core's executor awaits all three concurrently, because that's
how it schedules sibling fields of the same selection set when their
resolvers are coroutines. No asyncio.gather to write.

NOT demonstrated here: the DEPENDENT/hierarchical pattern (a nested field
whose resolver reads values already produced by its own parent field's
resolver, so GraphQL enforces execution order by construction — the child
necessarily runs after the parent, never before or concurrently with it).
The reference project's only example of that pattern followed a Patient's
`generalPractitioner` reference to the actual `Organization` record it
points at — Organization isn't part of this patient-only slice, so that
piece is intentionally omitted here. When Organization is added, the
natural place for it is a `resolvedOrganization` field on
`PatientGeneralPractitionerType` (app/gql/types/patient.py): read
`self.reference_id`/`self.reference_type`, call
`org.organization_service()`, return `Optional[OrgType]` — same shape as
every lazy field below, just nested one level deeper.

CAVEAT, stated plainly: the top-level `patientLazy` resolver (see
app/gql/examples/patient_lazy_resolvers.py) still calls
`PatientService.get_by_id()`, which — per the existing service/client
contract — returns the full Patient *including* all nine sub-resource
arrays already embedded, because there is currently no leaner "core fields
only" fetch on PatientService/PatientClient. This file discards those
embedded arrays and re-fetches each one on demand via list_names()/
list_identifiers()/etc. instead. So today this demonstrates the
resolver-shape and concurrency mechanics correctly, but does NOT yet reduce
fhir-server load for the common case of a client asking for scalar fields
plus only one or two sub-resources — realizing that savings needs a
genuinely lean core-only fetch added to PatientService (e.g. a FHIR
`_elements`-style partial fetch), which is a service-layer change outside
this file's scope. Once that method exists, only the one line inside
`patient_lazy()` needs to change — every resolver below already works.
"""

from typing import List, Optional

import strawberry

from app.gql.context import get_container
from app.gql.patient.types.types import (
    PatientAddressType,
    PatientCommunicationType,
    PatientContactType,
    PatientGeneralPractitionerType,
    PatientIdentifierType,
    PatientLinkType,
    PatientNameType,
    PatientPhotoType,
    PatientTelecomType,
)
from app.gql.permissions import require_gql_permission
from app.schemas.patient.response import (
    PatientAddressResponse,
    PatientCommunicationResponse,
    PatientContactResponse,
    PatientGeneralPractitionerResponse,
    PatientIdentifierResponse,
    PatientLinkResponse,
    PatientNameResponse,
    PatientPhotoResponse,
    PatientTelecomResponse,
)


@strawberry.type(
    description=(
        "Same data as PatientType, but every sub-resource array is its own lazy "
        "field resolver instead of a plain field — see this module's docstring for "
        "why. Scalar fields are populated eagerly from the core fetch; name/"
        "identifier/telecom/address/photo/contact/communication/generalPractitioner/"
        "link only hit the fhir-server if the client's query actually selects them."
    )
)
class PatientLazyType:
    """Lazy-resolver counterpart to PatientType — see module docstring."""

    id: int
    user_id: Optional[str]
    org_id: Optional[str]
    active: Optional[bool]
    gender: Optional[str]
    birth_date: Optional[str]
    deceased_boolean: Optional[bool]
    deceased_datetime: Optional[str]
    marital_status_system: Optional[str]
    marital_status_code: Optional[str]
    marital_status_display: Optional[str]
    marital_status_text: Optional[str]
    multiple_birth_boolean: Optional[bool]
    multiple_birth_integer: Optional[int]
    managing_organization_type: Optional[str]
    managing_organization_id: Optional[int]
    managing_organization_display: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    created_by: Optional[str]
    updated_by: Optional[str]

    @classmethod
    def from_core_dict(cls, data: dict) -> "PatientLazyType":
        """Builds the scalar-only half of a Patient from the raw fhir-server dict, deliberately ignoring the embedded sub-resource arrays (see module docstring caveat) since each is re-fetched lazily by its own field resolver below."""
        return cls(
            id=data["id"],
            user_id=data.get("user_id"),
            org_id=data.get("org_id"),
            active=data.get("active"),
            gender=data.get("gender"),
            birth_date=data.get("birth_date"),
            deceased_boolean=data.get("deceased_boolean"),
            deceased_datetime=data.get("deceased_datetime"),
            marital_status_system=data.get("marital_status_system"),
            marital_status_code=data.get("marital_status_code"),
            marital_status_display=data.get("marital_status_display"),
            marital_status_text=data.get("marital_status_text"),
            multiple_birth_boolean=data.get("multiple_birth_boolean"),
            multiple_birth_integer=data.get("multiple_birth_integer"),
            managing_organization_type=data.get("managing_organization_type"),
            managing_organization_id=data.get("managing_organization_id"),
            managing_organization_display=data.get("managing_organization_display"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            created_by=data.get("created_by"),
            updated_by=data.get("updated_by"),
        )

    # ── Lazy sub-resource fields — INDEPENDENT / parallel ────────────────────
    # None of the resolvers below reads another field's result — each only
    # uses `self.id`, set once above from the core fetch. Request several of
    # these together in one query and graphql-core's executor awaits them
    # concurrently, since each is `async def` and they belong to the same
    # selection set. That concurrency is not something written here; it is
    # graphql-core's default behaviour for sibling async field resolvers.

    @strawberry.field(
        description="This Patient's HumanName entries. Lazily fetched via list_names() only if selected. Requires `patient:read`."
    )
    async def name(self, info: strawberry.types.Info) -> List[PatientNameType]:
        actor = require_gql_permission(info, "patient", "read")
        service = get_container(info).patient.patient_service()
        data = await service.list_names(self.id, actor)
        return [
            PatientNameType.from_pydantic(PatientNameResponse.model_validate(item))
            for item in data["data"]
        ]

    @strawberry.field(
        description="This Patient's Identifier entries. Lazily fetched via list_identifiers() only if selected. Requires `patient:read`."
    )
    async def identifier(
        self, info: strawberry.types.Info
    ) -> List[PatientIdentifierType]:
        actor = require_gql_permission(info, "patient", "read")
        service = get_container(info).patient.patient_service()
        data = await service.list_identifiers(self.id, actor)
        return [
            PatientIdentifierType.from_pydantic(
                PatientIdentifierResponse.model_validate(item)
            )
            for item in data["data"]
        ]

    @strawberry.field(
        description="This Patient's telecom (ContactPoint) entries. Lazily fetched via list_telecom() only if selected. Requires `patient:read`."
    )
    async def telecom(self, info: strawberry.types.Info) -> List[PatientTelecomType]:
        actor = require_gql_permission(info, "patient", "read")
        service = get_container(info).patient.patient_service()
        data = await service.list_telecom(self.id, actor)
        return [
            PatientTelecomType.from_pydantic(
                PatientTelecomResponse.model_validate(item)
            )
            for item in data["data"]
        ]

    @strawberry.field(
        description="This Patient's Address entries. Lazily fetched via list_addresses() only if selected. Requires `patient:read`."
    )
    async def address(self, info: strawberry.types.Info) -> List[PatientAddressType]:
        actor = require_gql_permission(info, "patient", "read")
        service = get_container(info).patient.patient_service()
        data = await service.list_addresses(self.id, actor)
        return [
            PatientAddressType.from_pydantic(
                PatientAddressResponse.model_validate(item)
            )
            for item in data["data"]
        ]

    @strawberry.field(
        description="This Patient's photo Attachments. Lazily fetched via list_photos() only if selected. Requires `patient:read`."
    )
    async def photo(self, info: strawberry.types.Info) -> List[PatientPhotoType]:
        actor = require_gql_permission(info, "patient", "read")
        service = get_container(info).patient.patient_service()
        data = await service.list_photos(self.id, actor)
        return [
            PatientPhotoType.from_pydantic(PatientPhotoResponse.model_validate(item))
            for item in data["data"]
        ]

    @strawberry.field(
        description="This Patient's contact people. Lazily fetched via list_contacts() only if selected. Requires `patient:read`."
    )
    async def contact(self, info: strawberry.types.Info) -> List[PatientContactType]:
        actor = require_gql_permission(info, "patient", "read")
        service = get_container(info).patient.patient_service()
        data = await service.list_contacts(self.id, actor)
        return [
            PatientContactType.from_pydantic(
                PatientContactResponse.model_validate(item)
            )
            for item in data["data"]
        ]

    @strawberry.field(
        description="This Patient's communication/language preferences. Lazily fetched via list_communications() only if selected. Requires `patient:read`."
    )
    async def communication(
        self, info: strawberry.types.Info
    ) -> List[PatientCommunicationType]:
        actor = require_gql_permission(info, "patient", "read")
        service = get_container(info).patient.patient_service()
        data = await service.list_communications(self.id, actor)
        return [
            PatientCommunicationType.from_pydantic(
                PatientCommunicationResponse.model_validate(item)
            )
            for item in data["data"]
        ]

    @strawberry.field(
        description="This Patient's generalPractitioner references. Lazily fetched via list_general_practitioners() only if selected. Requires `patient:read`."
    )
    async def general_practitioner(
        self, info: strawberry.types.Info
    ) -> List[PatientGeneralPractitionerType]:
        actor = require_gql_permission(info, "patient", "read")
        service = get_container(info).patient.patient_service()
        data = await service.list_general_practitioners(self.id, actor)
        return [
            PatientGeneralPractitionerType.from_pydantic(
                PatientGeneralPractitionerResponse.model_validate(item)
            )
            for item in data["data"]
        ]

    @strawberry.field(
        description="This Patient's links to other Patient/RelatedPerson records. Lazily fetched via list_links() only if selected. Requires `patient:read`."
    )
    async def link(self, info: strawberry.types.Info) -> List[PatientLinkType]:
        actor = require_gql_permission(info, "patient", "read")
        service = get_container(info).patient.patient_service()
        data = await service.list_links(self.id, actor)
        return [
            PatientLinkType.from_pydantic(PatientLinkResponse.model_validate(item))
            for item in data["data"]
        ]
