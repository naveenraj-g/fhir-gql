# Resource Rollout Plan

Scope: **which FHIR resources to add next, in what order, and how much REST vs. GraphQL work each one is** — a dimension the `01`–`09` reports don't cover, since those are about Medplum's platform *features*, not about fhir-gql's own resource coverage.

## Where this comes from

`D:\code\work\projects\fhir\fhir-gql` — the sibling project this codebase was originally sliced down from — already has **16 FHIR resources fully implemented on the REST side**: `appointment`, `condition`, `diagnostic_report`, `document_reference`, `encounter`, `healthcare_service`, `location`, `medication_request`, `observation`, `organization`, `practitioner`, `practitioner_role`, `schedule`, `service_request`, `slot`, plus a `terminology` client (code lookups, not a resource with CRUD). Every one of them already has a router, service, `fhir_client` domain client, DI module, and Pydantic schemas following the exact pattern `app/routers/patient.py` / `app/services/patient_service.py` / `app/fhir_client/patient.py` follow here — porting one is mechanical, not exploratory design work, the same way this project's initial Patient slice was ported.

**GraphQL coverage is much thinner there**: `app/gql/resolvers/` and `app/gql/types/` in the sibling project only have `patient.py` and `organization.py` (plus the two lazy/everything example files already analyzed and partially ported here). **14 of the 16 remaining resources have no GraphQL precedent at all** — adding GraphQL for those means applying the established pattern fresh (types from `strawberry.experimental.pydantic`, resolvers following `app/gql/resolvers/patient.py`'s shape), not copying existing code.

## Rollout order

Grouped by dependency — resources that other resources reference should land before their dependents, so cross-reference fields (`Patient.generalPractitioner`, `Encounter.subject`, etc.) have something real to point at instead of an opaque `{referenceType, referenceId}` pair.

### Group 1 — Who / Where (unlocks Patient's existing reference fields)

| Resource | REST source | GraphQL source | Why first |
|---|---|---|---|
| **Organization** | ✅ sibling project | ✅ sibling project (only other GraphQL precedent besides Patient) | `Patient.managingOrganization` and `Patient.generalPractitioner` (when type=Organization) already exist as opaque reference fields on the *current* `PatientResponse`/`PatientType` — this is what finally lets the `resolvedOrganization` dependent-resolver pattern (dropped when porting `patient_lazy_example.py` — see that file's docstring) get built for real. |
| **Practitioner** | ✅ sibling project | ❌ new work | `Patient.generalPractitioner` (type=Practitioner) needs this to resolve the same way. |
| **PractitionerRole** | ✅ sibling project | ❌ new work | Same reference target, third `generalPractitioner` variant. |
| **Location** | ✅ sibling project | ❌ new work | Referenced by Encounter/Appointment/Schedule in Group 2 — lands before them for the same reason Organization lands before Patient's resolved reference. |

**This group is the highest-priority next step.** It's the direct, concrete unlock for the reverse-reference/DataLoader GraphQL work flagged as **High priority** in `03-graphql-api.md` ("the moment two resources have a real reference relationship... build the first reverse-reference field together with a `strawberry.dataloader.DataLoader`") — Organization is that first real cross-resource relationship, already half-wired.

### Group 2 — Scheduling / Visit cluster

| Resource | REST source | GraphQL source | Notes |
|---|---|---|---|
| **Schedule** | ✅ sibling project | ❌ new work | A Practitioner/Location's available-time container. |
| **Slot** | ✅ sibling project | ❌ new work | Individual bookable slots within a Schedule. |
| **Appointment** | ✅ sibling project | ❌ new work | References Patient, Practitioner, Location — the reference-resolution pattern from Group 1 gets reused, not reinvented. |
| **Encounter** | ✅ sibling project | ❌ new work | The clinical "visit" resource — referenced by almost everything in Group 3, so it must land before them. |

### Group 3 — Clinical data cluster (all reference Patient + Encounter)

| Resource | REST source | GraphQL source | Notes |
|---|---|---|---|
| **Observation** | ✅ sibling project | ❌ new work | Vitals, labs — highest clinical-data volume, prioritize within this group. |
| **Condition** | ✅ sibling project | ❌ new work | Diagnoses/problem list. |
| **MedicationRequest** | ✅ sibling project | ❌ new work | Prescriptions. |
| **ServiceRequest** | ✅ sibling project | ❌ new work | Orders (labs, imaging, referrals) — already referenced by the excluded `patient_everything_example.py`, so its schema/service shape is a known quantity. |
| **DiagnosticReport** | ✅ sibling project | ❌ new work | Lab/imaging report results, typically references one or more Observations. |
| **DocumentReference** | ✅ sibling project | ❌ new work | Clinical documents/attachments. No binary-storage work needed on this side at all — FileNest (a separate, already-existing service) handles upload/storage and hands back file metadata; this resource just needs its `content.attachment` input schema to accept that same `{url, content_type, size, hash}` shape `PhotoCreateSchema` already uses — see the correction note in `07-integrations-and-media.md`. |

### Group 4 — Supporting / reference data

| Resource | REST source | GraphQL source | Notes |
|---|---|---|---|
| **HealthcareService** | ✅ sibling project | ❌ new work | Describes services a Location/Organization offers — lower traffic, no other resource depends on it. |
| **Terminology client** | ✅ sibling project (client-only, no CRUD) | n/a | Code-system lookups (`$lookup`, `$validate-code`, `$expand`) — see `11-fhir-standard-features-roadmap.md` for whether this belongs in fhir-gql or fhir-server. Not a resource with its own REST/GraphQL CRUD surface, so it doesn't fit the group-1–3 dependency ordering. |

## Per-resource checklist (repeat for every resource above)

Mirrors exactly how Patient was built, per `README.md`'s "Extending with another resource" section:

1. **Port REST**: copy the sibling project's `app/{routers,services,fhir_client,schemas,di/modules,di/dependencies}/<resource>.py`, adjust imports/DI wiring to match this project's `Container` (`core=core` pattern in `app/di/container.py`).
2. **Register REST**: add to `app/routers/__init__.py`.
3. **Design GraphQL** (new work for everything except Organization): `app/gql/types/<resource>.py` (types from `strawberry.experimental.pydantic`, following `app/gql/types/patient.py`'s leaf-types-first declaration order) + `app/gql/resolvers/<resource>.py` (Query/Mutation mixins, following `app/gql/resolvers/patient.py`'s RBAC-check-then-call-service shape).
4. **Register GraphQL**: mix the new Query/Mutation classes into `app/gql/schema.py`.
5. **Wire cross-references where they exist** (Group 1 unlocks this for Patient; each later group unlocks it for its own dependents): add a dependent/hierarchical resolver field following the `resolvedOrganization` pattern documented (but not built) in `app/gql/types/patient_lazy_example.py`.
6. **Enforce `org_id`/tenant scoping consistently on every new resource's by-id routes from day one** — don't repeat the gap flagged in `02-fhir-core-engine.md` and `06-admin-and-multitenancy.md` for Patient; bake the fix into the pattern going forward rather than retrofitting sixteen resources later.

## What's explicitly NOT in this rollout

`Bot`, `ClientApplication`, `Project`, `ProjectMembership`, `Subscription`, `AsyncJob`, `Binary`, `Media`, `AuditEvent`, `CodeSystem`/`ValueSet`/`ConceptMap`/`StructureDefinition` (FHIR's own definitional/terminology resources) are all **infrastructure resources**, not clinical-data resources — they're covered by the platform-feature roadmap (`10-implementation-roadmap.md`) and the individual `01`–`09` reports, not by this resource-rollout list, since adding them isn't "port a REST+GraphQL CRUD slice," it's "build a subsystem" (auth, subscriptions, bulk export, terminology service).
