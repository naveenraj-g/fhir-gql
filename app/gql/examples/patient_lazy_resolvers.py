"""
EXAMPLE / reference resolvers — companion to
app/gql/examples/patient_lazy_types.py. See that module's docstring for the
sub-resource-level mechanics (field-level lazy resolution) and its one
honest caveat (the core fetch below still calls `get_by_id()`/`list()`,
which already return every sub-resource array server-side — see that
docstring for why, and what a real fix would need).

This file holds TWO query fields that contrast the two shapes the same
lazy sub-resource resolvers behave in, depending on whether the parent ID is
already known or not:

  1. `patientLazy(patientId: ...)` — PURE PARALLEL. The caller already
     supplies the one thing every sub-resource resolver needs (`self.id`),
     as a query argument. So `name`, `identifier`, `telecom`, ... have
     nothing left to wait on and nothing they depend on each other for —
     graphql-core resolves all of them concurrently the moment they're
     selected together.

        query {
          patientLazy(patientId: 1) {
            id
            gender
            name { family given }
            generalPractitioner { referenceType referenceId }
          }
        }

  2. `patientsLazy(...)` — DEPENDENT AT LIST SCALE. There is no single
     `patientId` argument here; the caller only knows filters (name,
     limit, offset). Each Patient's own `id` doesn't exist yet from the
     caller's point of view — it only becomes known once `service.list()`
     resolves and hands back that Patient's row. Every sub-resource
     resolver for *that* Patient object (still the exact same `name`/
     `identifier`/etc. methods on PatientLazyType — no new type needed)
     necessarily runs after its own parent Patient has resolved, since it
     reads that Patient's `self.id`. This is the scenario your boss is
     describing: fetching "all user data" means each patient's
     sub-resource fetches are gated behind that one patient's own ID
     coming back from the list first — a real parent → child dependency,
     repeated once per list item — not a single independent lookup like
     case 1.

        query {
          patientsLazy(limit: 5) {
            id
            name { family given }
            identifier { value }
          }
        }

     Two concurrency levels still apply here, both free/automatic:
       - Within one Patient, `name` and `identifier` are still siblings —
         concurrent with each other, exactly like case 1, once that
         Patient's id is known.
       - Across different Patients in the list, graphql-core resolves each
         list item's subtree independently too, so patient #1's `name`
         fetch and patient #2's `name` fetch also run concurrently with
         each other, not one-list-item-at-a-time.

     What this does NOT solve, and is worth flagging plainly: none of that
     concurrency collapses *repeated* calls. `patientsLazy(limit: 50) {
     name }` still fires `list_names()` once per patient — 50 separate
     fhir-server calls, just running concurrently rather than serially.
     That's the classic GraphQL N+1 problem. The standard fix is a
     `strawberry.dataloader.DataLoader` that batches same-tick `list_names`
     calls by patient id into one request — not implemented here since it
     wasn't asked for, but it's the natural next step once this list field
     sees real traffic.
"""

from typing import List, Optional

import strawberry

from app.gql.context import get_container
from app.gql.errors import translate_errors
from app.gql.examples.patient_lazy_types import PatientLazyType
from app.gql.permissions import require_gql_permission
from app.schemas.patient.input import ListPatientsSchema


@strawberry.type(
    description=(
        "EXAMPLE query fields demonstrating lazy/dependent/parallel resolver "
        "composition for Patient — see app/gql/examples/patient_lazy_types.py."
    )
)
class PatientLazyQuery:
    """Mixed into the root Query type in app/gql/schema.py, alongside — not instead of — PatientQuery."""

    @strawberry.field(
        description=(
            "EXAMPLE field — PURE PARALLEL case. `patientId` is already known as an "
            "argument, so every sub-resource (name, identifier, telecom, address, "
            "photo, contact, communication, generalPractitioner, link) is resolved "
            "lazily and independently of the others — only fetched if the client's "
            "query actually selects it, and all selected ones run concurrently. See "
            "app/gql/examples/patient_lazy_types.py and this module's docstring for "
            "the full explanation. Requires the `patient:read` permission."
        )
    )
    @translate_errors
    async def patient_lazy(self, info: strawberry.types.Info, patient_id: int) -> PatientLazyType:
        """EXAMPLE resolver — core-only fetch; see module docstring for the get_by_id() caveat."""
        actor = require_gql_permission(info, "patient", "read")
        service = get_container(info).patient.patient_service()
        core = await service.get_by_id(patient_id, actor)
        return PatientLazyType.from_core_dict(core)

    @strawberry.field(
        description=(
            "EXAMPLE field — DEPENDENT-AT-LIST-SCALE case. Lists Patients first (one "
            "service.list() call that doesn't need any single patient's id up front), "
            "then for each Patient returned, every sub-resource field is resolved "
            "lazily against THAT patient's own id — which only exists once this list "
            "has already produced it, so each patient's sub-resource fetches "
            "necessarily run after that patient's own row has resolved. Sub-resources "
            "within one patient, and across different patients, still run "
            "concurrently with each other — see this module's docstring for the "
            "N+1 caveat this pattern doesn't solve on its own. Requires the "
            "`patient:read` permission."
        )
    )
    @translate_errors
    async def patients_lazy(
        self,
        info: strawberry.types.Info,
        family_name: Optional[str] = None,
        given_name: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[PatientLazyType]:
        """EXAMPLE resolver — lists Patients, then hands each row to the same lazy sub-resource resolvers `patientLazy` uses."""
        actor = require_gql_permission(info, "patient", "read")
        service = get_container(info).patient.patient_service()
        filters = ListPatientsSchema(family_name=family_name, given_name=given_name, limit=limit, offset=offset)
        data = await service.list(filters, actor)
        # Each item only becomes a usable `self.id` for the sub-resource
        # resolvers below at this point — before this line, no individual
        # patient id existed for any of them to depend on.
        return [PatientLazyType.from_core_dict(item) for item in data["data"]]
