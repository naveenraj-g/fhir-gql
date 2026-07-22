# Search & Filter Standards

Scope: **every filter every FHIR resource's list/search endpoint should support**, on both REST and GraphQL. This is a reference/standards document, not a feature-gap report like `01`–`09` — it defines the target filter contract that `10-resource-rollout-plan.md` and `11-implementation-roadmap.md`'s Phase 3 ("FHIR feature depth") should build toward, resource by resource, as each one gets ported.

## Current state (baseline, confirmed by reading the code)

`D:\code\work\projects\fhir\fhir-server\app\routers\patient.py`'s `list_patients` — the only list endpoint that exists anywhere in this stack today — supports exactly:

```
family_name, given_name, gender, active, user_id, org_id, limit, offset
```

No date ranges, no identifier search, no reference filters, no sorting, no total-count control. Every resource added from here on should be built against the fuller contract below from day one, rather than repeating this minimal starting point sixteen more times.

---

## 1. Universal filters (every resource, no exceptions)

These apply the same way regardless of resource type — build them once, in one shared place, not per-resource.

| Filter | Example | What it does |
|---|---|---|
| `_id` | `_id=123,456` | Filter by one or more IDs — comma = OR |
| `_lastUpdated` | `_lastUpdated=ge2024-01-01` | Filter by modification timestamp, with comparator prefixes — the basis of any "sync since X" client |
| `_sort` | `_sort=-birthdate` | Sort ascending (`field`) or descending (`-field`) on any supported field; multiple fields comma-separated for tie-breaking |
| `_count` | `_count=50` | Page size (this stack's existing `limit`) |
| `_total` | `_total=accurate\|estimate\|none` | Whether/how to compute the total count — `none` avoids a `COUNT(*)` on large tables when the client only needs the page |
| `_elements` | `_elements=id,name,gender` | Return only named fields — bandwidth saver, and the prerequisite for a lean "core fields only" fetch (flagged as a gap in the GraphQL lazy-resolver work) |
| `_summary` | `_summary=count` | `true` (summary elements only) / `text` / `data` / `count` (count only, no rows) |
| `:exact` modifier | `family:exact=Smith` | Exact string match instead of the default substring/contains behavior |
| `:contains` modifier | `family:contains=mit` | Explicit substring match (today's implicit default for `family_name`/`given_name`) |
| `:missing` modifier | `email:missing=true` | Resources where a field is absent (`true`) or present (`false`) |
| Comparator prefixes | `birthdate=ge1990-01-01` | `eq`/`ne`/`gt`/`lt`/`ge`/`le`/`sa`/`eb`/`ap` on any date/number/quantity field |
| Multi-value OR | `status=active,on-hold` | Comma-separated values on one param = OR |
| Multi-param AND | `status=active&code=123` | Repeating different params = AND (already how this stack's filters compose) |

Lower priority, apply only if a concrete need appears — full FHIR-spec compliance items, not commonly used by an in-house client:

| Filter | What it does | Why lower priority |
|---|---|---|
| `_tag` / `_security` / `_profile` / `_source` | Meta-level filtering (labels, security classification, profile conformance) | Not used unless resources carry meaningful `meta` data |
| `_text` / `_content` | Full-text search across narrative/content | Needs a text-search index (Elasticsearch-style); heavy for uncertain payoff here |
| `_has` | Reverse-chained search ("Patients that have an Observation with code=X") | Real spec-compliance work; only worth it if an external SMART client requires literal FHIR search syntax |
| Chained reference search | `general-practitioner:Practitioner.name=Smith` | Same — powerful, but a lot of query-planner work for a system that controls both ends |

---

## 2. Structural patterns that matter more than spec completeness

These aren't FHIR-spec parameter names — they're the underlying *shapes* of filter that actually get used constantly, and should be prioritized over exotic modifiers:

- **Reference filters** (`patient_id=123`, `subject_id=123`) — the single most important filter class in this entire list. Almost every clinical resource's most common query is "everything for patient X." Every resource in Groups 2–4 of the rollout plan needs this as a first-class, indexed filter from the day it's built, not retrofitted later.
- **Date ranges via paired comparator params** (`date_from`/`date_to` or FHIR-style `date=ge...&date=le...`) — every resource with a clinically meaningful date needs a *range*, not just an equality filter. A single `date=2024-01-01` filter is nearly useless clinically; "show me everything in the last 30 days" is the real use case.
- **Token search with system+code, not plain string match** — coded fields (LOINC, SNOMED, ICD-10) should filter on a `system|code` pair (e.g. `code=http://loinc.org|8480-6`), otherwise you get false-positive matches across code systems that happen to reuse a code value.
- **`_sort` and real `_total` semantics** — flat-out missing today across the board.

---

## 3. Resource-by-resource filter matrix

Every resource from `10-resource-rollout-plan.md`'s rollout groups, with its **must-have filters beyond the universal set above**. "Ref → X" means a reference filter pointing at resource X.

### Patient (exists, incomplete)

| Filter | Type | Notes |
|---|---|---|
| `family_name`, `given_name` | string | Already exist |
| `gender`, `active` | token/bool | Already exist |
| `user_id`, `org_id` | string | Already exist — tenant/identity scoping |
| `identifier` | token | Search by MRN/SSN/etc. value — **missing today, high value** |
| `birthdate` | date range | **Missing today** |
| `address`, `address-city`, `address-state`, `address-postal-code` | string | **Missing today** |
| `telecom`, `email`, `phone` | token | **Missing today** |
| `deceased` | bool | **Missing today** |
| `general-practitioner` | ref → Practitioner/Organization/PractitionerRole | Unlocks once Group 1 lands |
| `organization` | ref → Organization | Managing organization |

### Group 1 — Organization / Practitioner / PractitionerRole / Location

| Resource | Must-have filters |
|---|---|
| **Organization** | `name` (string), `identifier` (token), `type` (token), `active` (bool), `partof` (ref → Organization, parent org) |
| **Practitioner** | `name`/`family`/`given` (string), `identifier` (token, e.g. NPI), `active` (bool), `telecom` (token) |
| **PractitionerRole** | `practitioner` (ref), `organization` (ref), `role`/`specialty` (token), `location` (ref), `active` (bool) |
| **Location** | `name` (string), `address`/`address-city` (string), `type` (token), `status` (token), `organization` (ref), `partof` (ref → Location, parent location) |

### Group 2 — Scheduling / Visit cluster

| Resource | Must-have filters |
|---|---|
| **Schedule** | `actor` (ref → Practitioner/Location/PractitionerRole), `date`/`active` (range/bool), `service-type` (token) |
| **Slot** | `schedule` (ref), `status` (token: free/busy/booked), `start`/`end` (date range — non-negotiable for scheduling) |
| **Appointment** | `patient` (ref), `practitioner`/`participant` (ref), `location` (ref), `status` (token), `date`/`start` (range), `service-type` (token) |
| **Encounter** | `patient` (ref), `status` (token), `class` (token), `date`/`period` (range), `participant` (ref), `location` (ref), `service-provider` (ref → Organization) |

### Group 3 — Clinical data cluster (all need `patient`/`subject` as the primary filter)

| Resource | Must-have filters |
|---|---|
| **Observation** | `patient`/`subject` (ref — critical), `code` (token, LOINC/SNOMED), `category` (token), `date`/`effective-date` (range), `value-quantity`/`value-string`/`value-concept`, `status` (token), `encounter` (ref) |
| **Condition** | `patient` (ref), `code` (token), `clinical-status` (token), `verification-status` (token), `onset-date` (range), `recorded-date` (range), `severity` (token) |
| **MedicationRequest** | `patient` (ref), `status` (token), `intent` (token), `medication`/`code` (token), `authoredon` (date range), `requester` (ref), `encounter` (ref) |
| **ServiceRequest** | `patient` (ref), `status` (token), `code` (token), `authored` (date range), `requester` (ref), `performer` (ref), `priority` (token) |
| **DiagnosticReport** | `patient` (ref), `code` (token), `category` (token), `date`/`issued` (range), `status` (token), `result` (ref → Observation), `based-on` (ref → ServiceRequest) |
| **DocumentReference** | `patient` (ref), `type`/`category` (token), `date` (range), `status` (token), `author` (ref) |

### Group 4 — Supporting data

| Resource | Must-have filters |
|---|---|
| **HealthcareService** | `organization` (ref), `location` (ref), `service-type`/`category` (token), `active` (bool), `name` (string) |

---

## 4. Value-type reference (how each filter type should behave)

| Value type | Example | Matching behavior |
|---|---|---|
| **string** | `family=Smith` | Case-insensitive substring match by default; `:exact` modifier for exact match |
| **token** | `gender=male`, `code=http://loinc.org\|8480-6` | Exact match on code, optionally scoped to a `system` |
| **date** | `birthdate=ge1990-01-01` | Comparator-prefixed, supports ranges via repeated param |
| **number / quantity** | `value-quantity=gt5.4` | Comparator-prefixed, optionally with a unit |
| **reference** | `patient=123` or `patient=Patient/123` | Exact match against a resource's own ID; the highest-value filter type in this whole document |
| **composite** | `code-value-quantity=8480-6$gt140` | Two related values joined with `$` — spec-complete but low priority; defer unless a concrete need appears |

---

## 5. Ownership and phasing

**Ownership**: this is fhir-server's job, not fhir-gql's — filter-to-SQL compilation (token/date/reference indexing, `WHERE` clause construction) is a Postgres concern fhir-gql has no access to, same verdict as the search-engine section of `02-fhir-core-engine.md`. fhir-gql's job is exposing a **consistent** REST-query-param / GraphQL-field-argument contract that matches whatever fhir-server actually implements — which means this is a **two-repo change**: fhir-gql cannot expose a filter fhir-server hasn't built.

**Recommended build order**, per resource, as each one is ported per `10-resource-rollout-plan.md`:

1. **Reference filters** (`patient_id`, `subject_id`, etc.) — build this first, always, for every new resource. It's the highest-usage filter type by a wide margin.
2. **Date-range filters** on every clinically-relevant date field — second priority, since "recent X" / "X in this period" is the next most common query shape.
3. **Coded-value filters** (`code`, `status`, `category`) as simple exact/IN-list matches — cheap, used constantly.
4. **`_sort` and real `_total`/`_count` semantics** — currently missing across the board; worth fixing once, generically, rather than per-resource.
5. **Full FHIR modifier/comparator/chaining grammar** (`:exact`, `:missing`, chained references, `_has`, composite params) — defer unless a concrete client requirement (e.g. a SMART app expecting literal FHIR search syntax) demands actual spec compliance. This is meaningful engineering effort for a system that controls both the client and the server end to end.
