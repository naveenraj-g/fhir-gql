# Workflow & Business-Logic Placement

Scope: **where does a given business rule live**, as more FHIR resources land and each one's
`Service` accumulates validation beyond plain CRUD. This is a different question from
`10-resource-rollout-plan.md` (which resource to add next) — it's about keeping rule placement
consistent once a resource's `Service` has more than one kind of rule to enforce, so the answer
isn't "wherever it was easiest to add that day."

## The three tiers

Every business rule in this codebase falls into exactly one of these:

1. **Same-resource rules** — the resource validates itself, or a reference to another instance of
   its own kind. Only ever needs that resource's own `Client`/`Service`. Lives as a private helper
   method on that resource's `Service`, called from `create`/`update`.
   Examples already in the codebase: `OrganizationsService.register()`'s dedup-by-name check,
   `OrganizationsService._validate_partof()` (Organization referencing a parent Organization —
   see worked example below), `PatientService._require_patch_payload()`.

2. **Cross-resource orchestration rules** — a workflow spans two or more resource *domains*
   (e.g. booking an appointment needs Patient + Practitioner + Schedule + facility-matching). No
   single resource's `Service` should reach into another resource's `Client`/`Service` to do this —
   it creates awkward, direction-dependent coupling between resources that are otherwise peers, and
   risks the same rule being re-implemented slightly differently in the REST router vs. the GraphQL
   resolver if it isn't centralized in one place both transports call through.
   **Not yet needed** — no resource pair in this codebase requires cross-domain orchestration yet.
   See "Anticipated next case" below for where this goes once one does.

3. **Cross-cutting reusable rules** — the identical *shape* of check needed by 2+ resources'
   `Service`s independently (not a workflow spanning resources — the same rule, repeated).
   Candidate to lift out of the first resource that implemented it into a shared helper once a
   second resource needs the same thing, rather than copy-pasting.
   Current candidate: `OrganizationsService._check_ownership()` (fetch-then-compare `org_id`
   ownership check) is private to Organization today. The moment a second resource needs the same
   tenant-ownership pattern on its by-id routes — Patient is the obvious next one, see the gap
   `06-admin-and-multitenancy.md` already flagged — lift it into a shared helper (e.g.
   `app/services/tenant_scope.py`) both `PatientService` and `OrganizationsService` call, rather than
   duplicating the fetch-and-compare logic a second time.

## Worked example: Organization's `partof` (tier 1)

Organization's `partof` field is a FHIR reference to a parent Organization (e.g.
`"Organization/190001"`). This looked at first like it might need cross-resource orchestration, but
it doesn't — validating it only ever needs `OrganizationClient` (Organization referencing
Organization), so it's tier 1, and it lives in `app/services/organization_service.py`:

- `_validate_partof(partof, actor)` parses the reference, fetches the parent via
  `self._client.get_by_id(...)`, and reuses `_check_ownership` so a parent belonging to a different
  tenant is rejected the same way any other cross-tenant lookup is (404, not 403 — a caller can't
  distinguish "wrong tenant" from "doesn't exist" by probing ids).
- Called from `register()` only when `dto.partof is not None`.
- **No cycle detection** (walking the ancestor chain to prevent A→B→A) is implemented, because none
  is needed: `partof` is create-only — `PatchOrgSchema` never exposes it, only the free-text
  `partof_display` is patchable — and a brand-new organization has no id yet at validation time, so
  it structurally cannot reference itself or anything that could reference it back. If `partof` is
  ever made patchable (re-parenting), *that* is the point at which this method needs an
  ancestor-chain walk added — don't add it speculatively before that's a real requirement.

## Anticipated next case: Appointment booking (tier 2)

Per `10-resource-rollout-plan.md`'s Group 2 (Schedule → Slot → Appointment → Encounter), booking an
appointment is the first rule that will actually need tier 2:

- Patient exists and is in the caller's tenant.
- Practitioner/PractitionerRole exists, is active, and (per the Group 1 unlock) resolves to a real
  Organization/facility.
- The requested Slot is free and belongs to a Schedule for that Practitioner/Location.
- HealthcareService (if specified) is actually offered at that facility — the "PractitionerRole
  facility matching" rule from the original conversation that prompted this doc.

None of this belongs inside `AppointmentService` reaching into `PatientClient`/`PractitionerClient`
directly. When Schedule/Slot/Appointment land, introduce a new **`app/workflows/`** package —
one module per workflow (e.g. `app/workflows/book_appointment.py`), DI-injected via its own
`WorkflowContainer` (or provider group) with the several resource `Service`s it needs
(`PatientService`, `PractitionerService`, `ScheduleService`, `SlotService`, ...). Routers/resolvers
for compound operations call the workflow; routers/resolvers for that resource's own plain CRUD
keep calling its resource `Service` directly, exactly as today.

## Rollout guidance

Extend `10-resource-rollout-plan.md`'s per-resource checklist (item 6, tenant scoping) with one more
step: **as each resource's `Service` is written, classify every validation it needs into one of the
three tiers above** — same-resource logic goes in that `Service`; anything needing another
resource's `Client`/`Service` waits for (or joins) `app/workflows/`; anything duplicated across two
resources' `Service`s gets lifted into a shared helper at the point of the *second* duplication, not
before. Don't build `app/workflows/` speculatively ahead of Group 2 landing — the first real tier-2
case is what should shape its actual DI/module structure, not a guess made now.
