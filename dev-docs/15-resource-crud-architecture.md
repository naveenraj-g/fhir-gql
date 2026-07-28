# Resource CRUD architecture: what every resource exposes, and why

The endpoint shape every FHIR resource in this project should follow — decided once, here, so
every future resource (and every review of an existing one) can check itself against one rule
instead of re-litigating it per resource. Route-level (REST + GraphQL) and database-level
(fhir-server), for both the parent resource and its sub-resource arrays (identifiers, telecom,
addresses, qualifications, availability windows, etc.).

## The rule, in one table

| Operation | Parent resource | Sub-resource (array item) | Bulk/"full" variant |
|---|---|---|---|
| **Create** | `POST /resource` — scalar/core fields only | `POST /resource/{id}/sub` — own endpoint per sub-resource type | `POST /resource/full` — parent + any combination of sub-resource arrays, atomically, in one fhir-server transaction |
| **Update** | `PATCH /resource/{id}` — scalar/core fields only | `PATCH /resource/{id}/sub/{sub_id}` — own endpoint, edits one item in place | **None.** No bulk `update_full`. |
| **Delete** | `DELETE /resource/{id}` — deletes the resource *and cascades to every sub-resource row* | `DELETE /resource/{id}/sub/{sub_id}` — deletes one item, resource and every other item untouched | **None.** No separate "full delete" — the parent delete already cascades. |

Same shape for every resource, whether it's a small one (Organization: 7 sub-resource types) or a
large one (Practitioner: 7; Patient: 9). GraphQL mirrors this 1:1 — one mutation per REST endpoint,
no extra design decision at that layer; see any `app/gql/<resource>/mutations.py` for the pattern.

## Why `create_full` exists but `update_full`/"full delete" don't

**Create** is the one place a bulk/atomic endpoint earns its keep: a brand-new parent has no
children yet, so "create the parent and an initial batch of children in one transaction" is a
real, common need (e.g. registering a Practitioner along with their first name/telecom/address in
one call from a signup form) — and if any part fails, nothing is left half-created.

**Update** doesn't have the same justification once per-item endpoints exist. A bulk
`update_full` that replaces whole sub-resource arrays (the pattern Patient and Practitioner
currently expose — see below) can only implement "replace" semantics: delete every existing row
for that array and insert the new list from scratch. That's strictly worse than per-item PATCH
once per-item endpoints exist:
- **Audit trail is destroyed.** Every row gets a new id and a fresh `created_by`/`updated_by`,
  even for the 9 out of 10 items that didn't actually change. Per-item PATCH updates the one row
  that changed and leaves the other nine with their original history intact.
- **No real advantage in exchange.** The one thing bulk-replace buys you — one network round trip
  for many changes — isn't worth losing per-item identity/audit for a resource type. If a
  front-end genuinely needs to change five telecom entries at once, five PATCH calls (or a
  client-side batching/transaction if that ever becomes a real requirement) is the honest cost of
  keeping every change individually attributable.

**Delete** doesn't need a bulk/full variant for a different reason: it isn't needed, because plain
delete already does the whole job. Every sub-resource table's foreign key relationship to its
parent is declared with `cascade="all, delete-orphan"` at the ORM level in fhir-server (confirmed
for Organization — `app/models/organization/organization.py` in the fhir-server repo declares this
on every one of its seven child relationships: identifiers, types, aliases, telecom, addresses,
contacts, endpoints). Deleting the parent row therefore already deletes every child row in the
same transaction — there is nothing a "full delete" endpoint could do that the plain
`DELETE /resource/{id}` doesn't already do.

## Current state vs. this policy

Patient and Practitioner (the first two resources built, before this rule was made explicit) each
expose an `update_full`/`patch_full` bulk-array-replace endpoint *in addition to* their per-item
endpoints — two different ways to change the same sub-resource array. That's legacy, not the
pattern to keep copying: every resource ported after this doc (Organization, Location,
HealthcareService, PractitionerRole, Schedule, Slot, and anything future) should follow the table
above — `create` + `create_full`, but only per-item `update`/`delete`, no bulk update or bulk
delete. Patient/Practitioner's existing `update_full` isn't being ripped out retroactively, it's
just not a precedent to extend to new resources.

## Checklist for porting/reviewing a resource against this rule

- [ ] Parent `create`/`update` schemas only ever contain scalar/core fields — no sub-resource
      arrays on the plain create, only on `*_full`.
- [ ] Every sub-resource array has its own `POST`/`PATCH`/`DELETE` REST endpoints
      (`/resource/{id}/sub`, `/resource/{id}/sub/{sub_id}`).
- [ ] A `create_full` endpoint exists if the resource has any sub-resource arrays at all, atomic
      in one fhir-server transaction.
- [ ] No `update_full`/bulk-PATCH endpoint is added for new resources.
- [ ] No separate "full delete" endpoint — confirm the fhir-server model's child relationships
      declare `cascade="all, delete-orphan"` (or the equivalent explicit delete-children-first
      logic in the repository, if cascade isn't used) so plain delete is provably complete.
- [ ] Reference fields (`part_of`, `provided_by`, etc.) are patchable only when real-world
      reassignment is a genuine operation on the same record — see
      `dev-docs/13-workflow-orchestration.md` and the per-resource Service docstrings for the
      reasoning already applied to Organization/Location/HealthcareService.
- [ ] GraphQL exposes exactly one mutation per REST endpoint from the table above — no additional
      GraphQL-only bulk operations invented at that layer.
