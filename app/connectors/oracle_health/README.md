# Oracle Health (Cerner Millennium) connector

Status: **not built yet.** This file holds the research notes. Update it as the connector is built.

## Supported FHIR R4 resources (Millennium)

Source: https://docs.oracle.com/en/industries/health/millennium-platform-apis/mfrap/rest-endpoints.html
("All REST endpoints", FHIR R4 APIs for Oracle Health Millennium Platform). The page lists 44 entries; the code Console
scope list (next section) has 41. Compared: the Console lacks Bundle, CapabilityStatement, OperationDefinition and
StructureDefinition (not grantable as scopes) and adds FinancialTransaction (the page's `Basic` category). Everything
else matches, including the write flags.

Read = GET by id. Search = GET the list. Patch = HTTP PATCH.

| # | Resource | Read | Search | Create | Update | Patch | Delete | Other operations |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|---|
| 1 | Account | Y | Y | | | | | |
| 2 | AllergyIntolerance | Y | Y | Y | Y | | | |
| 3 | Appointment | Y | Y | Y | | Y | | |
| 4 | Basic (FinancialTransaction category) | | | Y | | | | |
| 5 | Binary | Y | | | | | | GET `/Binary/$autogen-ccd-if` |
| 6 | Bundle | | | | | | | POST `/` (batch / transaction) |
| 7 | CapabilityStatement | | | | | | | GET `/metadata`; GET `/.well-known/smart-configuration` |
| 8 | CarePlan | Y | Y | | | | | |
| 9 | CareTeam | Y | Y | | | | | |
| 10 | ChargeItem | Y | Y | Y | | | | POST `$create`, `$modify`; POST `/{id}/$credit` |
| 11 | Communication | Y | Y | Y | | Y | | |
| 12 | Condition | Y | Y | Y | Y | | | |
| 13 | Consent | Y | Y | | | | | |
| 14 | Coverage | Y | Y | Y | | Y | Y | |
| 15 | Device | Y | Y | | | | | |
| 16 | DiagnosticReport | Y | Y | Y | | | | |
| 17 | DocumentReference | Y | Y | Y | Y | | | GET `/$docref` |
| 18 | Encounter | Y | Y | Y | | Y | | |
| 19 | FamilyMemberHistory | Y | Y | Y | Y | | | |
| 20 | Goal | Y | Y | | | | | |
| 21 | Immunization | Y | Y | Y | Y | | | |
| 22 | InsurancePlan | Y | Y | | | | | |
| 23 | **Location** | Y | Y | | | | | |
| 24 | Media | Y | | | | | | |
| 25 | MedicationAdministration | Y | Y | | | | | |
| 26 | MedicationDispense | Y | Y | | | | | |
| 27 | MedicationRequest | Y | Y | Y | | Y | | |
| 28 | NutritionOrder | Y | Y | | | | | |
| 29 | Observation | Y | Y | Y | Y | | | |
| 30 | OperationDefinition | Y | | | | | | |
| 31 | **Organization** | Y | Y | Y | | | | GET `/$get-cg-for-mrcu` |
| 32 | Patient | Y | Y | Y | | Y | | POST `/{id}/$health-cards-issue` |
| 33 | Person | Y | Y | | | | | |
| 34 | Practitioner | Y | Y | Y | | | | |
| 35 | Procedure | Y | Y | Y | | | | |
| 36 | Provenance | Y | Y | Y | | | | |
| 37 | Questionnaire | Y | Y | | | | | |
| 38 | QuestionnaireResponse | Y | Y | | Y | | | |
| 39 | RelatedPerson | Y | Y | Y | | Y | | |
| 40 | Schedule | Y | Y | | | | | |
| 41 | ServiceRequest | Y | Y | | | | | |
| 42 | Slot | Y | Y | | | Y | | |
| 43 | Specimen | Y | Y | | | | | |
| 44 | StructureDefinition | Y | | | | | | |

Notes:
- Only Coverage supports Delete.
- Organization: read, search and create (no update, patch or delete). Location: read and search only.
- Some paths in the source page are written inconsistently (for example `/Patient{ID}`); the Basic resource backs the
  FinancialTransaction category.

## Scopes offered by the code Console (41 resources, as registered)

Read-only (18): Account, Binary, CarePlan, CareTeam, Consent, Device, Goal, InsurancePlan, **Location**, Media,
MedicationAdministration, MedicationDispense, NutritionOrder, Person, Questionnaire, Schedule, ServiceRequest,
Specimen.

Read and write (21): AllergyIntolerance, Appointment, ChargeItem, Communication, Condition, Coverage, DiagnosticReport,
DocumentReference, Encounter, FamilyMemberHistory, Immunization, MedicationRequest, Observation, **Organization**,
Patient, Practitioner, Procedure, Provenance, QuestionnaireResponse, RelatedPerson, Slot.

Write-only (2): Basic, FinancialTransaction.

Relevant to us: **Organization has a write scope (create per the endpoint page, no update or delete), Location is
read-only.** Unlike OpenEMR and Epic, writes here are possible with a system app, so the connector need not be
read-only for Organization.

## Verified live against the sandbox (CapabilityStatement `/metadata`, FHIR 4.0.1)

Auth: `client_secret` (HTTP Basic) works; token endpoint `https://authorization.cerner.com/tenants/<tenant>/protocols/oauth2/profiles/smart-v1/token`.

| | Organization | Location |
|---|---|---|
| Interactions | read, search-type, create | read, search-type |
| Search params | `_id`, `identifier`, `type`, `name`, `address`, `_count` | `_id`, `identifier`, `type`, `-physicalType`, `address`, `address-city`, `address-state`, `address-postalcode`, `name`, `organization` |

Rules and quirks seen live:
- **Location search is restrictive:** at least one of `_id`, `-physicalType`, `identifier`, `address`, `address-state`,
  `address-city`, `address-postalcode`, `type` is required (`name` alone is a 400). `address-city` also needs
  `address-state` or `address-postalcode`.
- Search modifiers such as `name:contains` are rejected (400 "unsupported modifier").
- Parameters Oracle doesn't list (for example `address-city` on Organization) are silently ignored, so the result is
  unfiltered. No `_sort`, `_include` or `_revinclude` are advertised.
- Organization update/patch/delete and every Location write: not available (connector answers 405).
- **Organization create works** (verified through GraphQL `createFhirOrganization`; needs `system/Organization.write` in
  `scope`, now the default). It created id `3690655` ("fhir-gql e2e test org") in the shared public sandbox, which
  cannot be deleted through the API. Oracle rejects a duplicate name with 409 ("name ... is already used by an entity
  with id=...").
- Verified end to end through the real GraphQL schema (in-process, JWT layer faked): `getFhirOrganization`,
  `searchFhirOrganizations`, `getFhirOrganizations`, `createFhirOrganization`, `getFhirLocation`, `searchFhirLocations`
  all work; `updateFhirOrganization`, `deleteFhirOrganization` and `createFhirLocation` return the 405 message.
- Paging: only `_count` is supported, so `offset` (sent as `_offset`) is ignored. Following the bundle's `next` link
  would be needed for real paging (to do with the search refinement).

## Still to confirm when building (from the console, not yet seen)

- Auth type for a System app: client secret versus signed-JWT keys (sources disagree).
- Sandbox tenant id and the exact base and token URLs.
- Scopes the console actually grants (known quirk: granted scopes can differ from those requested).
