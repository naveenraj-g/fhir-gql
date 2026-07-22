# Admin APIs and Multi-Tenancy (Projects) — Medplum vs fhir-gql

Scope: Medplum's `packages/server/src/admin/{bot,client,invite,project,routes,super,utils}.ts`.
This is the layer that manages Medplum's tenant boundary — the `Project` resource — plus
everything scoped underneath it (memberships, invites, OAuth clients, bots) and a
"super admin" layer that operates across every project on the instance.

## Context: what fhir-gql looks like today

Before mapping features, two facts about fhir-gql's current (`app/auth/rbac.py`,
`app/auth/models.py`, `app/auth/dependencies.py`) design matter for every verdict below:

1. **fhir-gql already carries a tenant-scoping field, but it is not a "Project."**
   `AuthUser.org_id` (`app/auth/models.py:35`) is populated straight from the JWT's
   `activeOrganizationId` claim — a claim minted by the separate BetterAuth/IAM service,
   not by fhir-gql. fhir-gql never creates, reads, updates, or lists "organizations"; it only
   *reads* whichever org the IAM service says is currently active for the caller.
2. **That field is not consistently enforced.** `app/services/patient_service.py` and
   `app/fhir_client/patient.py` show `org_id` is threaded into `list()` and `get_me()` as a
   filter parameter, but `get_by_id`, `update`, `delete`, and every sub-resource endpoint
   (`app/routers/patient.py`) take only a bare integer `patient_id` — no `org_id` is sent to
   the fhir-server on those calls. There is currently no code path in fhir-gql that stops an
   authenticated user with `patient:read`/`patient:update` from reading or mutating a Patient
   belonging to a different `org_id` by guessing/incrementing the ID, unless the downstream
   fhir-server independently re-derives and enforces org scoping from the token (out of scope
   for this repo). This gap is orthogonal to whether fhir-gql adopts a Medplum-style `Project`
   concept — it exists regardless, and is called out again in "Recommended next steps."

Medplum's model, by contrast, is that every single resource (including `User`, `Bot`,
`ClientApplication`, `AccessPolicy`) carries a `meta.project` id, and every repository read is
transparently filtered by the caller's project. Medplum's "admin" layer is the set of
privileged mutations on top of that: project settings, who belongs to a project and with what
role, provisioning machine identities (bots, OAuth clients) inside a project, and a super-admin
layer with instance-wide reach that bypasses project scoping entirely.

---

### Project Resource Read & Metadata

- **What it does:** Lets a project admin fetch their project's id, name, settings, secrets,
  and configured sites in one call.
- **Source files:** `packages/server/src/admin/project.ts` — `projectAdminRouter.get('/:projectId', ...)`
  handler (anonymous, inline).
- **How it works:** `getAuthenticatedContext()` (Express `AsyncLocalStorage`-backed request
  context, defined outside this file) already resolved `ctx.project` from the caller's access
  token during `authenticateRequest` + `verifyProjectAdmin` middleware. The handler just
  echoes back `project.id/name/setting/secret/site` as plain JSON — no additional DB query.
  Authorization is entirely upstream: the route is only reachable if `verifyProjectAdmin`
  (see below) let the request through.
- **Belongs in:** `shared IAM service`, if fhir-gql ever needs an org-settings surface at all.
  fhir-gql has no `Project`-equivalent resource of its own to read metadata from — "which org
  is this" already lives in the JWT claim, and org display name/settings would logically live
  wherever BetterAuth stores organizations (BetterAuth's `organization` plugin already models
  this). fhir-server is not the right owner either — it stores clinical data, not tenant
  metadata.
- **Port notes for fhir-gql (FastAPI/Python):** No action needed unless a future requirement
  surfaces (e.g., "show org name in the UI"). If it does, it's a read against the IAM service's
  own admin API, not something modeled in `app/auth/rbac.py` or `app/di/container.py` — it
  would be a new `IamAdminClient` wired in a `CoreContainer`-style singleton the same way
  `FhirClient` is today (`app/di/core.py`), not a new "project" domain container.
- **Priority:** Low — no current requirement references org metadata beyond the id used for
  filtering.

### Project Settings / Secrets / Sites Configuration

- **What it does:** Three near-identical endpoints let a project admin overwrite the project's
  `setting[]` (key/value config), `secret[]` (server-side secrets available to Bots), and
  `site[]` (allowed redirect domains) arrays wholesale.
- **Source files:** `packages/server/src/admin/project.ts` —
  `projectAdminRouter.post('/:projectId/settings', ...)`,
  `.../secrets`, `.../sites` handlers.
- **How it works:** Each handler does `ctx.repo.updateResource({...ctx.project, setting: req.body})`
  (or `secret`/`site`) — a full-resource update of the `Project` FHIR resource through the
  caller's project-scoped `Repository`, which is already access-policy-constrained to this
  project. No separate authorization check beyond the router-level `verifyProjectAdmin`.
- **Belongs in:** `shared IAM service` conceptually (org-level configuration), but note this
  Medplum feature exists specifically because Bots need project-scoped secrets and
  ClientApplications need project-scoped allowed sites/redirect URLs — both Medplum concepts
  fhir-gql does not have (see Bot/Client features below). Without bots/OAuth clients as
  first-class fhir-gql concepts, there is nothing for "project secrets/sites" to configure.
- **Port notes for fhir-gql (FastAPI/Python):** Not applicable today. Would only become
  relevant if fhir-gql grows its own automation/OAuth-client surface, at which point secrets
  would belong in a proper secrets manager (not a FHIR resource field) referenced from
  `app/config.py`-style settings, scoped per org via `actor.org_id`.
- **Priority:** Low — no current fhir-gql feature (bots, OAuth clients) needs this.

### Project Admin Authorization Gate

- **What it does:** Middleware that blocks every route under `/admin/projects/*` unless the
  caller is either a super admin or an admin member (`ProjectMembership.admin === true`) of
  the specific project being administered.
- **Source files:** `packages/server/src/admin/utils.ts` — `verifyProjectAdmin(req, res, next)`.
  Wired in `packages/server/src/admin/project.ts:22` via
  `projectAdminRouter.use(verifyProjectAdmin)`.
- **How it works:** Reads `ctx.project.superAdmin` and `ctx.membership.admin` off the
  already-resolved request context (populated earlier by `authenticateRequest`, which decoded
  the access token and loaded the caller's `ProjectMembership` for `ctx.project`). If neither
  flag is true, calls `next(new OperationOutcomeError(forbidden))`, short-circuiting the whole
  router. This is a coarse, router-level equivalent of fhir-gql's `require_permission()` — one
  check gates an entire sub-tree of routes rather than one route.
- **Belongs in:** Conceptually a `shared IAM service` concern (it's authorization based on
  org-membership role, i.e. "is this user an org admin"), expressed as a **fhir-gql
  (middleware)** dependency if/when fhir-gql grows admin routes, exactly the way
  `require_permission()` already expresses JWT-claim-based authorization as a FastAPI
  dependency today. The pattern (router-level `Depends`/`.use()` gate vs. per-route) is
  directly reusable; the *source of truth* for "is admin" would be a claim BetterAuth's
  organization plugin already puts on the token (commonly `role` or `permissions` scoped to
  the active org), not a resource fhir-gql owns.
- **Port notes for fhir-gql (FastAPI/Python):** If fhir-gql ever exposes org-admin-only
  endpoints, add a `require_org_admin()` dependency factory next to `require_permission()` in
  `app/auth/rbac.py`, following the exact same shape: read a claim off `request.state.user`
  (e.g. `user.get("orgRole") == "admin"` or `"org:admin" in user.get("permissions", [])`) and
  raise `HTTPException(403)` otherwise. Apply it at the `APIRouter(dependencies=[...])` level
  (FastAPI's router-level `dependencies=` param mirrors Express's `router.use(...)`) rather
  than per-endpoint, so a whole `admin_router` inherits the gate the way
  `projectAdminRouter.use(verifyProjectAdmin)` does. No DI container changes needed — this is
  pure claim inspection, same as today's RBAC.
- **Priority:** Medium — cheap to add later (it's a small, additive dependency function) but
  only useful once fhir-gql actually has admin-only mutations to protect. Not worth building
  speculatively.

### Project Membership Read & Update

- **What it does:** Fetches a single member's `ProjectMembership` (their role, access policy,
  profile link) or updates it — e.g. to change a user's access policy or admin flag within the
  project.
- **Source files:** `packages/server/src/admin/project.ts` —
  `projectAdminRouter.get('/:projectId/members/:membershipId', ...)`,
  `projectAdminRouter.post('/:projectId/members/:membershipId', ...)`.
- **How it works:** Reads the `ProjectMembership` by id via `ctx.repo.readResource(...)`, then
  defends against cross-project access with an explicit reference-string comparison —
  `membership.project?.reference !== getReferenceString(ctx.project)` → `403 forbidden`. This
  is a **manual, per-request tenant-isolation check**, not something the repository layer
  enforces automatically for a *specific-id* read (id-based reads bypass the project filter
  that list/search queries get, so the handler must re-verify ownership itself — the exact
  failure mode fhir-gql currently has on `get_patient`/`update_patient`/`delete_patient`, see
  "Context" above). The POST handler additionally requires the body's `resourceType` and `id`
  to match the path, then calls `ctx.repo.updateResource(resource)`.
- **Belongs in:** `shared IAM service` — membership/role management for an organization is
  identity data, not clinical data or orchestration logic. If BetterAuth's organization plugin
  is in use, it almost certainly already exposes equivalent membership-role management.
  fhir-gql should not duplicate a user/role/membership model.
- **Port notes for fhir-gql (FastAPI/Python):** The one directly transferable lesson is the
  **defensive ownership check pattern**, not the membership CRUD itself: any fhir-gql endpoint
  that reads/writes a resource *by id* must independently verify the resource's tenant field
  matches `actor.org_id` before returning/mutating it, because a bare `WHERE id = :id` lookup
  (which is what `PatientClient.get_by_id`/`update`/`delete` currently issue) does not filter
  by tenant the way `list()` does. Concretely: either (a) have the fhir-server itself enforce
  `org_id` on every query keyed by id (requires the fhir-server to also receive `org_id` on
  those calls, which `app/fhir_client/patient.py` does not currently send), or (b) have
  `PatientService` do a `get_by_id` then compare `result["org_id"] != actor.org_id` and raise
  404 before returning, mirroring Medplum's `membership.project?.reference !== ...` check.
  Option (a) is architecturally cleaner for fhir-gql's "thin middleware" role since it avoids
  an extra round trip and keeps the source of truth for scoping in the layer that owns
  persistence.
- **Priority:** Medium-High — not the multi-tenancy *feature* itself (Low priority, see
  Recommended next steps), but the **ownership-check pattern it demonstrates is a live gap** in
  fhir-gql today, independent of whether a Project concept is ever adopted.

### Project Membership Deletion (with owner protection)

- **What it does:** Removes a member from a project. Refuses to delete the project owner.
  If the departing user was project-scoped (an account that exists only inside this project,
  e.g. a Patient-portal login) and this was their only membership anywhere, also deletes the
  underlying `User` resource so no orphaned account is left behind.
- **Source files:** `packages/server/src/admin/project.ts` —
  `projectAdminRouter.delete('/:projectId/members/:membershipId', ...)`.
- **How it works:** Same cross-project ownership check as above, plus
  `ctx.project.owner?.reference === membership.user?.reference` → `400 badRequest` (owner
  cannot be removed). Then, inside `systemRepo.withTransaction(...)`, it searches for *other*
  `ProjectMembership` records for the same user (`count: 2` so it only needs to distinguish
  "1 vs. more than 1" without paying for a full count), deletes the membership, and — only if
  that was genuinely their sole membership and the user record is project-scoped
  (`user.project?.reference === ctx.project`) — deletes the `User` resource too. Non-project
  (server-scoped) users are never auto-deleted, only their membership is removed.
- **Belongs in:** `shared IAM service`. This is user lifecycle management tied to Medplum's
  dual user model (server-scoped vs. project-scoped accounts), a distinction that does not
  exist in fhir-gql's architecture at all — fhir-gql never creates or deletes user accounts;
  BetterAuth owns the entire user table.
- **Port notes for fhir-gql (FastAPI/Python):** Not portable as a feature. The transactional
  "delete membership, then conditionally delete the now-orphaned account" pattern is a useful
  reference *if* fhir-gql's team ever builds an internal admin tool that calls into BetterAuth's
  admin API to offboard a user from an org, but that logic would live in BetterAuth (or a thin
  client calling BetterAuth's admin endpoints), not in `app/auth/rbac.py`, since fhir-gql has no
  membership/user table of its own to transact against.
- **Priority:** Low — pure IAM-service territory; no fhir-gql architecture decision hinges on
  this.

### Project-Scoped Force Password Reset

- **What it does:** Lets a project admin force-set a specific member's password by email,
  without going through the normal reset-email flow (e.g. for support/onboarding).
- **Source files:** `packages/server/src/admin/project.ts` —
  `projectAdminRouter.post('/setpassword', ...)`.
- **How it works:** Validates `email` + `password` (min length 8) via `express-validator`,
  resolves the `User` via `getUserByEmailInProject(email, ctx.project.id)` (project-scoped
  lookup — a server-scoped admin cannot accidentally reset a password outside their project),
  then calls the shared `setPassword(ctx.systemRepo, user, password)` helper.
- **Belongs in:** `shared IAM service` — password/credential management is squarely
  authentication infrastructure. fhir-gql validates JWTs (`app/auth/dependencies.py`) but has
  no password store, no `User` table, and no credential-mutation surface; BetterAuth owns this
  end-to-end.
- **Port notes for fhir-gql (FastAPI/Python):** None — out of scope for fhir-gql by design. If
  a "reset a user's password as an org admin" UI is needed, it should call BetterAuth's admin
  API directly (or through a thin proxy endpoint in fhir-gql that just forwards the call with
  RBAC applied), not be reimplemented against a credential store fhir-gql doesn't have.
- **Priority:** Low — not fhir-gql's responsibility under the current split architecture.

### Project Member MFA Reset

- **What it does:** Lets a project admin reset a member's MFA enrollment (e.g. they lost their
  authenticator device), rotating the TOTP secret and emailing the user a security notice.
- **Source files:** `packages/server/src/admin/project.ts` —
  `projectAdminRouter.post('/:projectId/members/:membershipId/mfa/reset', ...)`.
- **How it works:** Same cross-project membership ownership check as the read/update/delete
  handlers, then `403` if `!user.mfaEnrolled && !user.mfaSecret` (nothing to reset), otherwise
  `systemRepo.updateResource<User>({...user, mfaEnrolled: false, mfaSecret: authenticator.generateSecret()})`
  — regenerating the secret (not just clearing the flag) is the important detail: it prevents
  the old authenticator app entry from still working after a "reset." A best-effort
  notification email is sent afterward.
- **Belongs in:** `shared IAM service` — MFA enrollment is authentication state.
- **Port notes for fhir-gql (FastAPI/Python):** None — fhir-gql doesn't manage MFA; BetterAuth
  does. Same "thin proxy to IAM admin API" note as the password-reset feature above, if this
  is ever needed from a fhir-gql-fronted admin UI.
- **Priority:** Low.

### User Invitation Workflow (Project Membership Provisioning)

- **What it does:** The single most complex feature in this surface: given a name + email (or
  `externalId`) and a target `resourceType` (`Patient`, `Practitioner`, or `RelatedPerson`),
  creates (or reuses) a `User` account, creates (or reuses) the matching FHIR profile resource,
  links them via a `ProjectMembership`, and emails an invite/password-reset link.
- **Source files:** `packages/server/src/admin/invite.ts` — `inviteHandler` (route entry),
  `inviteUser` (orchestrator), `makeUserResource`, `upsertProfileResource`,
  `validateAccessPolicies`, `upsertProjectMembership`, `searchForExistingMembership`,
  `sendInviteEmail` (all internal helpers).
- **How it works, in detail:**
  - **Scope resolution:** `makeUserResource` decides whether the new `User` is
    project-scoped or server-scoped: Patients default to project-scoped, Practitioners/
    RelatedPersons default to server-scoped, but `externalId`-based users and an explicit
    `scope` override always force project-scoping. This dual-scoping model (some users belong
    to exactly one project, others can span projects) does not exist in fhir-gql/BetterAuth's
    world at all — BetterAuth's org model is "one identity, many org memberships," closer to
    Medplum's server-scoped case as the default.
  - **Conflict avoidance:** inside a `serializable` DB transaction, it searches existing
    `ProjectMembership`s for the same email+project combination *at the same scope* to avoid
    silently creating a duplicate/confused identity, then does a `conditionalCreate` keyed on
    email (+ project, if project-scoped) so re-inviting the same email is idempotent rather
    than erroring.
  - **Profile upsert:** `upsertProfileResource` either validates a caller-supplied existing
    profile (must belong to the same project and match `resourceType`), or searches/creates a
    new Patient/Practitioner/RelatedPerson by email within the project, enforcing FHIR-required
    fields (e.g. `RelatedPerson.patient` must reference a Patient in the same project).
  - **Access policy validation:** `validateAccessPolicies` batch-reads every `AccessPolicy`
    reference in the request (top-level, `access[]`, and `membership.access[]`) and rejects the
    invite if any policy doesn't exist or belongs to a different project — cross-tenant
    reference-integrity enforcement, done eagerly rather than relying on a DB constraint.
  - **Membership upsert:** `upsertProjectMembership` applies a project's
    `defaultPatientAccessPolicy` when inviting a Patient with no explicit policy, then either
    creates a new membership or (if `upsert: true`) updates an existing one for the same
    user+project, again inside a serializable transaction guarded by
    `searchForExistingMembership`.
  - **Notification:** `sendInviteEmail` sends different copy for new vs. returning users, and
    — notably — converts an SES/email-provider failure into an `allOk` `OperationOutcome`
    (HTTP 200) rather than a hard error, a deliberate backward-compatibility choice documented
    inline as "a long time ago, we made the mistake of establishing a convention."
- **Belongs in:** `shared IAM service`, unambiguously. This entire feature is about creating
  authentication identities (`User`) and org memberships — the exact thing BetterAuth exists
  to own. The one piece that is *not* purely an IAM concern is "create the clinical profile
  resource this identity is linked to" (the Patient/Practitioner/RelatedPerson), which touches
  `fhir-server (data layer)` — but even that should be initiated as an orchestrated write from
  whichever service handles onboarding (today, unclear if that's fhir-gql, a separate
  onboarding service, or BetterAuth webhooks), not bolted onto fhir-gql's admin surface as a
  copy of Medplum's design.
- **Port notes for fhir-gql (FastAPI/Python):** Do not port this as-is. If fhir-gql needs an
  "invite a new patient user" flow, the correct shape given the current split is: (1) BetterAuth
  creates the identity + org membership via its own invite API (its organization plugin already
  supports this), (2) BetterAuth (or the caller, post-invite) triggers fhir-gql's *existing*
  `POST /patients` endpoint to create the clinical Patient record, passing the new user's `sub`
  as `user_id` and the org as `org_id` — both already required fields on
  `PatientCreateSchema` (`app/schemas/patient/input.py:67`). No new DI wiring is needed for
  this because it reuses `PatientContainer`/`PatientService` exactly as they exist today; the
  only new piece would be a webhook/event receiver if BetterAuth needs to call fhir-gql
  automatically after provisioning an identity, and that receiver would live beside
  `app/routers/patient.py` as its own thin router, not inside `rbac.py`.
- **Priority:** Low for fhir-gql to build directly (identity provisioning is IAM's job), but
  **Medium** to explicitly design the *seam* — i.e., agree with the BetterAuth/IAM team on the
  handoff contract (who calls whom, in what order, with what retries) for "new user → new
  Patient record" — since today that handoff appears to not exist at all (nothing in
  `app/routers/patient.py` suggests an automated trigger; `POST /patients` looks like it's
  called directly by a client, with `user_id`/`org_id` supplied manually).

### OAuth ClientApplication Provisioning (Machine Users)

- **What it does:** Lets a project (or super) admin register a new OAuth2 client
  (`ClientApplication`) scoped to a project — generating a client secret and, importantly,
  creating a `ProjectMembership` *for the client itself*, so the client application acts as its
  own first-class actor with an optional `AccessPolicy`.
- **Source files:** `packages/server/src/admin/client.ts` — `createClientHandler`,
  `createClient`, `CreateClientRequest` interface.
- **How it works:** If the caller is a super admin, the target project is taken from the URL
  param (`req.params.projectId`) rather than the caller's own project — the only place in this
  file set where an admin can act on a project they are not a member of, gated purely by
  `superAdmin`. `createClient` uses `repo.getSystemRepo()` (bypasses access-policy filtering
  entirely — a privileged internal repository) to `createResource<ClientApplication>` with
  `meta.project` stamped to the target project and a freshly generated 32-byte secret
  (`generateSecret(32)`), then immediately creates a matching `ProjectMembership` linking the
  new client (as both `user` and `profile`) to the project, optionally with an `accessPolicy`.
  This is the mechanism that lets Medplum treat machine clients exactly like human members for
  authorization purposes — a `ProjectMembership` is the unit of "can act in this project,"
  regardless of whether the actor behind it is a person or a service.
- **Belongs in:** `shared IAM service`. OAuth client/credential issuance is authentication
  infrastructure; fhir-gql validates bearer JWTs but has no OAuth client registry, no client
  secret storage, and no concept of a "machine ProjectMembership." If fhir-gql ever needs
  service-to-service auth (e.g., a batch job calling its API), the client should be registered
  with BetterAuth (assuming it supports client-credentials grants) and presented to fhir-gql as
  just another JWT with a `permissions` claim — fhir-gql's existing `require_permission()` would
  handle it identically to a human caller's token, with zero new code.
- **Port notes for fhir-gql (FastAPI/Python):** None required. This is the strongest example in
  the whole admin surface of "Medplum built this because Medplum *is* the IAM system"; fhir-gql
  deliberately is not, so this entire feature has no fhir-gql-side counterpart to build.
- **Priority:** Low — not applicable to fhir-gql's architecture.

### Bot Provisioning via Admin API

- **What it does:** Lets a project admin create a `Bot` (Medplum's server-side automation/
  scripting resource — think "serverless function scoped to a project, triggered by FHIR
  events or subscriptions") within their project.
- **Source files:** `packages/server/src/admin/bot.ts` — `createBotHandler`,
  `createBotValidator`.
- **How it works:** Validates `name` is present, then delegates entirely to
  `createBot(ctx.repo, ctx.project, req.body)` (implemented in
  `fhir/operations/botinit.ts`, outside this file's scope) using the caller's already
  project-scoped repository — so the Bot is automatically created inside the caller's project
  with no extra scoping logic needed here.
- **Belongs in:** `fhir-server (data layer)`, if fhir-gql ever needs server-side automation at
  all — a "Bot" is fundamentally a data-layer/execution-runtime concept (stored code, triggered
  by resource writes) closer to fhir-server's persistence and event model than to fhir-gql's
  request-orchestration role. It is not an IAM concern (bots aren't authentication identities in
  spirit, even though Medplum implements them as one for uniformity) and not naturally
  middleware either.
- **Port notes for fhir-gql (FastAPI/Python):** No action — fhir-gql has no automation/scripting
  concept today and none is implied by the current Patient-only scope. If this is ever wanted,
  it is a new capability for fhir-server (or a separate automation service), not something
  `app/di/container.py` or `app/auth/rbac.py` need to anticipate now.
- **Priority:** Low — no current or near-term fhir-gql requirement touches automation/bots.

### Admin Router Composition

- **What it does:** Mounts the two admin sub-routers under a common prefix:
  `/admin/projects/*` → project-scoped admin operations, `/admin/super/*` → instance-wide
  super-admin operations.
- **Source files:** `packages/server/src/admin/routes.ts` — `adminRouter`.
- **How it works:** Trivial Express `Router()` composition:
  `adminRouter.use('/projects/', projectAdminRouter); adminRouter.use('/super/', superAdminRouter);`.
  All authentication/authorization happens inside the two sub-routers (`authenticateRequest` +
  `verifyProjectAdmin`/`requireSuperAdmin`), not here.
- **Belongs in:** N/A as a Medplum feature to port — this is pure routing plumbing. The pattern
  (separate router per privilege tier, each independently gated) is worth noting as a structural
  precedent for `fhir-gql (middleware)` *if* an admin surface is ever built: keep org-admin
  routes and any future "platform admin" routes in physically separate `APIRouter`s with their
  own `dependencies=[...]`, rather than branching on role inside shared handlers.
- **Port notes for fhir-gql (FastAPI/Python):** If/when needed, mirror this with two
  `APIRouter`s (`org_admin_router`, `platform_admin_router`) each carrying its own
  router-level `dependencies=[Depends(require_org_admin(...))]` / a platform-admin equivalent,
  included into `api_router` in `app/routers/__init__.py` exactly like `patients_router` is
  today.
- **Priority:** Low — trivial to add later; no reason to build ahead of need.

### Super Admin Authorization Gate

- **What it does:** Restricts an entire class of operations (schema rebuilds, reindexing,
  database maintenance, cross-project purges) to a single "instance operator" role that sits
  above all projects.
- **Source files:** `packages/server/src/admin/super.ts` — every handler calls
  `requireSuperAdmin()` (imported from `../context`, outside this file set) as its first
  statement, e.g. `requireSuperAdmin(); requireAsync(req);` at
  `packages/server/src/admin/super.ts:63-64` and throughout the file.
- **How it works:** `requireSuperAdmin()` is a context-assertion helper (analogous to
  `getAuthenticatedContext()`) that presumably reads `ctx.project.superAdmin` /
  `ctx.membership.superAdmin` and throws `forbidden` if false, returning the context object
  otherwise (its return value is used later, e.g. `const ctx = requireSuperAdmin();` then
  `ctx.repo`/`ctx.requestId`). Every single route in `super.ts` calls it before doing anything
  else — there is no router-level `.use()` gate here (unlike `verifyProjectAdmin`), each handler
  asserts individually, presumably because some handlers need the returned context object and
  others don't.
- **Belongs in:** Split three ways depending on what's being protected: the *authorization
  primitive itself* ("is this caller a platform operator") is a `shared IAM service` concern —
  BetterAuth would need a "platform admin" role/claim orthogonal to any org membership, since
  super admins act across all tenants. The *operations it protects* (below) are overwhelmingly
  `fhir-server (data layer)` concerns, since they're all database/schema/index maintenance.
- **Port notes for fhir-gql (FastAPI/Python):** Not a fhir-gql concern to implement generally,
  but the *authorization primitive* is directly reusable if fhir-gql ever needs any
  break-glass/operator route (e.g., a cache-flush or rate-limit-override endpoint): add
  `require_platform_admin()` next to `require_permission()` in `app/auth/rbac.py`, sourced from
  a claim BetterAuth would need to add (e.g. `"platform:admin"` in `permissions`, which
  `check_permission()` already knows how to check with zero new code —
  `check_permission(user, "platform", "admin")` would just work against the existing
  `resource:action` string convention).
- **Priority:** Low — no fhir-gql feature currently needs platform-wide operator access; the
  underlying `check_permission()` primitive already supports adding this the moment it's needed.

### Terminology & Metadata Rebuild Operations

- **What it does:** Three super-admin-only async jobs that rebuild built-in FHIR terminology
  and metadata tables (ValueSets, StructureDefinitions, SearchParameters) instance-wide, run
  after Medplum ships changes to these built-ins.
- **Source files:** `packages/server/src/admin/super.ts` —
  `POST /valuesets`, `POST /structuredefinitions`, `POST /searchparameters` handlers
  (`superAdminRouter.post('/valuesets', ...)` etc.).
- **How it works:** Each requires `Prefer: respond-async` (`requireAsync(req)` — else `400`),
  resolves a shard-specific system repo (`getShardSystemRepo(PLACEHOLDER_SHARD_ID)` — Medplum
  supports DB sharding, which fhir-gql/fhir-server show no sign of), and runs the rebuild via
  `sendAsyncResponse` (returns `202 Accepted` with a polling location while the job runs in the
  background using Medplum's `AsyncJob` FHIR resource as a job-status record).
- **Belongs in:** `fhir-server (data layer)` entirely — these operate directly on database
  tables that back FHIR search/validation, which fhir-server owns exclusively.
- **Port notes for fhir-gql (FastAPI/Python):** None — fhir-gql has no terminology/schema
  storage to rebuild; it is a stateless pass-through for the one resource (Patient) it knows
  about.
- **Priority:** Low — not applicable; would only matter if fhir-gql ever became responsible for
  seeding/validating FHIR terminology itself, which contradicts its stated role as a middleware
  layer in front of a fhir-server that owns persistence.

### Resource Reindexing Operation

- **What it does:** Re-derives search-index columns for one, many, or all resource types —
  needed after a change to how a resource type's search parameters are computed, without a full
  data migration.
- **Source files:** `packages/server/src/admin/super.ts` — `POST /reindex` handler.
- **How it works:** Extensive `express-validator` body validation (`reindexType` ∈
  `outdated|all|specific`, conditional `maxResourceVersion` requirement, tunable
  `batchSize`/timeouts/backoff), builds a `ReindexJobOptions`, and dispatches an async
  `addReindexJob` (BullMQ-style background worker job) scoped by shard. Also demonstrates
  Medplum's resource versioning scheme (`Repository.VERSION`) — reindex-by-version lets an
  admin target only rows written under an older search-index format.
- **Belongs in:** `fhir-server (data layer)` — reindexing is inseparable from owning the search
  index/database schema.
- **Port notes for fhir-gql (FastAPI/Python):** None — no search index exists in fhir-gql.
- **Priority:** Low.

### Database Maintenance & Migration Operations

- **What it does:** A cluster of instance-wide DB-operator endpoints: run pending schema
  migrations (`/migrate`, `/migrations`), reconcile drift between expected and actual schema
  (`/reconcile-db-schema-drift`), manually stamp a data version to skip a migration
  (`/setdataversion`), tune Postgres autovacuum table settings (`/tablesettings`), run
  `VACUUM`/`ANALYZE` (`/vacuum`), and backfill the `projectId` column from `compartments[]`
  after a schema change (`/rebuildprojectid`).
- **Source files:** `packages/server/src/admin/super.ts` — `POST /migrate`, `GET /migrations`,
  `POST /reconcile-db-schema-drift`, `POST /setdataversion`, `POST /tablesettings`,
  `POST /vacuum`, `POST /rebuildprojectid`.
- **How it works:** Each is a thin, heavily-validated wrapper around raw SQL/DDL execution
  against `getDatabasePool(DatabaseMode.WRITER)` or migration-runner modules
  (`migration-sql`, `migrations/migrate`, `migrations/migration-utils`). Notably,
  `/tablesettings` and `/vacuum` build **DDL strings by interpolation** because "DDL queries
  cannot be parameterized," guarded instead by an allow-list
  (`OVERRIDABLE_TABLE_SETTINGS`) and an `isValidTableName` regex check — a deliberate,
  narrowly-scoped exception to parameterized-query discipline, only reachable by super admins.
  `/rebuildprojectid` is the most tenancy-relevant of the group: it literally re-derives the
  `projectId` column (the physical column every table filters on for tenant isolation) from the
  `compartments` array on every row of every resource table — i.e., Medplum's project-scoping
  enforcement is a real, physical, indexed column that occasionally needs a full-table repair
  operation, underscoring how deep the multi-tenancy commitment goes at the storage layer.
- **Belongs in:** `fhir-server (data layer)` entirely — schema, indexes, and vacuum/analyze
  tuning are inseparable from whichever service owns the Postgres instance.
- **Port notes for fhir-gql (FastAPI/Python):** None directly. The one transferable insight is
  architectural: **if fhir-gql's team ever does adopt org/project scoping, the enforcement
  mechanism should look like Medplum's `projectId` column** — a real, indexed, physically
  enforced column on every fhir-server table, checked on every query the fhir-server executes —
  rather than something fhir-gql tries to enforce by convention in Python at the middleware
  layer (which is exactly the gap identified in "Context" above: middleware-layer conventions
  get missed, as the `get_by_id`/`update`/`delete` methods show).
- **Priority:** Low as a feature to build; the underlying insight (push tenant enforcement to a
  physical column in fhir-server, not to per-call middleware discipline) is worth carrying into
  the "Recommended next steps" decision below.

### Cleanup & Queue Maintenance Operations

- **What it does:** A grab-bag of instance-wide housekeeping: purge old `AuditEvent`/`Login`
  resources before a given date (`/purge`), delete stale AWS Lambda function versions used for
  Bot execution (`/lambda-cleaner`), remove a stuck bot job from the BullMQ queue
  (`/removebotidjobsfromqueue`), and reload all cron-triggered bot schedules
  (`/reloadcron`).
- **Source files:** `packages/server/src/admin/super.ts` — `POST /purge`,
  `POST /lambda-cleaner`, `POST /removebotidjobsfromqueue`, `POST /reloadcron`.
- **How it works:** `/purge` calls `ctx.repo.purgeResources(resourceType, before)` restricted
  to exactly `AuditEvent`/`Login` via validator — a safety rail against accidentally purging
  clinical resource types. `/lambda-cleaner` and `/reloadcron` are both async jobs
  (`AsyncJobExecutor`) that touch AWS Lambda (bots-as-Lambda-functions, a Medplum deployment
  detail) and a cron worker queue respectively — both tied to Medplum's Bot execution model,
  which fhir-gql has no equivalent of.
- **Belongs in:** `fhir-server (data layer)` for `/purge` (it's deleting rows from tables the
  fhir-server owns); N/A for the Lambda/cron/queue operations since they depend entirely on
  Medplum's Bot-as-Lambda execution architecture, which has no fhir-gql or fhir-server
  counterpart at all.
- **Port notes for fhir-gql (FastAPI/Python):** None for the bot/lambda pieces. `/purge`'s
  *pattern* (a narrowly-scoped, allow-listed cleanup operation restricted to specific
  non-clinical resource types) is a reasonable reference if fhir-gql/fhir-server ever need a
  retention-policy job for, say, expired rate-limit counters or stale idempotency keys — but
  that would be a fhir-server or infra cron job, not a fhir-gql HTTP endpoint.
- **Priority:** Low.

---

## Summary Table

| Feature | Priority | Belongs in |
|---|---|---|
| Project Resource Read & Metadata | Low | shared IAM service |
| Project Settings / Secrets / Sites Configuration | Low | shared IAM service |
| Project Admin Authorization Gate | Medium | shared IAM service (claim source) + fhir-gql (middleware) if built |
| Project Membership Read & Update | Medium-High (pattern), Low (feature) | shared IAM service (feature); fhir-gql (middleware) for the ownership-check pattern |
| Project Membership Deletion | Low | shared IAM service |
| Project-Scoped Force Password Reset | Low | shared IAM service |
| Project Member MFA Reset | Low | shared IAM service |
| User Invitation Workflow | Low (build), Medium (seam design) | shared IAM service (identity) + fhir-server (profile) |
| OAuth ClientApplication Provisioning | Low | shared IAM service |
| Bot Provisioning via Admin API | Low | fhir-server (data layer) |
| Admin Router Composition | Low | fhir-gql (middleware), pattern only |
| Super Admin Authorization Gate | Low | shared IAM service (primitive) |
| Terminology & Metadata Rebuild Operations | Low | fhir-server (data layer) |
| Resource Reindexing Operation | Low | fhir-server (data layer) |
| Database Maintenance & Migration Operations | Low (feature), informs architecture | fhir-server (data layer) |
| Cleanup & Queue Maintenance Operations | Low | fhir-server (data layer) / N/A |

---

## Recommended next steps

**Do not build a Medplum-style `Project` resource, admin API, or membership model inside
fhir-gql.** Every genuinely multi-tenancy-relevant feature in this admin surface — project
CRUD, membership, invites, roles, password/MFA resets, OAuth client and bot provisioning — is
either identity/authentication territory that BetterAuth already owns (and likely already
solves via its `organization` plugin, which is functionally Medplum's Project +
ProjectMembership + invite flow under different names) or physical data-layer territory
(`projectId` columns, reindexing, vacuum tuning) that belongs to fhir-server. Building a
parallel `Project` concept inside fhir-gql would mean maintaining a second, competing source of
truth for "what organizations exist and who's in them," which is worse than the status quo, not
better — and per this document's own instructions, retrofitting multi-tenancy later is
expensive, so the wrong move here (building a shadow copy of IAM's org model) is exactly the
kind of decision that should not be made by default.

**What fhir-gql *should* do, and soon, is close the tenant-isolation gap that already exists
in its current single-org-field design**, independent of any Project decision: `get_patient`,
`update_patient`, `delete_patient`, and every sub-resource endpoint in
`app/routers/patient.py` operate on a bare integer id with no `org_id` sent to or enforced by
the fhir-server, unlike `list_patients`/`get_me` which do filter by `org_id`. Concretely:
1. Confirm with the fhir-server team whether `org_id` is already independently re-derived and
   enforced server-side on every by-id operation (in which case fhir-gql's gap is cosmetic), or
   whether fhir-gql is the only layer that ever sees `org_id` on these calls (in which case this
   is a live cross-tenant data leak).
2. If the latter, thread `actor.org_id` through `PatientClient.get_by_id/patch/delete` (and the
   sub-resource equivalents) exactly as it's already threaded through `list()`, following
   Medplum's `membership.project?.reference !== ctx.project` defensive-check pattern from
   `admin/project.ts` as the template — either as a query parameter the fhir-server enforces, or
   as a fhir-gql-side comparison against the fetched resource before returning it.

**Revisit the Project question only if a concrete trigger appears** — e.g., fhir-gql needs to
expose org-scoped configuration fhir-server doesn't have anywhere else to live, or a second
downstream service needs fhir-gql to broker cross-org authorization decisions BetterAuth's
claims can't express. Until then, fhir-gql's correct posture is: stay a thin, stateless
relay of the `org_id`/`permissions` claims BetterAuth already issues, enforce them
*consistently* (the gap above), and leave org/project lifecycle management entirely to
BetterAuth and physical tenant-column enforcement entirely to fhir-server.
