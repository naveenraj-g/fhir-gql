# Connector capabilities: FHIR operations and search (Organization and Location)

What each backend connector really supports for **Organization** and **Location**: first the HTTP/FHIR operations
(read, search, create, PUT, PATCH, delete), then every FHIR search parameter (common ones first, then the
resource-specific ones), with how each backend behaves.

- Last verified: **2026-11-18**.
- Connectors covered: `internal` (our fhir-server), `medplum`, `openemr`, `epic`, `oracle_health`.
- Purpose: reference for the team discussion about a common connector contract. It describes what the backends do today; it does
  not propose anything.

## 0. How to read this document

**Symbols**

| Symbol | Meaning |
|---|---|
| ✅ | Supported as FHIR R4 specifies |
| ⚠️ | Partly supported, or behaves differently from the spec (explained in the notes under the table) |
| ❌ | Not supported (the cell says what happens instead) |
| ❓ | Not verified: no evidence either way |

**What "not supported" looks like.** Each backend reacts differently when it gets something it does not support. This is
the most important thing to know when using a connector:

| Wording in the cells | What the backend does |
|---|---|
| `ignored` | Returns 200 and silently drops the parameter. The result is **unfiltered**. |
| `ignored + warning` | Same, but adds a Bundle entry with `search.mode = outcome` (an `OperationOutcome`) saying "Unknown parameter: X. Parameter has been ignored." |
| `400` | Rejects the request with a client error (what FHIR R4 asks servers to do for unsupported modifiers). |
| `empty` | Returns **zero results** instead of ignoring the parameter (OpenEMR Location). |
| `500` | The backend itself fails (OpenEMR bugs). |

**Evidence.** Every statement comes from one of these (listed per connector in section 1, and in the links in section 6):

- **(L) live**: tested on 2026-11-18 against the running backend, through our connector.
- **(D) documentation**: the vendor's docs or the server's own CapabilityStatement (`/metadata`).
- **(C) code**: our `fhir-server` source (it was not started for this exercise).

Sandbox data is test data and counts can change. The tests used a non-matching value to see whether a parameter filters
(`zzzqq9`) and compared against a baseline search. Medplum's local instance was empty, so five labelled test records were
created, tested and **deleted again**.

## 1. Connectors at a glance

| Connector | Backend | Auth (gateway to backend) | Base URL used | Evidence |
|---|---|---|---|---|
| `internal` | Our `fhir-server` (FastAPI, FHIR R4, content-based storage) | `token_passthrough` (forwards the caller's JWT) | `http://localhost:8001/api/fhir/v1` (`/organizations`, `/locations`) | (C) source, plus its CLAUDE.md |
| `medplum` | Medplum server (FHIR R4 4.0.1), local Docker | `client_secret` (id and secret in the form body) | `http://localhost:8103/fhir/R4` | (L) + (D) `/metadata` |
| `openemr` | OpenEMR standard FHIR API (4.0.1), local Docker | `private_key_jwt` with **system scopes** | `http://localhost/apis/default/fhir` | (L) + (D) `/metadata`, Swagger |
| `epic` | Epic on FHIR public sandbox (R4) | `private_key_jwt` | `https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4` | (L) + (D) `/metadata` |
| `oracle_health` | Oracle Health (Cerner Millennium) FHIR R4, public sandbox tenant | `client_secret` (HTTP Basic) or `private_key_jwt` | `https://fhir-ehr-code.cerner.com/r4/<tenant>` | (L) + (D) docs, `/metadata` |

Abbreviations used in the tables: **INT** = internal, **MED** = medplum, **OEM** = openemr, **EPI** = epic, **ORA** = oracle_health.

## 2. Operations

Sources: the CapabilityStatement of each backend (`/metadata`, (D)), HL7 FHIR R4 RESTful API
([restful.html](https://hl7.org/fhir/R4/http.html)), and live calls (L). INT is from the router source (C):
`app/routers/organization/core.py`, `app/routers/location/core.py`.

### 2.1 Organization

| Operation | INT | MED | OEM | EPI | ORA |
|---|---|---|---|---|---|
| **Read** `GET [base]/Organization/{id}` | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Search** `GET [base]/Organization?...` | ✅ | ✅ | ✅ | ⚠️ only `_id` (and `_count`); any other search is a 400 "Only an _ID search is allowed" | ✅ (restrictive, see section 3) |
| **Search** `POST [base]/Organization/_search` | ✅ | ✅ accepted (200) | ✅ | ✅ | ✅ |
| **Create** `POST [base]/Organization` | ✅ | ✅ | ⚠️ endpoint exists, but needs an admin **user** login (`user/Organization.write`). A system-scope token gets 401 | ❌ read-only | ✅ needs scope `system/Organization.write`; a duplicate name gives 409 |
| **Update** `PUT [base]/Organization/{id}` | ❌ no PUT route | ✅ | ⚠️ endpoint exists, same user-login limit as create | ❌ | ❌ |
| **Patch** `PATCH [base]/Organization/{id}` | ✅ merge-patch on top-level elements | ✅ JSON Patch (RFC 6902) | ❌ | ❌ | ❌ |
| **Delete** `DELETE [base]/Organization/{id}` | ✅ | ✅ | ❌ 404, no route | ❌ | ❌ |
| **vread / history** | ❌ | ✅ (`vread`, `history-instance`) | ❌ | ❌ (`readHistory: false`) | ❌ |
| **Conditional create / update / delete** | ❌ | ✅ (conditionalCreate, conditionalUpdate, conditionalDelete: single) | ❌ | ❌ (`not-supported`) | ❌ |

### 2.2 Location

| Operation | INT | MED | OEM | EPI | ORA |
|---|---|---|---|---|---|
| **Read** `GET [base]/Location/{id}` | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Search** `GET [base]/Location?...` | ✅ | ✅ | ✅ (very few parameters, see quirks) | ⚠️ needs at least one parameter besides `status` | ⚠️ needs at least one qualifying parameter (e.g. `address-state`; `name` alone is a 400) |
| **Search** `POST [base]/Location/_search` | ✅ | ✅ accepted (200) | ✅ | ✅ | ✅ |
| **Create** | ✅ | ✅ | ❌ no route | ❌ | ❌ |
| **Update** (PUT) | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Patch** | ✅ merge-patch | ✅ JSON Patch | ❌ | ❌ | ❌ |
| **Delete** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **vread / history** | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Conditional create / update / delete** | ❌ | ✅ | ❌ | ❌ | ❌ |

### 2.3 What our GraphQL mutations do on each connector

The GraphQL gateway has three write mutations per resource. Each connector maps them like this (verified live where the
backend is reachable):

| GraphQL | INT | MED | OEM | EPI | ORA |
|---|---|---|---|---|---|
| `createFhirOrganization` | `POST /organizations` | `POST /Organization` | **405** (local, connector read-only) | **405** (local) | `POST /Organization` ✅ (verified: created id 3690655) |
| `createFhirLocation` | `POST /locations` | `POST /Location` | 405 | 405 | 405 |
| `updateFhirOrganization` / `...Location` | `PATCH` with a plain partial object (merge-patch) | `PATCH` with a JSON Patch array (built by `app/connectors/medplum/json_patch.py`) | 405 | 405 | 405 |
| `deleteFhirOrganization` / `...Location` | `DELETE` | `DELETE` | 405 | 405 | 405 |

"405 (local)" means our connector answers without calling the backend, because the backend cannot do it. The GraphQL
schema still lists these mutations whichever connector is active.

### 2.4 Using PUT to emulate PATCH

Some backends offer `PUT` (replace the whole resource) but no `PATCH`. A connector can emulate a patch by **fetching the
current resource, merging the changed top-level fields into it, and sending the result back with PUT**. This is the same
rule fhir-server's own merge-patch uses (a supplied list or object replaces the stored one).

| Backend | PUT available | Emulation possible? |
|---|---|---|
| MED | ✅ and PATCH | Not needed, real PATCH is used |
| OEM | Organization only, and only with a user login | Possible later (parked, see `app/connectors/openemr/README.md`). It was implemented once and removed |
| EPI, ORA | ❌ no PUT | Not possible |
| INT | ❌ no PUT, but real PATCH | Not needed |

Caveats of the emulation: it is **not atomic** (two writers can overwrite each other between the read and the write, since
none of these backends is used with `If-Match`/version checks here), the `meta` element must be dropped before the PUT, and
elements the backend does not store would be lost on write.

## 3. Search parameters

Spec references: [FHIR R4 Search](https://hl7.org/fhir/R4/search.html) (common parameters, modifiers, prefixes, result
parameters), [Organization](https://hl7.org/fhir/R4/organization.html#search),
[Location](https://hl7.org/fhir/R4/location.html#search).

### 3.1 Common parameters (all resources)

Spec: [search.html#all](https://hl7.org/fhir/R4/search.html#all).

| Parameter | Meaning | INT | MED | OEM | EPI | ORA |
|---|---|---|---|---|---|---|
| `_id` | Logical id (comma list = OR) | ✅ | ✅ | ✅ | ✅ (Organization: the only search parameter) | ⚠️ pattern checked; cannot be combined with `_count` |
| `_lastUpdated` | Last change time (date prefixes) | ✅ | ✅ | ⚠️ works (`ge`, `lt` verified); Location empties on unknown params | ❌ ignored + warning | ❌ ignored |
| `_tag` | `meta.tag` | ❌ ignored + warning | ✅ | ⚠️ Org ignored / Loc **empty** | ❌ ignored + warning | ❌ ignored |
| `_profile` | `meta.profile` | ❌ ignored + warning | ✅ | ⚠️ Org ignored / Loc **empty** | ❌ ignored + warning | ❌ ignored |
| `_security` | `meta.security` | ❌ ignored + warning | ✅ | ⚠️ Org ignored / Loc **empty** | ❌ ignored + warning | ❌ ignored |
| `_source` | `meta.source` | ❌ ignored + warning | ✅ | ⚠️ Org ignored / Loc **empty** | ❌ ignored + warning | ❌ ignored |
| `_text` | Narrative text search | ❌ ignored + warning | ❌ 400 | ⚠️ Org ignored / Loc **empty** | ❌ ignored + warning | ❌ ignored |
| `_content` | Whole-resource text search | ❌ ignored + warning | ❌ 400 | ⚠️ Org ignored / Loc **empty** | ❌ ignored + warning | ❌ ignored |
| `_list` | Members of a List | ❌ ignored + warning | ❌ 400 | ⚠️ Org ignored / Loc **empty** | ❌ ignored + warning | ❌ ignored |
| `_has` | Reverse chaining | ❌ ignored + warning | ✅ | ⚠️ Org ignored / Loc **empty** | ❌ ignored + warning | ❌ 400 |
| `_type` | Resource types (system-wide search) | ❌ ignored + warning | ⚠️ accepted, no effect on a type search | ⚠️ Org ignored / Loc **empty** | ❌ ignored + warning | ❌ ignored |
| `_query` | Named query | ❌ **always 400** (R4: servers SHALL refuse an unknown query) | ❌ 400 | ⚠️ Org ignored / Loc **empty** | ❌ ignored + warning | ❌ ignored |
| `_filter` | Filter expression | ❌ ignored + warning | ✅ | ⚠️ Org ignored / Loc **empty** | ❌ ignored + warning | ❌ ignored |

**Notes**

- **INT (C):** `_id` and `_lastUpdated` are real search parameters (`_id` supports `:not`, `:missing`; `_lastUpdated` all nine
  prefixes, precision-aware ranges). `_tag`, `_profile`, `_security`, `_source`, `_text`, `_content`, `_list`, `_has`,
  `_type`, `_filter` are listed in `UNSUPPORTED_COMMON` (`app/fhir/search/parser.py`) and treated exactly like unknown
  parameters: ignored and reported in a `search.mode = outcome` entry, or a 400 when the request has `Prefer: handling=strict`.
  `_query` is always refused.
- **MED (L, D):** Medplum also has `_compartment`, `_project` and `_deleted` (Medplum-specific). `_filter` and `_has` are
  documented on its advanced search pages. `_text`, `_content`, `_list` and `_query` answer `400 Unknown search parameter`.
  Source: [Advanced Search Parameters](https://www.medplum.com/docs/search/advanced-search-parameters).
- **OEM (L):** the same unknown-parameter rule applies to every row marked "Org ignored / Loc **empty**": **Organization**
  silently ignores the parameter; **Location returns zero results** as soon as any unrecognised parameter is present (even
  `_pretty=true` or `foo=1`). See quirks in section 4. Only `_id` and `_lastUpdated` are declared for Location.
- **EPI (L):** Organization accepts only `_id` (plus `_count`). With `_id` present, extra parameters are ignored and a warning
  entry is added: `Unknown parameter: FOO. Parameter has been ignored.` Location accepts its own parameters (table 3.5).
- **ORA (L):** unknown parameters are dropped silently. `_has` returns 400 (`_has: parameters cannot have more than one
  modifier`). `_id` must match an allowed pattern and cannot be combined with `_count`.

### 3.2 Result and control parameters

Spec: [search.html#standard](https://hl7.org/fhir/R4/search.html#standard).

| Parameter | Meaning | INT | MED | OEM | EPI | ORA |
|---|---|---|---|---|---|---|
| `_sort` | Order of results | ✅ (see notes) | ✅ | ❌ ignored | ❌ ignored + warning | ❌ ignored |
| `_count` | Page size | ✅ default 50, max 200, `0` = count only | ✅ default 20, max 1000 | ✅ | ✅ | ⚠️ min 1, max 100, default 100; not with `_id` |
| `_offset` | Skip N results (not in the FHIR spec) | ✅ | ✅ up to 10,000 | ❌ ignored | ❌ ignored + warning | ❌ ignored |
| `_total` | Whether to return a total | ✅ `none`, `estimate`, `accurate` | ✅ default `none` | ⚠️ ignored, total always present | ⚠️ ignored + warning, total always present | ⚠️ ignored; Organization has total, Location has none |
| `_summary` | Subset of elements (`true`, `count`, ...) | ✅ | ✅ | ❌ ignored | ❌ ignored + warning | ❌ ignored |
| `_elements` | Named top-level elements | ✅ (adds SUBSETTED tag) | ✅ | ❌ ignored | ❌ ignored + warning | ❌ ignored |
| `_include` | Add referenced resources | ✅ | ✅ | ⚠️ declared `*`, not demonstrated | ✅ (Location: `organization`, `partof`) | ❌ ignored |
| `_revinclude` | Add resources that refer to the results | ✅ | ✅ | ⚠️ only `Provenance:target` declared | ⚠️ only `Provenance:target` declared | ❌ ignored |
| `:iterate` (on include) | Repeat the include | ✅ | ✅ | ❌ | ❌ 400 | ❌ ignored |
| `_contained` / `_containedType` | Search or return contained resources | ⚠️ only `false` / `container`; other values 400 | ❌ 400 | ❌ ignored (Loc: empty) | ❌ ignored + warning | ❌ ignored |
| `_format` | Response format | ✅ JSON only (others 400) | ✅ | ❌ ignored | ✅ accepted | ⚠️ ignored (always JSON) |
| `_pretty` | Pretty-print | ✅ accepted, no effect | ✅ accepted | ❌ ignored | ❌ ignored + warning | ❌ ignored |
| **Paging links** (`Bundle.link`) | How to get the next page | `self`, `first`, `previous`, `next`, `last` | `self`, `first`, `previous`, `next` (cursor possible) | none seen | `next` (a `sessionID` link) and `self` | `next` and `self` |

**Notes**

- **INT (C):** `_sort` accepts only parameters that define a sort. Organization: `_id`, `_lastUpdated`, `active`,
  `address-city`, `address-country`, `address-postalcode`, `address-state`, `identifier`, `name`, `partof`, `phonetic`, `type`.
  Location: `_id`, `_lastUpdated`, `address-city`, `address-country`, `address-postalcode`, `address-state`, `address-use`,
  `identifier`, `name`, `operational-status`, `organization`, `partof`, `status`, `type`. Not sortable: `address`, `endpoint`,
  `near` (400). Unknown sort names are a 400. `_include`: Organization `partof` (and `endpoint`, accepted, adds nothing, because Endpoint is
  not a resource on this server); Location `organization`, `partof` (and `endpoint`). `_revinclude`: Organization
  `partof`, `Location:organization`; Location `partof`. `_total` default is the server's choice; `_summary` values `true`,
  `text`, `data`, `count`, `false` (`text` cannot be combined with include).
- **MED (L, D):** `_sort=-name` and `_sort=-_lastUpdated` change the order as expected. `_summary=count` returns total with
  no entries; `_summary=true` and `_elements=name` reduce the resource. `_total=accurate` adds `total` (an exact count only
  below roughly 1 million results). `_include` and `_revinclude` verified on `Organization:partof`, `Location:organization`,
  `Location:partof` and `Location:organization` as a revinclude from Organization. `_contained` answers 400. Paging: also
  `_cursor` (only for ascending `_lastUpdated` sorts). Sources:
  [Paginated Search](https://www.medplum.com/docs/search/paginated-search),
  [Including Linked Resources](https://www.medplum.com/docs/search/includes).
- **OEM (L):** `_count` works (`_count=1` returns one). `_offset`, `_sort`, `_summary`, `_elements` change nothing. The
  bundle always carries `total`. The CapabilityStatement declares `searchInclude: *` and `searchRevInclude: Provenance:target`,
  but no included resource was ever returned in testing (Organization has no references to follow; Location empties on the
  extra parameter).
- **EPI (L):** every unsupported control parameter adds the warning entry. `_include` returned the managing Organization
  and parent Locations (Location). `_revinclude=Location:partof` returned nothing. Paging is by following the `next` link
  (it carries a `sessionID`); `_count=0` is not "count only". `_format` is accepted without warning.
- **ORA (L, D):** [Organization search](https://docs.oracle.com/en/industries/health/millennium-platform-apis/mfrap/op-organization-get.html)
  and [Location search](https://docs.oracle.com/en/industries/health/millennium-platform-apis/mfrap/op-location-get.html)
  document `_count` (default 100). Tested: `_count=0` gives 400 (`_count: value must be at least 1`); `_count=500`
  returns 100. Organization bundles carry `total` (116 in one search); Location bundles did not. Paging is by `next` link, and
  that link uses `-offset=5` (a hyphen), not `_offset`, so the gateway's `nextOffset` comes back null for Oracle. Epic's `next`
  link is an opaque `?sessionID=...`, so `nextOffset` is null there too.

### 3.3 Modifiers, prefixes and search mechanics

Spec: [search.html#modifiers](https://hl7.org/fhir/R4/search.html#modifiers),
[#prefix](https://hl7.org/fhir/R4/search.html#prefix), [#combining](https://hl7.org/fhir/R4/search.html#combining),
[#chaining](https://hl7.org/fhir/R4/search.html#chaining), [#has](https://hl7.org/fhir/R4/search.html#has),
[#errors](https://hl7.org/fhir/R4/search.html#errors).

| Feature | Example | INT | MED | OEM | EPI | ORA |
|---|---|---|---|---|---|---|
| String default | `name=Prob` (starts with, case-insensitive) | ✅ | ✅ | ✅ (prefix) | ✅ (prefix, case-insensitive) | ✅ |
| `:exact` | `name:exact=Probe` | ✅ | ✅ | ✅ | ❌ 400 | ❌ 400 |
| `:contains` | `name:contains=rob` | ✅ | ✅ | ✅ | ❌ 400 | ❌ 400 |
| `:missing` | `name:missing=true` | ✅ | ✅ | ❌ **500** | ❌ 400 | ❌ 400 |
| `:not` (token) | `status:not=active` | ✅ | ✅ (a string `:not` is 400) | ❌ modifier ignored (acts like the plain search) | ❌ 400 | ❌ 400 |
| `:text` (token) | `type:text=hosp` | ✅ (`type`, `identifier`) | ✅ accepted | ❌ modifier ignored | ❌ 400 | ❌ 400 |
| `:above`, `:below`, `:in`, `:not-in` (token) | `type:below=sys\|code` | ✅ (`type`, `operational-status`) | ❌ 400 (`Invalid modifier :above for Organization-type`) | ❌ not implemented | ❌ 400 | ❌ 400 |
| `:of-type` (token) | `identifier:of-type=sys\|code\|value` | ✅ | ❌ 400 | ❌ not implemented | ❌ 400 | ❌ 400 |
| `:[type]` (reference) | `partof:Organization=Organization/1` | ✅ | ✅ | ❌ ignored | ❌ 400 | ✅ (on Location `organization`) |
| `:identifier` (reference) | `partof:identifier=sys\|val` | ✅ | ✅ accepted | ❌ modifier ignored | ❌ 400 | ❌ 400 |
| `:above`, `:below` (reference) | `partof:below=Organization/1` | ✅ (hierarchy) | ⚠️ accepted (200); hierarchy behaviour not verified | ❌ modifier ignored | ❌ 400 | ❌ 400 |
| Date prefixes | `_lastUpdated=ge2024-01-01` | ✅ all nine | ✅ | ⚠️ on `_lastUpdated` | ❌ (no date parameter) | ❌ (no date parameter) |
| OR (comma) | `name=A,B` | ✅ | ✅ | ✅ | ✅ (name) | ❌ 400 (`multiple values ... not supported`) |
| AND (repeat) | `name=A&name=B` | ✅ | ✅ | ✅ | ❌ 400 (`Don't support searching by NAME AND NAME`) | ❌ 400 (`multiple occurrences ... not supported`) |
| AND across different parameters | `name=A&address-state=IL` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Chaining | `partof.name=X` | ✅ (`partof`) | ✅ (`partof.name`, `organization.name`) | ❌ ignored | ❌ ignored + warning | ❌ ignored |
| Reverse chaining `_has` | `_has:Location:organization:name=X` | ❌ | ✅ | ❌ | ❌ | ❌ 400 |
| `POST [type]/_search` | form-encoded body | ✅ | ✅ | ✅ | ✅ | ✅ |
| `Prefer: handling=strict` | 400 for unknown parameters | ✅ | ⚠️ always strict; `handling=lenient` is **not** honoured (still 400) | ❌ header ignored | ❌ header ignored | ❌ header ignored |
| **Default for an unknown parameter** | `foo=1` | ignored + warning | **400** | Org ignored / Loc **empty** | ignored + warning | ignored |

**Notes**

- **INT (C):** modifiers per parameter are in tables 3.4 and 3.5. A known parameter with an unsupported modifier is a 400.
  Chaining is documented for reference parameters (`partof.name`, recursive); other reference chains were not verified.
  Escaping of `, | $ \` is supported.
- **MED (L):** `name:exact=Prob` gives 0 while the full name gives 1, `address-city=springfield` matches case-insensitively and
  `address-city:exact=springfield` does not. Chain results verified in both directions. A string `:not` is rejected
  (`Unsupported string search operator: not`). Token modifiers: `:not` and `:text` work; `:above`, `:below`, `:in`, `:not-in` and
  `:of-type` are rejected (`Invalid modifier :above for Organization-type`). Reference modifiers `:identifier`, `:above`,
  `:below` are accepted (200); `:missing` works. `_source` filters. The prefixes Medplum documents are `eq ne gt lt ge le sa eb`
  ([Basic Search](https://www.medplum.com/docs/search/basic-search)). `POST /_search` verified with filters (a matching name
  returned 1, a non-matching one 0).
- **OEM (L, C):** `name:contains` and `name:exact` work, and so does OpenEMR's own non-FHIR `name:suffix`. `:missing` returns an
  HTTP 500 (a PHP error in OpenEMR's query builder). Comma-OR and repeated-AND both work on `name`. Source
  (`src/Services/Search/SearchModifier.php`, `StringSearchField.php`, `FHIRSearchFieldFactory.php`): the only modifiers it knows are
  `contains`, `exact`, `prefix`, `suffix`, `missing` (strings) and an internal `not-in-exact`; any other modifier on a string
  falls back to a prefix search, token modifiers are stored but not applied (`_id:not=x` and `email:not=zzz` behaved like the plain
  search), and reference fields ignore modifiers altogether.
- **EPI (L):** string search is prefix-only and case-insensitive (`name=apex` finds "Apex ...", `name=pex` finds nothing).
  Repeating a parameter is a 400, but `name=Apex,Community` (comma) works (7 results). Other messages seen: `Modifier :EXACT
  is not supported for parameter NAME.`
- **ORA (L):** modifiers on `name` give `name: provided with an unsupported modifier`. Different parameters can be combined
  (an identifier or address plus a name that matches nothing returned 0). `_id` accepts a comma list of ids (2 results).

### 3.4 Organization search parameters

Spec: [Organization search parameters](https://hl7.org/fhir/R4/organization.html#search).

| Parameter | Type | Meaning (R4) | INT | MED | OEM | EPI | ORA |
|---|---|---|---|---|---|---|---|
| `active` | token | Is the record active | ✅ | ✅ | ❌ ignored | ❌ 400 | ❌ ignored |
| `address` | string | Any address string field | ✅ | ✅ | ❌ **500** | ❌ 400 | ✅ |
| `address-city` | string | City | ✅ | ✅ | ✅ | ❌ 400 | ❌ ignored |
| `address-country` | string | Country | ✅ | ✅ | ❌ ignored | ❌ 400 | ❌ ignored |
| `address-postalcode` | string | Postal code | ✅ | ✅ | ❌ **500** | ❌ 400 | ❌ ignored |
| `address-state` | string | State | ✅ | ✅ | ✅ | ❌ 400 | ❌ ignored |
| `address-use` | token | Address use | ✅ | ✅ | ❌ ignored | ❌ 400 | ❌ ignored |
| `endpoint` | reference | Technical endpoints | ⚠️ matches only the reference or `:identifier` (Endpoint is not stored here) | ✅ | ❌ ignored | ❌ 400 | ❌ ignored |
| `identifier` | token | Any identifier | ✅ | ✅ | ❌ ignored | ❌ 400 | ✅ |
| `name` | string | Name or alias | ✅ | ✅ | ✅ | ❌ 400 | ✅ |
| `partof` | reference | Parent organization | ✅ | ✅ | ❌ ignored | ❌ 400 | ❌ ignored |
| `phonetic` | string | Phonetic name match | ✅ | ✅ | ❌ ignored | ❌ 400 | ❌ ignored |
| `type` | token | Organization type | ✅ | ✅ | ❌ ignored | ❌ 400 | ⚠️ the system must be `http://terminology.hl7.org/CodeSystem/organization-type` |

Backend-specific extras: **OEM** also declares `email`, `phone` and `telecom` (token) on Organization (not R4 Organization
parameters; they come from the facility record).

**Notes**

- **INT (C):** modifiers per parameter, from the registry (`app/repository/organization/search.py`): `active` `:missing`, `:not`;
  `address`, `address-city`, `address-country`, `address-postalcode`, `address-state` `:exact`, `:contains`, `:missing`;
  `address-use` `:missing`, `:not`; `endpoint` `:identifier`, `:missing`; `identifier` `:missing`, `:not`, `:of-type`, `:text`;
  `name` `:exact`, `:contains`, `:missing`; `partof` `:above`, `:below`, `:identifier`, `:missing` (recursive hierarchy);
  `phonetic` `:missing`; `type` `:above`, `:below`, `:in`, `:not-in`, `:missing`, `:not`, `:text` (value sets and the IS-A hierarchy
  come from the terminology service). `name` also searches the alias.
- **MED (L):** every R4 parameter is declared and filtered correctly in tests (`active=false` returned the one inactive record,
  `phonetic=Prob` matched both "Probe ..." records, `type=...|prov` and `type:not=...|prov` complement each other).
- **OEM (L, D):** declared in `/metadata`: `_id`, `_lastUpdated`, `email`, `phone`, `telecom`, `address`, `address-city`,
  `address-postalcode`, `address-state`, `name` ([OpenEMR Swagger](http://localhost/swagger/openemr-api.yaml)). In tests
  `address` and `address-postalcode` fail with HTTP 500 (`SQL Statement failed on preparation`), so only `address-city`,
  `address-state` and `name` really filter. `name` is a prefix match; `:contains` and `:exact` also work. Cause of the 500s
  (read from OpenEMR's source, `src/Services/FHIR/FhirOrganizationService.php`, `loadSearchParameters()`): `address` is mapped to
  the columns `line1` and `line2`, and `address-postalcode` to `zip`, but the `facility` table has neither (it has `street`,
  `city`, `state`, `postal_code`, `country_code`), so the SQL fails. This is an OpenEMR bug, not something the connector can fix.
  Where OpenEMR documents this: its Swagger file lists the Organization parameters but only `_id` and `_lastUpdated` for Location,
  although the code (and `/metadata`) also supports `address`, `name`, `address-city`, `address-state`, `address-postalcode` on
  Location (`FhirLocationService.php`). The source is the authority.
- **EPI (L, D):** the CapabilityStatement lists only `_id` and `_count`. `?name=EHS` returns `400 Only an _ID search is
  allowed.` (the "❌ 400" in the table). If `_id` is also present, any other parameter is silently dropped with the
  `Unknown parameter ... has been ignored` warning entry. Organization ids can be taken from `Location.managingOrganization`.
- **ORA (L, D):** documented parameters: `_id`, `_count`, `address`, `identifier`, `name`, `type`
  ([docs](https://docs.oracle.com/en/industries/health/millennium-platform-apis/mfrap/op-organization-get.html)). `address` matches
  street, name, state or postal code, starting with the given text. Combining two parameters works as AND (an
  address or identifier plus a name that matches nothing returned 0). `name`, `address` and `type` search with no
  other restriction. `identifier` works alone and combined (`system|value` and bare `value` both found the record;
  a made-up value found nothing); an identifier whose **system Oracle does not recognise** (for example
  `http://x.example|...`) was ignored when combined with `name`. `address-city` and the other address parts are not
  declared and are silently ignored (a search for a city returned all 2,224 organizations).

### 3.5 Location search parameters

Spec: [Location search parameters](https://hl7.org/fhir/R4/location.html#search).

| Parameter | Type | Meaning (R4) | INT | MED | OEM | EPI | ORA |
|---|---|---|---|---|---|---|---|
| `address` | string | Any address string field | ✅ | ✅ | ✅ | ✅ | ✅ (not with `address-state`) |
| `address-city` | string | City | ✅ | ✅ | ✅ | ✅ | ⚠️ needs `address-state` or `address-postalcode` |
| `address-country` | string | Country | ✅ | ✅ | ❌ **empty** | ✅ | ❌ ignored |
| `address-postalcode` | string | Postal code | ✅ | ✅ | ✅ | ✅ | ⚠️ returned only some of the matching locations |
| `address-state` | string | State | ✅ | ✅ | ✅ | ✅ | ✅ |
| `address-use` | token | Address use | ✅ | ✅ | ❌ **empty** | ✅ | ❌ ignored |
| `endpoint` | reference | Technical endpoints | ⚠️ reference or `:identifier` only | ✅ | ❌ **empty** | ✅ | ❌ ignored |
| `identifier` | token | Any identifier | ✅ | ✅ | ❌ **empty** | ✅ | ✅ |
| `name` | string | Name or alias | ✅ | ✅ | ✅ | ⚠️ prefix match; case-insensitive | ⚠️ matches the **alias** only (the real name found nothing); needs another qualifying parameter |
| `near` | special | Distance from lat/long | ✅ (`lat\|long\|distance\|units`, km default, 50 km) | ❌ 400 | ❌ **empty** | ❌ ignored + warning | ❌ ignored |
| `operational-status` | token | Bed status | ✅ | ✅ | ❌ **empty** | ✅ | ❌ ignored |
| `organization` | reference | Managing organization | ✅ | ✅ | ❌ **empty** | ✅ | ⚠️ needs another qualifying parameter |
| `partof` | reference | Parent location | ✅ | ✅ | ❌ **empty** | ✅ | ❌ ignored |
| `status` | token | active, suspended, inactive | ✅ | ✅ | ❌ **empty** | ⚠️ search defaults to `status=active` | ❌ ignored |
| `type` | token | Location type | ✅ | ✅ | ❌ **empty** | ⚠️ accepted but did not narrow results; alone it is a 400 | ✅ |

Backend-specific extras: **MED** `physical-type`; **ORA** `-physicalType` (Oracle's own parameter name, a token);
**MED** also the common Medplum parameters listed in 3.1.

**Notes**

- **INT (C):** modifiers per parameter (`app/repository/location/search.py`): same string, token and reference rules as
  Organization; `operational-status` and `type` also take `:above`, `:below`, `:in`, `:not-in`; `organization` `:identifier`;
  `partof` `:above`, `:below`, `:identifier`; `status` `:missing`, `:not`; `near` has no modifiers (computed with plain trigonometry in
  SQL) and adds the `location-distance` extension to each match.
- **MED (L, D):** all parameters in the table filter correctly **except `near`**: `/metadata` lists `near` (type `special`),
  but a search answers `400 Unrecognized search parameter type: special`. The same applies to `near` with valid values.
- **OEM (L, D):** declared in `/metadata`: `_id`, `_lastUpdated`, `address`, `address-city`, `address-state`,
  `address-postalcode`, `name`. **Any other parameter makes the result empty** (verified with `_total=accurate`, `_pretty=true`,
  `foo=1`, and the undeclared real parameters), so these are marked ❌ **empty**.
- **EPI (L, D):** the CapabilityStatement lists `type`, `_count`, `_id`, `address`, `address-city`, `address-country`,
  `address-postalcode`, `address-state`, `address-use`, `endpoint`, `identifier`, `name`, `operational-status`,
  `organization`, `partof`, `status`. A search needs a qualifying parameter: `type` alone gives `400 This resource requires at
  least one parameter besides status for searching`. `status=active` is added to the search by default. `_id` must be a valid
  Epic id (`400 Invalid FHIR ID provided` otherwise). When a search returns nothing the bundle contains a warning entry
  `Resource request returns no results.`
- **ORA (L, D):** [documented parameters](https://docs.oracle.com/en/industries/health/millennium-platform-apis/mfrap/op-location-get.html):
  `_id`, `_count`, `-physicalType`, `identifier`, `address`, `address-city`, `address-state`, `address-postalcode`, `name`,
  `organization`, `type`. Rules (Oracle's own, returned as 400 when broken): one of `_id` or `-physicalType` or `identifier`
  or `address` or `address-state` or `address-city` or `address-postalcode` or `type` is required; `address-city` needs
  `address-state` or `address-postalcode`; `name` and `organization` need at least one of the qualifying
  parameters; `address` cannot be combined with `address-state`. Tested with real values taken from real records: `name`
  found a location only by its **alias** (`MX BH CL` found it; its real name "Model Behavioral Health Clinic", a word of it
  or a prefix of it found nothing, with any qualifier); `address-postalcode` worked for some codes (64108 and 64117 returned
  3 locations each) but returned nothing for others (64111, 19973) and not every location that has the code (4 and 6
  locations carry 64108 and 64117); `address` (matching a street word or the city) and `address-state` returned the expected
  records. The cause is on Oracle's side and may be specific to the sandbox data.

## 4. Connector behaviour and quirks

**internal (fhir-server).** Full FHIR R4 search for both resources, written for this project (`app/fhir/search/`). Unknown
and unimplemented parameters are ignored and reported in the result (or rejected with `Prefer: handling=strict`).
Paging uses `_count` (default 50, max 200) and `_offset`, with `first`, `previous`, `next`, `last` links. Only `application/fhir+json` is served. Writes
validate the resource against base FHIR R4 first. (C)

**medplum.** The most complete FHIR search of the four external backends: all R4 parameters, modifiers (except string `:not`),
chaining, `_has`, `_include`, `_revinclude`, `_filter`, `_tag`, `_summary`, `_elements`, `_total`, offset and cursor
paging. It is **strict**: unknown or unsupported parameters are a 400 and `Prefer: handling=lenient` does not change that. `near`
is declared but rejected. Full read/write including PUT, PATCH, DELETE, history and conditional operations. (L, D)

**openemr.** A thin layer over the `facility` table. Organization and Location read/search only, with a handful of
parameters; Organization create/update need an admin user login. Gotchas: on **Location any unrecognised parameter empties the
result**, so a client must send only declared parameters (the gateway's default `_count` and `_offset` are harmless, but
`_total` and the other control parameters are not for Location); on Organization `address`, `address-postalcode` and `:missing`
cause **HTTP 500**; `_offset`, `_sort`, `_summary`, `_elements` are ignored; `total` is always returned. (L)

**epic.** Read and search only. Organization can only be fetched by `_id` (take the id from a Location's
`managingOrganization`). Location needs a qualifying parameter and supports prefix `name`, address parts, `identifier`,
`organization`, `partof` and others; no modifiers (`:exact`, `:contains`, `:missing`, `:not`, `:iterate` all 400), no repeated parameters (AND), comma OR on `name` works.
Control parameters (`_sort`, `_total`, `_offset`, `_lastUpdated`, `_elements`, `_summary`) are ignored with a warning entry. Paging is
only through the `next` link (a `sessionID`), not `_offset`. (L, D)

**oracle_health.** Read and search for both, create for Organization. Search is the most restrictive: no modifiers, no
comma OR and no repeated parameter, Location needs one qualifying parameter, `_count` is 1 to 100, and `_id` cannot be combined with `_count`.
Parameters not on Oracle's list are silently ignored, so the result is unfiltered. Both Basic (client secret) and signed-JWT logins work.
Organization `type` accepts only the HL7 `organization-type` system. (L, D)

## 5. What this means for the gateway

Our GraphQL schema exposes every FHIR R4 search parameter of the resource as an argument, plus `count`, `offset`, `sort`,
`total`, `include`, `revinclude` and a generic `params` list. Not every connector can honour each one.

- **Offset paging** (`offset` becomes `_offset`) works on INT and MED only. On OEM, EPI and ORA it is ignored, so every page
  returns the same first results; paging there needs the `next` link (EPI, ORA).
- **Sorting** works on INT and MED only.
- **`total`** is sent as `_total`: honoured by INT and MED, ignored by the others (some always return a total, Oracle
  Location never does).
- **Include and revinclude** work on INT and MED, partly on EPI, and not on OEM and ORA.
- **Filters that are silently ignored** (ORA, EPI warnings, OEM Organization) return unfiltered results: the caller cannot tell
  from the data alone that a filter was dropped (EPI at least adds the warning entry).
- **Hard failures:** OEM Location (empty on any undeclared parameter), OEM Organization (500 on `address`), ORA and EPI (400s for
  modifiers and repeats) are the cases where a generic GraphQL query can fail or look empty on one backend and work on another.

Points to settle for a common connector contract (to discuss with the team): a per-connector capability description
(operations, supported parameters per resource, supported modifiers, paging style, total support); a policy for dropped or
unsupported parameters (ignore, warn, or reject); whether the gateway should refuse unsupported parameters before calling a
backend; offset-to-link paging; PUT-based patch emulation where PUT exists; and which mutations are exposed per active connector.

## 6. Sources

**FHIR specification (HL7, R4)**
- [Search](https://hl7.org/fhir/R4/search.html): common parameters, modifiers, prefixes, chaining, `_has`, result parameters, `Prefer` handling.
- [Organization](https://hl7.org/fhir/R4/organization.html) (search parameters table) and
  [Location](https://hl7.org/fhir/R4/location.html) (search parameters table).
- [RESTful API](https://hl7.org/fhir/R4/http.html): read, vread, update, patch, delete, create, conditional operations, history.

**Medplum**
- [Search overview](https://www.medplum.com/docs/search), [Basic Search](https://www.medplum.com/docs/search/basic-search),
  [Advanced Search Parameters](https://www.medplum.com/docs/search/advanced-search-parameters),
  [Paginated Search](https://www.medplum.com/docs/search/paginated-search),
  [Including Linked Resources](https://www.medplum.com/docs/search/includes).
- Local CapabilityStatement: `http://localhost:8103/fhir/R4/metadata`.

**OpenEMR**
- Local OpenAPI file (Swagger UI at `http://localhost/swagger/`): `http://localhost/swagger/openemr-api.yaml`.
- CapabilityStatement: `http://localhost/apis/default/fhir/metadata`.
- Project docs: [FHIR_README.md](https://github.com/openemr/openemr/blob/master/FHIR_README.md) and
  [Documentation/api/FHIR_API.md](https://github.com/openemr/openemr/blob/master/Documentation/api/FHIR_API.md). Neither lists Organization or Location
  search parameters; both point to Swagger.
- OpenEMR source (the authority for supported search parameters), read inside the Docker image:
  `src/Services/FHIR/FhirOrganizationService.php` and `src/Services/FHIR/FhirLocationService.php` (`loadSearchParameters()`),
  routes in `apis/routes/_rest_routes_fhir_r4_us_core_3_1_0.inc.php`. Public repository: [github.com/openemr/openemr](https://github.com/openemr/openemr).
- Standard (non-FHIR) facility API, relevant to a possible hybrid: `GET/POST/PUT /apis/default/api/facility` (in the same OpenAPI file).

**Epic on FHIR**
- Public CapabilityStatement: [`/metadata`](https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/metadata).
- Developer portal: [fhir.epic.com](https://fhir.epic.com). Its per-API specification pages could not be fetched automatically, so
  Epic behaviour here rests on the CapabilityStatement and live tests.

**Oracle Health (Cerner Millennium)**
- [All REST endpoints](https://docs.oracle.com/en/industries/health/millennium-platform-apis/mfrap/rest-endpoints.html) (44 entries).
- [Organization search](https://docs.oracle.com/en/industries/health/millennium-platform-apis/mfrap/op-organization-get.html),
  [Location search](https://docs.oracle.com/en/industries/health/millennium-platform-apis/mfrap/op-location-get.html).
- [Authorization Framework](https://docs.oracle.com/en/industries/health/millennium-platform-apis/authorization-framework).
- Sandbox CapabilityStatement: `https://fhir-ehr-code.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d/metadata`.
- More notes in `app/connectors/oracle_health/README.md`.

**This repository**
- fhir-server (internal connector): `app/fhir/search/parser.py`, `app/repository/organization/search.py`,
  `app/repository/location/search.py`, `app/routers/organization/core.py`, `app/routers/location/core.py`, its `CLAUDE.md`.
- fhir-gql: `app/connectors/<name>/`, `app/connectors/fhir_search.py` (how GraphQL arguments become query parameters),
  `app/connectors/token_manager.py`, and the per-connector READMEs.

## 7. Method and limits

1. Each backend's CapabilityStatement was read for the declared interactions and search parameters.
2. A baseline search that returns results was chosen for each backend and resource, then the same search was repeated with one
   extra parameter at a time: a non-matching value for each resource parameter, the common and control parameters, modifiers,
   OR/AND, chaining, `_has`, `POST _search` and `Prefer: handling=strict`. A result with zero entries means the
   parameter filtered; an unchanged result means it was ignored; a 4xx/5xx means it was rejected. Suspicious results were re-checked directly.
3. A second round of checks closed the gaps from the first version of this document: token and reference modifiers on every backend,
   `:not` on OpenEMR (also confirmed in its source), `_source`, and `POST _search` filtering on Medplum (the five Medplum test records
   were created again for it and deleted afterwards). What is still not verified (❓ no longer appears in the tables): the
   hierarchy behaviour of reference `:above`/`:below` on Medplum (accepted, semantics not tested), composite parameters (none exist
   on these resources), and anything about the `internal` connector at run time (it is documented from source only).
4. Backends change. Re-run the checks when upgrading a backend. Oracle and Epic behaviour is for their public sandbox tenants.
5. A ✅ for "this parameter filters" in sections 3.4 and 3.5 was established with a value that cannot match. That proves the
   parameter is applied, not that it matches correctly. Section 8 re-tested the parameters that matter for a common subset with
   **real values taken from real records** (the record is searched for by its own name, city, state, postal code); where that
   contradicted a ✅ above it was corrected (Oracle Location `name` and `address-postalcode`).

## 8. Proposal: a common subset for every connector (not implemented)

Status: **documentation only**. Nothing in the gateway changes. The idea, for the team discussion: expose in GraphQL, as
"common", only what works on **all five** connectors, and treat everything else as connector-specific.

Basis: sections 2 and 3, plus a final round of tests on 2026-11-18 in which each backend's own record was searched for by its own
values: Medplum (five temporary records, deleted again), OpenEMR (the one facility got a temporary address, then was restored to its
original empty values), Epic, Oracle. The `internal` column is from the source code (not run).

### 8.1 Operations

| Operation | Common to all five? | Notes |
|---|---|---|
| Read by id (Organization, Location) | **Yes** | |
| Search (`GET [type]?...`) | **Yes**, with the parameter limits below | Epic Organization only by `_id` |
| Search (`POST [type]/_search`) | **Yes** | |
| Create | No | Organization: INT, MED, ORA. Location: INT, MED |
| Update (PUT) | No | MED only |
| Patch | No | INT, MED |
| Delete | No | INT, MED |

### 8.2 Common search behaviour

| Feature | Common? | Evidence and limits |
|---|---|---|
| `_id` | **Yes** (5/5) | Oracle: cannot be combined with `_count` |
| `_count` (page size) | **Yes**, range **1 to 100** | INT max 200, MED max 1000, ORA min 1 / max 100 (400 for 0). OEM and EPI accept it. Never send it together with `_id` |
| Case-insensitive prefix match for strings | **Yes** | Verified: MED, OEM, EPI, ORA. INT by design. (OpenEMR `name=your`, Oracle `name=abc`, Epic `address-state=wi` all matched) |
| Combining **different** parameters (AND) | **Yes** | Verified on MED, OEM, EPI, ORA |
| Paging beyond the first page | **No** | INT, MED use `_offset`; EPI, ORA only the `next` link; OEM nothing |
| `_sort`, `_total`, `_summary`, `_elements`, `_include`, `_revinclude`, `_lastUpdated` | **No** | Each fails on at least two connectors (section 3.1, 3.2) |
| Modifiers (`:exact`, `:contains`, `:missing`, `:not`, ...) | **No** | EPI and ORA reject them; OEM 500 on `:missing` |
| OR with a comma, or repeating one parameter (AND) | **No** | ORA rejects both; EPI rejects repeats |
| Chaining, `_has` | **No** | MED only |

Because backends react so differently to what they do not support (ignore silently, ignore with a warning, 400, **empty
result**, 500), a common layer cannot rely on the backend to say "unsupported". It would have to refuse parameters outside
the common set itself.

### 8.3 Organization: what works on how many connectors

Verified with real values unless noted. "5/5" is the only fully common level.

| Parameter | Works on | Missing on | Level |
|---|---|---|---|
| `_id` | 5/5 | none | **Common** |
| `name` | 4/5 | EPI (Organization is searchable only by `_id` for this app) | Near-common |
| `address` | 3/5 (INT, MED, ORA) | OEM (HTTP 500), EPI | Partial |
| `address-city`, `address-state` | 3/5 (INT, MED, OEM) | EPI, ORA (ignored) | Partial |
| `identifier` | 3/5 (INT, MED, ORA) | OEM (ignored), EPI | Partial |
| `type` | 3/5 (INT, MED, ORA; ORA only with the HL7 `organization-type` system) | OEM, EPI | Partial |
| `address-postalcode` | 2/5 (INT, MED) | OEM (500), EPI, ORA | Backend-specific |
| `active`, `address-country`, `address-use`, `endpoint`, `partof`, `phonetic` | 2/5 (INT, MED) | OEM, EPI, ORA | Backend-specific |

So for Organization the only common query today is **by id**, and **by name** everywhere except Epic.

### 8.4 Location: what works on how many connectors

| Parameter | Works on | Caveats / missing on | Level |
|---|---|---|---|
| `_id` | 5/5 | none | **Common** |
| `address-state` | 5/5 | none | **Common** |
| `address` | 5/5 | ORA: cannot be combined with `address-state` or `address-city` | **Common** (with that rule) |
| `address-city` | 5/5 | ORA: only together with `address-state` or `address-postalcode` | **Common** (with that rule) |
| `address-postalcode` | 4/5 + 1 partial | ORA returns only some of the matching locations | Near-common |
| `name` | 4/5 + 1 partial | ORA matches the alias only and needs a qualifier; OEM, EPI, MED, INT match the name (prefix) | Near-common |
| `identifier` | 4/5 | OEM (empty result) | Partial |
| `organization` | 4/5 | OEM (empty result); ORA needs a qualifier | Partial |
| `address-country`, `address-use`, `endpoint`, `operational-status`, `partof`, `status`, `type` | 3/5 (INT, MED, EPI; ORA only `type`) | OEM empty; ORA ignores most | Backend-specific |
| `near` | 1/5 (INT) | MED rejects it; the others ignore or empty | Backend-specific |

### 8.5 Rules a common search must follow

These come from the strictest backend, so a query that obeys all of them runs on every connector:

1. **Location needs a qualifier:** send at least one of `address`, `address-state`, `address-postalcode`, or `_id`. `name` alone is a
   400 on Oracle; Epic wants a parameter besides `status`.
2. **Send each parameter once, with a single value** (no comma lists, no repeats): Oracle and Epic reject them.
3. **No modifiers.**
4. **`address-city` only together with `address-state` or `address-postalcode`** (Oracle).
5. **Do not combine `address` with `address-state` or `address-city`** (Oracle).
6. **`_count` between 1 and 100, and never with `_id`** (Oracle).
7. **Send nothing else on Location** (`_total`, `_sort`, `_offset`, `_summary`...): OpenEMR then returns an empty result. `_count` and
   `_offset` are tolerated by OpenEMR, but `_offset` has no effect.
8. **Organization on Epic: `_id` only.**
9. **First page only**: there is no common way to get the next page.

### 8.6 Suggested common GraphQL surface (a proposal)

| | Arguments in the common set |
|---|---|
| Organization | `id` (read), search by `name` (not available on Epic), `count` |
| Location | `id` (read), search by `addressState`, `address`, `addressCity` (with the rules above), optionally `addressPostalCode` and `name` flagged as "may be incomplete on some connectors"; `count` |

Everything else (`_lastUpdated`, sort, offset, total, include, modifiers, the other parameters) would stay connector-specific and be
documented per connector rather than offered as common. Points to decide: whether the gateway rejects out-of-set parameters or
passes them through; how a connector declares what it supports; whether `name` (4 of 5 on Organization) counts as common.

### 8.7 What could change this list

- **Epic Organization search:** the app's token only has `system/Organization.read` and `system/Location.read`. If the Organization
  Search API is added to the app registration, `name` may work (to be re-tested), which would make Organization `name` 5/5.
- **OpenEMR:** `address` and `address-postalcode` on Organization are crashing on missing database columns. A fixed OpenEMR would add
  them.
- **Oracle Location `name` and `address-postalcode`:** the sandbox data may be the cause. Re-test on a real customer tenant before
  relying on the Oracle results as final.
- **Medplum / internal:** support more than the common set, so they never limit it.
