# Identity, Authentication & Access — Medplum vs. fhir-gql

Scope: everything under Medplum `packages/server/src/auth/`, `src/oauth/`, and `src/scim/`, compared
against what already exists in `fhir-gql` (`app/auth/dependencies.py`, `app/auth/rbac.py`,
`app/auth/models.py`) and what the project's split architecture implies.

**Architecture reminder used throughout this document:** Medplum is a monolith — it issues its own
JWTs, owns the `User`/`Login`/`ProjectMembership`/`ClientApplication` resources, and persists
everything in one Postgres. `fhir-gql` is *not* that. It is a middleware layer in front of a
separate `fhir-server` (owns FHIR resource persistence — currently only `Patient`) and delegates
token issuance entirely to a separate **BetterAuth/IAM service**. `fhir-gql` today already
implements: JWT verification via JWKS (`PyJWKClient`, `app/auth/dependencies.py`), issuer/audience
validation, a `get_current_user` FastAPI dependency, and a coarse `resource:action` string-based RBAC
check shared between REST (`require_permission()`) and GraphQL (`require_gql_permission()`) — see
`app/auth/rbac.py` and `app/gql/permissions.py`. There is no password storage, no session/cookie
handling, no MFA, no OAuth2 authorization-server logic, and no SCIM anywhere in `fhir-gql` today —
by design, since BetterAuth is expected to own identity issuance.

---

## 1. Password-Based Authentication

### Password Login
- **What it does:** Authenticates a user with email + password and starts a `Login` flow that may
  need further steps (MFA, profile selection, scope consent) before an access token is issued.
- **Source files:** `auth/login.ts` (`loginHandler`, `loginValidator`), `oauth/utils.ts`
  (`tryLogin`, `authenticate`).
- **How it works:** Validates email format and 8+ char password via `express-validator`. Resolves
  `projectId` either explicitly or via `clientId`. Calls `tryLogin()`, which looks up the `User` by
  email, bcrypt-compares the password hash (`bcrypt.compare`), creates a `Login` resource
  (auth code, cookie secret, optional refresh secret), and resolves 0/1/N `ProjectMembership`
  candidates. Single membership auto-selects and returns an auth `code`; multiple memberships defer
  to `/auth/profile`.
- **Belongs in:** `shared IAM service` — password storage/verification and `Login` state machine are
  exactly what BetterAuth is meant to own; `fhir-gql` only ever sees the *finished* JWT.
- **Port notes for fhir-gql:** No action needed in `fhir-gql` itself. If BetterAuth doesn't already
  implement email+password login, that's a BetterAuth backlog item, not this repo's.
- **Priority:** Low (for fhir-gql) — out of this repo's ownership boundary, already delegated.

### Login Method Discovery (`/auth/method`)
- **What it does:** Given an email, tells the client whether to do normal password login or redirect
  to an external IdP (domain-based SSO routing) — without revealing whether the account exists.
- **Source files:** `auth/method.ts` (`methodHandler`, `isExternalAuth`, `getDomainConfiguration`).
- **How it works:** Splits the email domain, looks up a `DomainConfiguration` FHIR resource for that
  domain; if it has an `identityProvider`, builds and returns an `authorizeUrl` for that IdP's OAuth
  authorize endpoint. Explicitly documented as leaking domain-config existence but not user existence
  (anti-enumeration design).
- **Belongs in:** `shared IAM service` — domain-to-IdP routing is an IAM concern.
- **Port notes for fhir-gql:** N/A directly; if fhir-gql ever needs to render a "sign in with SSO"
  button, it should call a BetterAuth-exposed equivalent rather than reimplement domain lookup.
- **Priority:** Low.

---

## 2. Self-Service Registration & Onboarding

### New User Registration (`/auth/newuser`)
- **What it does:** Public sign-up: creates a `User` record with a bcrypt password hash, optionally
  scoped to a project, then immediately starts a login. Rejects breached passwords.
- **Source files:** `auth/newuser.ts` (`newUserHandler`, `createUser`, `newUserValidator`).
- **How it works:** Validates first/last name, email, password (8–72 bytes). Checks for an existing
  user with that email (project-scoped or global). Calls `pwnedPassword()` (k-anonymity query against
  the HaveIBeenPwned API via the `hibp` package) and rejects any password with `numPwns > 0`. Hashes
  with bcrypt (`bcryptHashPassword`, using a server-configured salt round count), creates the `User`,
  then calls `tryLogin()`. If email verification is required for new-project creation, fires a
  verification email via `verifyEmail()` + `sendEmail()`.
- **Belongs in:** `shared IAM service` — user creation/credentialing is IAM's job end-to-end.
- **Port notes for fhir-gql:** Not applicable to fhir-gql's own code. Worth flagging to whoever owns
  BetterAuth that breached-password checking (HIBP integration) is a real security feature clinical
  platforms should have and may not exist yet there.
- **Priority:** Low (for fhir-gql); Medium note-to-IAM-team on the HIBP check specifically.

### New Project Creation (`/auth/newproject`)
- **What it does:** Lets a freshly-registered user spin up their own tenant ("Project" in Medplum
  terms), with a default `ClientApplication`, admin `ProjectMembership`, and profile — the org/tenant
  self-onboarding flow.
- **Source files:** `auth/newproject.ts` (`newProjectHandler`), `fhir/operations/projectinit.ts`
  (`createProject`, referenced not read in full but invoked here).
- **How it works:** Requires a partial `Login` (post password/OAuth auth, pre-membership). Optionally
  gates on `requireVerifiedEmailForProjectCreation`. Delegates to `createProject()` to build the
  Project/membership/client bundle, then finalizes the login via `setLoginMembership`.
- **Belongs in:** `shared IAM service` for the tenant/org creation and membership bootstrap;
  conceptually equivalent to "organization" creation in a BetterAuth multi-tenant setup (fhir-gql's
  JWT already carries `activeOrganizationId`, implying org creation happens upstream).
- **Port notes for fhir-gql:** No server code needed here; if fhir-gql exposes an "org signup" UX at
  all, it should be a thin pass-through to BetterAuth's org APIs, not new business logic in this repo.
- **Priority:** Low.

### New Patient Self-Registration (`/auth/newpatient`)
- **What it does:** The patient-portal equivalent of new-project: given a *partial* login (user has
  authenticated but has no `ProjectMembership` yet) and a target project, creates a `Patient` FHIR
  resource, applies the project's `defaultPatientAccessPolicy`, and creates the membership binding
  user↔Patient↔access-policy — i.e., open patient self-registration for a portal.
- **Source files:** `auth/newpatient.ts` (`newPatientHandler`, `createPatient`),
  `auth/utils.ts` (`createProfile`, `createProjectMembership`).
- **How it works:** Reads the `Login`, rejects if already bound to a membership. Loads the `User`
  (must already be scoped to a project). Reads the target `Project`; if it has no
  `defaultPatientAccessPolicy` configured, registration is rejected outright (`Project does not allow
  open registration`) — this is the key authorization gate that makes open self-registration opt-in
  per tenant. Creates a bare-bones `Patient` resource (`createProfile`) with name + email telecom,
  then a `ProjectMembership` scoped to the default patient access policy, and finally binds it to the
  `Login`.
- **Belongs in:** `split across fhir-gql (middleware) + fhir-server (data layer) + shared IAM service`
  — this is the single most directly relevant feature in this whole document because fhir-gql's only
  implemented resource today is `Patient`. Concretely: (1) BetterAuth/IAM creates/owns the `User` and
  session; (2) **fhir-gql** should own the *orchestration* — deciding a "new patient portal signup" is
  allowed, calling the downstream fhir-server to create the `Patient` resource, and telling IAM to
  attach `activeOrganizationId`/permissions to the user's session; (3) **fhir-server** persists the
  actual `Patient` resource.
- **Port notes for fhir-gql:** This is the strongest candidate for a genuinely new fhir-gql
  capability. Suggested shape: a new `POST /api/v1/auth/self-register-patient` (or a mutation)
  endpoint in `app/routers/` that (a) requires a valid-but-unscoped JWT from BetterAuth (a "pending"
  user state — needs a BetterAuth contract for this), (b) validates the target org allows open
  patient registration (equivalent of `defaultPatientAccessPolicy` — could be an org setting fetched
  from IAM or a config flag), (c) calls `PatientService.create()` (already exists per
  `app/services/patient_service.py`) to create the `Patient` resource on fhir-server, (d) calls back
  to BetterAuth to bind `org_id` + `patient_id` + default patient permissions to the user. This needs
  a new BetterAuth API contract (bind-membership-after-signup) that doesn't appear to exist in the
  auth surface read so far — flag as a cross-team dependency.
- **Priority:** High — directly extends the one resource fhir-gql already supports, and is a common
  requirement for patient-portal-style clinical platforms.

### Registration Utility (`registerNew` / seed flow)
- **What it does:** A combined "create user + create project" helper used for test fixtures/first-run
  seeding, not a real production endpoint.
- **Source files:** `auth/register.ts` (`registerNew`).
- **How it works:** Directly creates a `User` (or reuses existing), calls `tryLogin`, then
  `createProject`, then issues tokens via `getAuthTokens` — bypassing HTTP validation since it's
  meant for tests/seeding only (explicitly commented "Do not use this method in production code!").
- **Belongs in:** `out of scope for fhir-gql` — this is Medplum-internal test/seed tooling, not a
  real feature surface.
- **Port notes for fhir-gql:** None; fhir-gql's equivalent would be a `conftest.py` fixture or a
  local dev-seed script, unrelated to production auth code.
- **Priority:** Low.

---

## 3. Password & Account Recovery

### Password Reset Request (`/auth/resetpassword`)
- **What it does:** "Forgot password" — emails a reset link without revealing whether the account
  exists (anti-enumeration).
- **Source files:** `auth/resetpassword.ts` (`resetPasswordHandler`, `resetPassword`).
- **How it works:** Blocks reset for externally-authenticated accounts (SSO users have no local
  password). Searches for the `User` by exact email (+ optional project scope). Regardless of
  found/not-found, ultimately responds `200 OK` (`allOk`) to prevent account enumeration per OWASP
  guidance — but only *sends the email* if a user was actually found. Creates a `UserSecurityRequest`
  (type `reset`) with a random secret (`generateSecret(16)`, i.e. 16 random bytes hex-encoded) and
  emails a `setpassword/{id}/{secret}` link.
- **Belongs in:** `shared IAM service`.
- **Port notes for fhir-gql:** N/A — no local password store in fhir-gql to reset.
- **Priority:** Low.

### Set Password (`/auth/setpassword`)
- **What it does:** Consumes a password-reset (or account-invite) token and sets a new password,
  revoking all existing sessions for that user as a security measure.
- **Source files:** `auth/setpassword.ts` (`setPasswordHandler`, `setPassword`).
- **How it works:** Loads the `UserSecurityRequest` by ID, checks `used` flag, rejects
  `type === 'verify-email'` requests (wrong endpoint), and compares the secret with
  `timingSafeEqualStr` (constant-time comparison to prevent timing side-channel attacks on the
  secret). On success: HIBP-checks the new password, bcrypt-hashes it, marks the security request
  `used`, and — critically — revokes every active `Login` for that user (`activeSessions` loop sets
  `revoked: true`), forcing re-authentication everywhere.
- **Belongs in:** `shared IAM service`.
- **Port notes for fhir-gql:** N/A directly, but the *pattern* (revoke-all-sessions-on-credential-
  change) is worth confirming BetterAuth actually does — if fhir-gql ever caches decoded JWTs or
  session state, it would need a way to react to a BetterAuth-side revocation event.
- **Priority:** Low for fhir-gql; worth a cross-team question about whether BetterAuth session
  revocation is instant or waits for JWT `exp`.

### Change Password (`/auth/changepassword`)
- **What it does:** Authenticated in-app "change my password" (requires knowing the old password).
- **Source files:** `auth/changepassword.ts` (`changePasswordHandler`, `changePassword`).
- **How it works:** Requires an authenticated session (`getAuthenticatedContext()`). Verifies
  `oldPassword` against the stored bcrypt hash before allowing `newPassword` to be set via the same
  `setPassword()` helper used above (so it also gets the HIBP check + session revocation side effect).
- **Belongs in:** `shared IAM service`.
- **Port notes for fhir-gql:** N/A.
- **Priority:** Low.

### Email Verification (`/auth/verifyemail`)
- **What it does:** Confirms a user controls the email address they registered with, via a
  time-unbounded but single-use token link.
- **Source files:** `auth/verifyemail.ts` (`verifyEmailHandler`, `verifyEmail`).
- **How it works:** Same `UserSecurityRequest` pattern as password reset (type `verify-email`),
  constant-time secret comparison, then a transaction (`systemRepo.withTransaction`) that atomically
  sets `User.emailVerified = true` and marks the request `used`. Supports an optional `redirectUri` to
  bounce the browser back to a client app after verifying (returned as a `redirectOk` outcome rather
  than a real HTTP redirect, so SPA clients can control navigation).
- **Belongs in:** `shared IAM service`.
- **Port notes for fhir-gql:** N/A.
- **Priority:** Low.

---

## 4. Multi-Factor Authentication (TOTP)

### MFA Enrollment, Verification & Disable
- **What it does:** TOTP-based two-factor auth (Google Authenticator-style): generate a secret + QR
  code, confirm enrollment with a live code, require the code at login, and allow disabling (with
  re-verification).
- **Source files:** `auth/mfa.ts` (`mfaRouter`: `GET /status`, `POST /login-enroll`, `POST /enroll`,
  `POST /verify`, `POST /disable`), `oauth/utils.ts` (`verifyMfaToken`).
- **How it works:** Uses `otplib`'s `authenticator` for TOTP secret generation/verification
  (`authenticator.generateSecret()`, `authenticator.verify({token, secret})`, configurable
  verification window via `mfaAuthenticatorWindow`) and the `qrcode` package (`toDataURL`) to render
  an enrollment QR code from an `otpauth://` URI (`authenticator.keyuri`). Two enrollment code paths:
  authenticated in-app enrollment (`/enroll`) and enrollment-during-login (`/login-enroll`, for
  first-time-mandatory-MFA users tied to a specific `Login`). `sendLoginResult()` (in `auth/utils.ts`)
  is the gate that decides whether a fresh login needs an MFA step: checks `user.mfaRequired` (org
  policy) vs `user.mfaEnrolled` vs `login.mfaVerified`, and returns `mfaEnrollRequired` /
  `mfaRequired` flags to the client instead of a final auth code until MFA clears.
  On disable, a *new* secret is generated immediately (not reused) so a lost/stolen 2FA device can't
  be replayed later.
- **Belongs in:** `shared IAM service` — TOTP secret storage and verification is core IAM identity
  state.
- **Port notes for fhir-gql:** N/A for fhir-gql code, but this is a clinically-relevant gap to flag:
  HIPAA-adjacent platforms commonly require MFA for practitioner accounts. If BetterAuth doesn't
  already support TOTP, `pyotp` + `qrcode` are the direct Python equivalents of `otplib`/`qrcode` used
  here, but that work belongs in BetterAuth, not fhir-gql.
- **Priority:** Medium (as a flag to raise with the IAM team, not as fhir-gql work) — MFA absence is a
  security gap worth knowing about even though it's out of this repo's hands.

---

## 5. Session / Login Lifecycle Management

### Multi-Profile Selection (`/auth/profile`)
- **What it does:** When one login (one email) maps to multiple `ProjectMembership`s (e.g. a
  practitioner who is also a patient, or belongs to multiple orgs), lets the client pick which
  profile/org to act as.
- **Source files:** `auth/profile.ts` (`profileHandler`).
- **How it works:** Takes `login` + `profile` (membership ID) from the client, reads the
  `ProjectMembership`, and calls `setLoginMembership()` to bind it to the in-flight `Login`
  (validates it belongs to the same user, isn't inactive, satisfies project auth requirements like
  `google-auth-required`, and passes IP access rules) before returning the final auth code.
- **Belongs in:** `shared IAM service` — directly maps to BetterAuth's `activeOrganizationId`
  switching concept, which fhir-gql's JWT already reflects.
- **Port notes for fhir-gql:** N/A; fhir-gql just needs to keep trusting whatever `org_id` /
  `activeOrganizationId` claim BetterAuth puts on the token it validates.
- **Priority:** Low.

### Scope Selection / Incremental Consent (`/auth/scope`)
- **What it does:** Lets a user narrow (never widen) the OAuth scope of an in-flight login — e.g. a
  SMART app asking for a subset of previously-granted permissions.
- **Source files:** `auth/scope.ts` (`scopeHandler`), `oauth/utils.ts` (`setLoginScope`,
  `matchesScope`).
- **How it works:** Parses both the existing granted scope and the newly requested scope into
  structured `SmartScope` objects (`parseSmartScopes`), and for every requested scope, requires it be
  a strict subset (same resource type/permission type, permission-letters subset, matching search
  `criteria`) of an already-existing granted scope — pure escalation prevention, not consent UI.
- **Belongs in:** `shared IAM service` / `out of scope for fhir-gql` — SMART scope negotiation only
  matters if fhir-gql itself becomes a SMART-on-FHIR authorization server, which the current
  architecture explicitly delegates elsewhere.
- **Port notes for fhir-gql:** None now. If fhir-gql's RBAC model (flat `resource:action` strings)
  ever needs SMART-style granularity (`patient/Observation.read`, compartment-scoped access), that's
  a much larger RBAC redesign — see the RBAC gap note in the OAuth2 Authorization Server section
  below.
- **Priority:** Low.

### Login Status Polling (`/auth/login/:login`)
- **What it does:** Lets a client poll an in-flight `Login`'s state (used after returning from an
  external IdP redirect, before the client has a final code).
- **Source files:** `auth/status.ts` (`statusHandler`).
- **How it works:** Reads the `Login` by ID; rejects if already `granted` or `revoked`; otherwise
  returns the same `sendLoginResult()` payload used everywhere else (MFA-required / profile-selection
  / final code).
- **Belongs in:** `shared IAM service`.
- **Port notes for fhir-gql:** N/A.
- **Priority:** Low.

### Client Branding Info (`/auth/clientinfo/:clientId`)
- **What it does:** Unauthenticated endpoint that returns a client app's sign-in page branding
  (welcome text, logo) so a login UI can theme itself before the user authenticates.
- **Source files:** `auth/clientinfo.ts` (`clientInfoHandler`).
- **How it works:** Looks up `ClientApplication.signInForm`, rewrites any attachment URLs to
  presigned URLs (`rewriteAttachments(RewriteMode.PRESIGNED_URL, ...)`) before returning.
- **Belongs in:** `shared IAM service` — cosmetic per-tenant login page config.
- **Port notes for fhir-gql:** N/A — fhir-gql has no login UI of its own.
- **Priority:** Low.

### Revoke / Logout Session
- **What it does:** Two related but distinct capabilities: `/auth/revoke` lets a user revoke a
  *specific* named login/session (e.g. "sign out that device" from a session list); `/oauth2/logout`
  revokes the *current* session and clears its cookie.
- **Source files:** `auth/revoke.ts` (`revokeHandler`), `oauth/logout.ts` (`logoutHandler`),
  `oauth/utils.ts` (`revokeLogin`).
- **How it works:** Both ultimately call `revokeLogin()`, which just flips `Login.revoked = true`
  (soft revocation checked on every subsequent token-validation path). `revokeHandler` additionally
  verifies the target login belongs to the requesting user (`login.user.reference !==
  ctx.membership.user.reference` → 404, not 403, to avoid confirming existence of other users'
  sessions). `logoutHandler` also clears the `medplum-{clientId}` cookie.
- **Belongs in:** `shared IAM service` for the actual session-store mutation; **fhir-gql (middleware)**
  arguably wants a thin `/api/v1/auth/logout` passthrough purely so REST/GraphQL clients have one
  consistent place to call regardless of which service ultimately owns session state, plus so
  fhir-gql can clear anything it caches about the caller.
- **Port notes for fhir-gql:** If added, this would be a simple router that forwards to BetterAuth's
  revoke/logout API and returns 204 — no new business logic, since fhir-gql holds no session store
  itself (JWTs are stateless from its point of view; it just stops trusting a token once BetterAuth's
  revocation is reflected in future JWKS/`exp` behavior).
- **Priority:** Medium — worth having *a* logout endpoint for API consistency, even if it's a thin
  proxy; Low if BetterAuth is called directly by clients for this.

### User-Facing "Who Am I" Endpoint (`/auth/me`)
- **What it does:** Returns everything a signed-in client needs to render itself: profile, project,
  membership, computed access policy, active MFA/session list, and UI menu config — the one big
  "bootstrap" call after login.
- **Source files:** `auth/me.ts` (`meHandler`, `getUserConfiguration`, `getUserConfigurationMenu`,
  `getSessions`).
- **How it works:** Pulls `authState` (already resolved by the auth middleware) and assembles: the
  `User`/`Project`/`ProjectMembership` triad, a computed `UserConfiguration` (with a hardcoded
  favorites/admin/super-admin menu tree based on role flags), the resolved `AccessPolicy`
  (`getAccessPolicyForLogin`), and — only if `membership.user` is a real `User` (not a bot/client) — a
  `UserSecurity` block listing MFA enrollment and active sessions from the last hour (`Login` search
  filtered by `_lastUpdated > now-1h`, enriched with parsed browser/OS via `Bowser`).
- **Belongs in:** `shared IAM service` for the identity/session parts; **fhir-gql (middleware)** could
  reasonably expose a *much smaller* `/api/v1/me` that just echoes the already-validated JWT claims
  (`sub`, `org_id`, `permissions`) for client convenience — but that's trivial and arguably
  unnecessary since the client already has the JWT it sent.
- **Port notes for fhir-gql:** Low-effort optional convenience endpoint: `GET /api/v1/auth/me`
  returning `AuthUser` (already exists as a dataclass in `app/auth/models.py`) plus raw permissions
  list from `request.state.user`. No new auth logic — just a read of what `get_current_user` already
  populated.
- **Priority:** Low — nice-to-have, not a gap in security or correctness.

---

## 6. Federated / External Identity

### Google Sign-In (`/auth/google`)
- **What it does:** "Sign in with Google" — verifies a Google-issued ID token client-side credential
  and either logs in an existing user or (if allowed) creates one.
- **Source files:** `auth/google.ts` (`googleHandler`, `getProjectsByGoogleClientId`).
- **How it works:** Verifies the Google JWT against Google's live JWKS
  (`createRemoteJWKSet('https://www.googleapis.com/oauth2/v3/certs')`) with `jose`'s `jwtVerify`,
  checking issuer `accounts.google.com`, algorithm RS256, and audience = the caller-supplied
  `googleClientId`. Supports multi-tenant Google Client IDs: if the client ID isn't Medplum's main
  one, it must be registered against a specific `Project` (`google-client-id` search parameter),
  restricting sign-in to that project only. Auto-provisions a `User` on first sign-in if
  `createUser` is requested and registration is enabled. Delegates the actual login/token issuance to
  the same `tryLogin()` used by password auth (`authMethod: 'google'`).
- **Belongs in:** `shared IAM service`.
- **Port notes for fhir-gql:** N/A directly. This is a BetterAuth social-provider integration
  concern; BetterAuth already has first-class Google OAuth plugin support in most configurations.
- **Priority:** Low.

### Generic External IdP Federation (Enterprise SSO / SAML-adjacent OIDC)
- **What it does:** The general-purpose "any OIDC-compliant enterprise IdP" login flow (Okta, Azure
  AD, generic OIDC) — the callback leg of a full authorization-code redirect dance initiated by
  `/auth/method`'s `authorizeUrl`.
- **Source files:** `auth/external.ts` (`externalCallbackHandler`, `getIdentityProvider`,
  `resolveExternalLoginIdentity`, `verifyExternalCode`, `isValidReturnToUrl`,
  `isDangerousRedirectUriPartialMatchAllowed`).
- **How it works:** Receives `code` + `state` (state is a JSON blob the server itself constructed and
  round-tripped, not an opaque token — carries domain/issuer/projectId/clientId/PKCE params/nonce).
  Resolves the `IdentityProvider` config from the `ClientApplication`, `DomainConfiguration`, or a
  server-level `externalAuthProviders` config matching the state's `issuer`. Exchanges the code for
  tokens at the IdP's token endpoint directly (server-to-server `fetch`, supporting both
  `client_secret_basic` and `client_secret_post`, plus optional PKCE `code_verifier`), extracting
  claims from the returned `id_token` (`parseJWTPayload` — notably *not* signature-verified again
  here, since it just came from a direct, authenticated server-to-server call to the IdP). Maps the
  IdP identity to a Medplum login identity via one of two configurable strategies:
  `identitySource: 'email' + identityMappingMode: 'user-email'` (match by email) or
  `identitySource: 'subject' + identityMappingMode: 'project-membership-external-id'` (match by
  opaque external ID, for cases where email isn't a stable/available identifier). Includes an SSRF
  guard (`validateOutboundUrl`) before ever fetching an admin-configured token URL, and a `returnTo`
  allow-list check (`isValidReturnToUrl`) against `DomainConfiguration.allowedPostLoginRedirectUrls`
  before honoring a client-supplied redirect target.
- **Belongs in:** `shared IAM service` — full enterprise SSO federation is squarely an IAM concern;
  most mature BetterAuth deployments would use its generic-OIDC or SAML plugin for this rather than
  fhir-gql reimplementing it.
- **Port notes for fhir-gql:** N/A for fhir-gql itself. Worth noting as reference: the
  email-vs-subject identity-mapping duality and the SSRF/redirect-allow-list hardening are both
  patterns worth verifying BetterAuth's config actually enforces, since a misconfigured external IdP
  integration is a classic account-takeover vector.
- **Priority:** Low (for fhir-gql); Medium as a "verify this is hardened" note for whoever configures
  BetterAuth's SSO integrations.

### External Token Exchange (deprecated helper) / RFC 8693 Token Exchange
- **What it does:** Lets a client that already holds an *external* IdP access token trade it directly
  for a Medplum token, without a redirect round-trip — used for native/mobile apps that obtained a
  token via a platform SDK (e.g. Firebase Auth, Cognito) rather than a browser redirect.
- **Source files:** `auth/exchange.ts` (`exchangeHandler` — deprecated, delegates into
  `oauth/token.ts`), `oauth/token.ts` (`handleTokenExchange`, `exchangeExternalAuthToken`,
  `resolveExternalAuthProvider`, `getExternalAuthLoginIdentity`).
- **How it works:** Implements OAuth 2.0 Token Exchange (RFC 8693) as
  `grant_type=urn:ietf:params:oauth:grant-type:token-exchange`. Validates `subject_token_type` is
  `access_token` only (no other token types supported). Resolves the identity provider either from
  server config (`externalAuthProviders`, matched by `clientId`) or from a `ClientApplication`'s
  configured `identityProvider`. Calls the IdP's userinfo endpoint (`getExternalUserInfo` in
  `oauth/utils.ts`) to validate the subject token is live and extract identity, then funnels into the
  same `tryLogin()` path (`authMethod: 'exchange'`). Supports a `userInfoMode: 'gcip'` special case
  for Google Cloud Identity Platform's non-standard batch-lookup userinfo shape.
- **Belongs in:** `shared IAM service`.
- **Port notes for fhir-gql:** N/A — this is exactly the kind of grant-type logic that should live
  entirely inside BetterAuth if it's needed at all; fhir-gql should never see raw external-IdP tokens.
- **Priority:** Low.

---

## 7. OAuth2 / OIDC Authorization Server Core

**Framing note:** Everything in this section is Medplum acting as a full OAuth2 Authorization Server
+ OIDC Provider (`/oauth2/authorize`, `/oauth2/token`, `/oauth2/userinfo`, `/.well-known/jwks.json`,
`/oauth2/register`, `/oauth2/introspect`). Per the assignment's framing, `fhir-gql` explicitly
delegates JWT *issuance* to BetterAuth — so unless there's a concrete product reason for `fhir-gql`
to become its own authorization server (e.g. it needs to issue *scoped-down* tokens to third-party
SMART apps independently of BetterAuth), **all of section 7 belongs to the shared IAM service**, not
`fhir-gql`. Each entry below still gets full treatment per the assignment's instructions, with that
judgment repeated per-feature for clarity.

### Authorization Endpoint (`GET/POST /oauth2/authorize`)
- **What it does:** The OIDC/OAuth2 "authorize" endpoint — entry point for the authorization-code
  flow, including SMART-on-FHIR app launch, single-sign-on via cookie, silent auth (`prompt=none`),
  and re-consent flows.
- **Source files:** `oauth/authorize.ts` (`authorizeGetHandler`, `authorizePostHandler`,
  `validateAuthorizeRequest`, `getExistingLogin`, `getExistingLoginFromIdTokenHint`,
  `getExistingLoginFromCookie`, `isValidAudience`, `isValidLaunch`).
- **How it works:** Validates `client_id` → `ClientApplication`, then the `redirect_uri` against the
  client's registered URIs (exact match by default; a legacy "dangerous partial match" opt-in exists
  per-project). Validates `response_type=code` only (implicit/hybrid unsupported), rejects the OIDC
  `request` (JAR) parameter as explicitly unsupported, validates `aud` matches the server's own
  origin (SMART requirement), validates PKCE `code_challenge`/`code_challenge_method` pairing, and
  validates an optional `launch` parameter against a real `SmartAppLaunch` resource (SMART launch
  context). Resolves an "existing login" from either an `id_token_hint` (JWT, decoded and matched to
  a `Login` by `login_id` claim) or a `medplum-{clientId}` cookie (SSO), bounded by a `max_age`
  freshness check. `prompt=none` short-circuits straight to a redirect with a fresh code if a valid
  existing login is found, or errors `login_required` if not. Otherwise falls through to the
  server-rendered `/oauth` consent/login page via `sendSuccessRedirect`.
- **Belongs in:** `shared IAM service` — full OAuth2 authorization-endpoint semantics, PKCE
  enforcement, and SMART launch-context validation are the core of what an authorization server does;
  this is precisely the kind of endpoint the project's split architecture already delegates away from
  fhir-gql.
- **Port notes for fhir-gql:** None — do not implement in fhir-gql.
- **Priority:** Low for fhir-gql (explicitly out of scope per project architecture); flag to IAM team
  only if SMART-on-FHIR third-party app support is ever a product requirement.

### Token Endpoint — Multi-Grant Dispatcher (`POST /oauth2/token`)
- **What it does:** The single endpoint that mints all Medplum access/refresh/ID tokens, dispatching
  across five distinct OAuth2 grant types.
- **Source files:** `oauth/token.ts` (`tokenHandler` and its five handlers:
  `handleClientCredentials`, `handleAuthorizationCode`, `handleRefreshToken`, `handleTokenExchange`,
  `handlePreAuthorizedCode`).
- **How it works:** Requires `application/x-www-form-urlencoded` body; dispatches on `grant_type`.
  See the four sub-entries below for grant-specific mechanics. Client authentication is resolved once
  up front via `getClientIdAndSecret()`, which tries — in order — `client_assertion` (private_key_jwt,
  RFC 7523), an `Authorization: Basic` header, an mTLS client-certificate header
  (`config.mtlsCertHeader`), then finally plain form-body `client_id`/`client_secret`.
- **Belongs in:** `shared IAM service`.
- **Port notes for fhir-gql:** None.
- **Priority:** Low.

### Client Credentials Grant
- **What it does:** Server-to-server (machine) authentication — a backend service authenticates as
  itself, not on behalf of a user.
- **Source files:** `oauth/token.ts` (`handleClientCredentials`).
- **How it works:** Requires `client_id` + `client_secret` (via any of the auth methods above),
  validates the `ClientApplication` is `active`, finds its bound `ProjectMembership`
  (`getClientApplicationMembership` — a membership whose `user` reference is the client app itself),
  creates a `Login` with `authMethod: 'client'`, `granted: true` immediately (no user interaction
  needed), checks IP access rules, and issues tokens.
- **Belongs in:** `shared IAM service`. Notably, this is the grant type fhir-gql's *own* backend
  identity (if it needs to call other services as itself) would consume as a *client*, not implement
  as a *server* — worth distinguishing those two roles clearly in any future design doc.
- **Port notes for fhir-gql:** None to implement; if fhir-gql itself needs a service-identity token
  (e.g. to call fhir-server with its own credentials rather than forwarding the user's), it would be
  a *client* of BetterAuth's client-credentials grant, using `httpx`/`authlib` to fetch and cache a
  token — not new authorization-server code.
- **Priority:** Low for fhir-gql as a server-side feature; Medium as a design question ("does
  fhir-gql ever need its own service identity to call fhir-server?") worth resolving explicitly.

### Authorization Code Grant (+ PKCE)
- **What it does:** Exchanges a one-time authorization `code` (from the authorize endpoint) for
  tokens — the standard web/mobile login flow, with PKCE as the primary client-auth mechanism for
  public clients.
- **Source files:** `oauth/token.ts` (`handleAuthorizationCode`, `verifyCode`).
- **How it works:** Looks up the `Login` by its `code` field, validates `client_id` matches, that it
  has a resolved `membership`, and that it isn't already `granted` (replay protection — a
  second use of the same code revokes the login and errors) or `revoked`. Unless the client is
  `pkceOptional`, requires and verifies a `code_verifier` against the stored `code_challenge` using
  either the `plain` method (exact string match) or `S256` (SHA-256 + base64url, `hashCode()`)
  per RFC 7636. Confidential clients can additionally/alternatively present a `client_secret`.
- **Belongs in:** `shared IAM service`.
- **Port notes for fhir-gql:** None.
- **Priority:** Low.

### Refresh Token Grant (with Rotation)
- **What it does:** Exchanges a long-lived refresh token for a new access token, rotating the refresh
  secret on every use (refresh token rotation, a modern OAuth2 security best practice).
- **Source files:** `oauth/token.ts` (`handleRefreshToken`).
- **How it works:** Verifies the refresh JWT's signature (`verifyJwt`), loads the `Login` by
  `login_id` claim, confirms the login has an active `refreshSecret` and the presented
  `refresh_secret` claim matches it via `timingSafeEqualStr` (constant-time — refresh secrets are
  high-value targets for timing attacks). Checks membership is still `active`. If a `Basic` auth
  header is present, validates it matches the login's original client. On success, generates a *new*
  `refreshSecret` (`generateSecret(32)`) and persists it to the `Login` before minting new tokens —
  so a stolen-and-reused old refresh token becomes invalid after the legitimate client's next
  refresh (rotation-based replay detection, though Medplum here doesn't appear to revoke-on-reuse-
  detected, just silently invalidates the old secret).
- **Belongs in:** `shared IAM service`.
- **Port notes for fhir-gql:** None — fhir-gql should never hold a refresh token; it only ever
  receives short-lived access tokens to validate.
- **Priority:** Low.

### Pre-Authorized Code Grant (Admin-Issued One-Time Login Links)
- **What it does:** Lets a project admin generate a code *on behalf of* another user (e.g. to email a
  one-click "activate your account" or "impersonate for support" link) without that user needing to
  authenticate interactively first.
- **Source files:** `auth/preauthorize.ts` (`preAuthorizeHandler`, `DEFAULT_PRE_AUTH_CODE_TTL`,
  `MAX_PRE_AUTH_CODE_TTL`), `oauth/token.ts` (`handlePreAuthorizedCode`).
- **How it works:** Restricted to project admins acting `onBehalfOf` another membership (requires the
  `x-medplum-on-behalf-of` mechanism to already be resolved — see below). Generates a 128-byte random
  code, stores only its SHA-256 *hash* on the `Login` (`preAuthorizedCodeHash`) — the raw code is
  never persisted, only returned once to the caller — with a configurable TTL (default 1h, max 7
  days). The token endpoint's `handlePreAuthorizedCode` hashes the incoming code the same way and
  matches by hash, checks expiry, and otherwise behaves like the authorization-code grant (single
  use, IP access rules, etc.).
- **Belongs in:** `shared IAM service` — this is an admin/support tooling feature layered on top of
  the authorization server, orthogonal to fhir-gql's request-orchestration role.
- **Port notes for fhir-gql:** None.
- **Priority:** Low.

### Token Exchange Grant — see "External Token Exchange" above (§6); same code path
  (`handleTokenExchange` → `exchangeExternalAuthToken`), included in the token endpoint's grant-type
  switch. **Belongs in:** `shared IAM service`. **Priority:** Low.

### Dynamic Client Registration (`POST /oauth2/register`, RFC 7591)
- **What it does:** OAuth2 Dynamic Client Registration — but Medplum's implementation is a deliberately
  narrow shim, *not* a real dynamic-registration endpoint: it only ever returns one of a small,
  hardcoded set of "standard clients" (e.g. the Medplum CLI, config-defined default clients) matched
  by redirect URI, never actually creates a new `ClientApplication`.
- **Source files:** `oauth/register.ts` (`registerHandler`), `oauth/clients.ts`
  (`getStandardClientByRedirectUri`).
- **How it works:** Takes `redirect_uris[0]` from the request, looks it up against
  `getStandardClientByRedirectUri()` (a small in-memory list seeded from `MEDPLUM_CLI_CLIENT_ID` +
  `config.defaultOAuthClients`), and returns that pre-existing client's `client_id` if a redirect URI
  match is found — otherwise 400. Real `ClientApplication` creation happens through the normal FHIR
  `POST /ClientApplication` REST API, not this endpoint (per the code comment context, this is
  effectively a compatibility shim for the MCP protocol's discovery flow, not full RFC 7591).
- **Belongs in:** `shared IAM service`.
- **Port notes for fhir-gql:** None.
- **Priority:** Low.

### OAuth Client Redirect-URI Resolution & Standard/Built-in Clients
- **What it does:** Shared helper logic for matching a requested redirect URI against a client's
  registered URIs (exact-match by default, with a documented-as-risky partial-match legacy
  fallback), plus a small registry of "built-in" clients that exist without a corresponding FHIR
  `ClientApplication` resource (CLI, MCP-required clients like Claude/ChatGPT).
- **Source files:** `oauth/clients.ts` (`getClientRedirectUri`, `getClientRedirectUris`,
  `isAllowedPartialRedirectUri`, `getStandardClientById`, `getStandardClientByRedirectUri`).
- **How it works:** `getClientRedirectUri` does exact string comparison by default (RFC 6749 / OAuth
  2.1 best practice); `allowPartial` mode (used only when a project has an explicit
  `allow-dangerous-redirect` setting) falls back to origin + path-prefix matching, explicitly
  documented in the source as NOT spec-recommended and kept only for legacy client migration.
- **Belongs in:** `shared IAM service`.
- **Port notes for fhir-gql:** None directly, but the redirect-URI exact-match-by-default /
  partial-match-only-if-explicitly-opted-in pattern is a good general security reference if fhir-gql
  ever validates any caller-supplied URLs (e.g. webhook callback URLs for a future feature) —
  worth reusing the *pattern*, not the code.
- **Priority:** Low.

### Client Authentication — Private Key JWT (`client_assertion`, RFC 7523)
- **What it does:** Lets a confidential client authenticate to the token endpoint using a self-signed
  JWT instead of a shared secret — required for SMART Backend Services (system-to-system clinical
  integrations) which explicitly mandate asymmetric client auth.
- **Source files:** `oauth/token.ts` (`parseClientAssertion`, `verifyMultipleMatchingException` in
  `oauth/utils.ts`).
- **How it works:** Client posts a JWT (`client_assertion_type=urn:ietf:params:oauth:client-assertion-
  type:jwt-bearer`) whose `iss` and `sub` both equal its own `client_id` (self-signed identity
  assertion) and `aud` equals the server's token URL. Server looks up the `ClientApplication` by that
  claimed `client_id`, requires it to have a configured `jwksUri`, fetches that JWKS
  (`createRemoteJWKSet`), and verifies the JWT signature/issuer/audience against it — accepting
  RS256/RS384/RS512/ES256/ES384/ES512. Handles the `jose` library's "multiple matching keys" edge
  case (a JWKS with several keys sharing a `kid`) by trying each candidate key in turn.
- **Belongs in:** `shared IAM service`.
- **Port notes for fhir-gql:** None — this only matters if fhir-gql itself becomes an authorization
  server accepting SMART Backend Services clients, which is explicitly out of scope per the current
  architecture.
- **Priority:** Low.

### Client Authentication — mTLS Certificate-Bound Tokens
- **What it does:** Validates a client TLS certificate (passed through from an upstream ALB/load
  balancer header) as an OAuth2 client authentication method — the highest-assurance client-auth
  option, used for FAPI-2/high-security financial/health API compliance profiles.
- **Source files:** `oauth/cert.ts` (`validateClientCert`, `validateCertExpiration`,
  `validateSelfSignedCert`, `validateCaSignedCert`), consumed by `oauth/token.ts`
  (`parseMtlsClientCertificate`).
- **How it works:** Uses Node's built-in `X509Certificate` (no external crypto library). Splits a PEM
  bundle into individual certs, checks expiration windows, and branches on whether the client cert is
  self-signed (must exactly match a fingerprint in the tenant's trusted-cert list,
  `certificateTrustStore`) or CA-signed (must chain to a trusted CA via `checkIssued` +
  signature `verify`). Configured via `config.mtlsCertHeader` naming which HTTP header the ALB
  injects the cert into.
- **Belongs in:** `shared IAM service`.
- **Port notes for fhir-gql:** None.
- **Priority:** Low.

### Client Secret Rotation
- **What it does:** Allows a client's secret to be rotated without a hard cutover — both the current
  and a "retiring" previous secret are accepted simultaneously during a rollover window.
- **Source files:** `oauth/token.ts` (`validateClientIdAndSecret`).
- **How it works:** Compares the presented secret against `client.secret` *and* (unconditionally, to
  avoid timing side-channels revealing whether a retiring secret exists) against
  `client.retiringSecret ?? client.secret`, both via `timingSafeEqualStr`.
- **Belongs in:** `shared IAM service`.
- **Port notes for fhir-gql:** None.
- **Priority:** Low.

### JWKS / Signing Key Management (`/.well-known/jwks.json`)
- **What it does:** Generates, stores, and rotates the asymmetric key pair(s) used to sign every
  Medplum-issued JWT, and publishes the public half as a standard JWKS document.
- **Source files:** `oauth/keys.ts` (`initKeys`, `getJwks`, `getSigningKey`, `generateIdToken`,
  `generateAccessToken`, `generateRefreshToken`, `generateJwt`, `verifyJwt`, `getKeyForHeader`).
- **How it works:** On boot, loads active `JsonWebKey` resources from the DB, or generates a fresh
  keypair (`generateKeyPair`, defaulting to ES256, with legacy RS256 support for existing
  deployments/customers per an explicit in-code migration note re: FAPI 2 compliance). Builds both a
  public JWKS (`{keys: JWK[]}`, no private material) and an internal signing-key map keyed by `kid`.
  All three token types (ID, access, refresh) go through one `generateJwt()` using `jose`'s
  `SignJWT`, setting `jti`, `iat`, `nbf`, `iss`, `aud`, `exp` — this is directly analogous to (and a
  useful reference for auditing) what fhir-gql's `decode_token()` already *consumes* on the verify
  side. `verifyJwt()` mirrors `fhir-gql`'s own `decode_token`: resolves signing key by `kid`, checks
  issuer, accepts both ES256 and RS256.
- **Belongs in:** `shared IAM service` for *issuance*. **Already implemented on the fhir-gql side for
  verification** — `app/auth/dependencies.py`'s `PyJWKClient` + `jwt.decode(...)` is the direct
  functional counterpart of this file's `verifyJwt`/`getKeyForHeader`, just consuming BetterAuth's
  JWKS instead of hosting one. No gap here; call this out explicitly so it isn't mistaken for missing
  functionality.
- **Port notes for fhir-gql:** None needed — already done. One nuance worth double-checking:
  fhir-gql's `decode_token()` accepts `["EdDSA", "RS256"]`; Medplum here defaults new keys to ES256
  with RS256 legacy support. Algorithm choice is BetterAuth's decision, not fhir-gql's, but confirm
  the accepted-algorithms allow-list in `dependencies.py` is kept in sync with whatever BetterAuth
  actually signs with (an algorithm mismatch here is silently a hard outage, not a soft warning).
- **Priority:** Low (already implemented); Medium as an ongoing "keep the algorithm allow-list in
  sync" operational note.

### Token Introspection (`POST /oauth2/introspect`, RFC 7662)
- **What it does:** Lets a resource server (or any authorized caller) ask "is this token still
  valid right now" — critical because JWT `exp` alone can't reflect a token that was revoked
  *before* it expired (e.g. after logout or password change).
- **Source files:** `oauth/introspect.ts` (`tokenIntrospectHandler`, `writeActiveResponse`,
  `writeInactiveResponse`).
- **How it works:** Verifies the JWT signature, then does the check a bare JWT verification
  *cannot* do — loads the live `Login` resource by `login_id` claim and checks `granted`/`revoked`
  flags against current DB state. Returns the standard RFC 7662 shape (`active`, `exp`, `iat`, `iss`,
  `sub`, `client_id`, `scope`) plus a SMART-specific `patient` field resolved from the launch context
  or `profile` claim.
- **Belongs in:** `shared IAM service` to *serve* introspection; **fhir-gql (middleware)** is a
  legitimate *consumer* of it. This is the one piece of section 7 with a real fhir-gql-side
  opportunity: fhir-gql's current `decode_token()` trusts a JWT purely on signature + `exp`/`iss`/
  `aud` — it has **no way to detect a token that was revoked before expiry** (e.g. immediately after
  a password change or explicit logout, per the "Set Password revokes all sessions" behavior
  documented above). If BetterAuth exposes an equivalent introspection endpoint, fhir-gql could
  optionally call it for high-sensitivity operations, or cache "known-revoked `jti`s" pushed via a
  webhook.
- **Port notes for fhir-gql:** If pursued: add an optional `introspect_token()` alongside
  `decode_token()` in `app/auth/dependencies.py` that calls BetterAuth's introspection endpoint (if
  it has one) via `httpx`, gated behind a config flag (`ENFORCE_INTROSPECTION`) so it can be applied
  selectively (e.g. only on write operations) rather than adding a network round-trip to every
  request. This is a real, current architectural gap — not urgent, but worth a deliberate decision
  rather than silence.
- **Priority:** Medium — genuine security gap (stateless JWT trust with no revocation check) worth a
  conscious decision, even if the decision is "acceptable risk given short access-token lifetimes."

### UserInfo Endpoint (`GET/POST /oauth2/userinfo`, OIDC Core)
- **What it does:** Standard OIDC endpoint returning the authenticated user's profile claims,
  scoped by which OIDC scopes (`profile`, `email`, `phone`, `address`) were granted at login.
- **Source files:** `oauth/userinfo.ts` (`userInfoHandler`, `buildProfile`, `buildEmail`,
  `buildPhone`, `buildAddress`).
- **How it works:** Reads the already-authenticated `ctx.login`/`ctx.profile`, conditionally adds
  claim groups based on `login.scope`. Notably formats FHIR `HumanName`/`Address` into OIDC's
  flat string conventions (`formatHumanName`, `formatAddress`, etc.) and only populates the rich
  profile block for `Patient`/`Practitioner` resource types (Bots/ClientApplications get just `sub`).
- **Belongs in:** `shared IAM service`.
- **Port notes for fhir-gql:** None — fhir-gql doesn't need a userinfo endpoint since it isn't an
  OIDC provider; if a client needs profile info, that's either already in the JWT claims or should
  be fetched from BetterAuth directly.
- **Priority:** Low.

### Bearer/Basic Auth Middleware & On-Behalf-Of Impersonation
- **What it does:** Two things bundled in one middleware layer: (1) dispatches incoming requests to
  either bearer-token or HTTP Basic client-credential verification, and (2) implements an admin
  "act as another user" header for support/automation scenarios.
- **Source files:** `oauth/middleware.ts` (`authenticateRequest`, `authenticateTokenImpl`,
  `isExtendedMode`), `oauth/utils.ts` (`getLoginForAccessToken`, `getLoginForBasicAuth`,
  `makeAuthResult`, `tryAddOnBehalfOf`).
- **How it works:** `authenticateTokenImpl` branches on the `Authorization` header's scheme:
  `Bearer` → `getLoginForAccessToken` (JWT verify + live `Login`/`membership.active` check, with a
  parallel path for *external* IdP-issued bearer tokens cached in Redis for 1h,
  `tryExternalAuth`/`redisKey = medplum:ext-auth:{issuer}:{hashCode(token)}`); `Basic` →
  `getLoginForBasicAuth` (client_id:client_secret pair, constant-time compared). Both funnel into
  `makeAuthResult`, which additionally checks for an `x-medplum-on-behalf-of` header — **only
  honored if the caller is a project admin or superAdmin** — that lets an authenticated admin
  request execute *as* a different `ProjectMembership`/profile (looked up either by
  `ProjectMembership/{id}` reference or by matching `profile` + `project`), attaching
  `authState.onBehalfOf`/`onBehalfOfMembership` and re-resolving the FHIR repository under that
  identity.
- **Belongs in:** `split` — the bearer/basic dispatch and JWT-vs-live-session check is `shared IAM
  service` territory (fhir-gql's `get_current_user` already does the bearer-JWT half, just without a
  live-revocation check per the introspection note above). The **on-behalf-of impersonation
  pattern**, however, is genuinely relevant to **fhir-gql (middleware)** if any support/automation
  tooling needs to act as another user against the Patient API — it's an authorization *pattern* independent of
  who issues tokens.
- **Port notes for fhir-gql:** If an on-behalf-of feature is wanted: add an `X-On-Behalf-Of` header
  check in `get_current_user` (or a new dependency layered on top of it) that (a) requires the
  caller's own JWT to carry an admin/superadmin permission, (b) resolves the target user via a
  BetterAuth lookup API, and (c) substitutes the `AuthUser.sub`/`org_id` used for the rest of the
  request — mirroring `tryAddOnBehalfOf`'s admin-only gate. Not needed until there's a concrete
  support-tooling requirement.
- **Priority:** Low-Medium — the impersonation pattern is worth remembering exists, but nothing to
  build until a concrete use case shows up.

---

## 8. SCIM 2.0 User Provisioning

### SCIM User CRUD + Search (`/scim/2.0/Users*`)
- **What it does:** Standard enterprise user-lifecycle provisioning protocol (SCIM 2.0) — lets an
  external Identity Provider (Okta, Azure AD, etc.) automatically create/update/deactivate/delete
  user accounts in Medplum when they're created/changed/removed in the corporate directory, instead
  of manual admin invites.
- **Source files:** `scim/routes.ts` (`scimRouter`: `GET/POST /Users`, `GET/PUT/PATCH/DELETE
  /Users/:id`), `scim/utils.ts` (`searchScimUsers`, `createScimUser`, `readScimUser`,
  `updateScimUser`, `patchScimUser`, `deleteScimUser`, `convertToScimUser`,
  `scimUserToUserAndMembership`, `convertScimToJsonPatch`, `getScimUserResourceType`), `scim/types.ts`
  (`ScimUser`, `ScimListResponse`, `ScimPatchRequest`/`ScimPatchOperation`, `ScimName`, `ScimEmail`,
  `ScimPhoneNumber`, `ScimMeta`).
- **How it works:** Entire router is gated behind `authenticateRequest` + `verifyProjectAdmin` — only
  project admins (or their automation credentials) can call it. Maps Medplum's `ProjectMembership` +
  `User` pair onto the SCIM `User` schema (`urn:ietf:params:scim:schemas:core:2.0:User`): SCIM
  `id` = membership ID, `userType` = FHIR profile resource type (`Patient`/`Practitioner`/
  `RelatedPerson`, read from a Medplum-specific extension on the SCIM payload, defaulting to
  `Practitioner`), `externalId` bridges to the IdP's own user ID for correlation. Create delegates to
  the existing admin `inviteUser()` flow (with `sendEmail: false`, since SCIM-provisioned users are
  expected to already have IdP-managed credentials). PATCH implements a genuine SCIM→JSONPatch
  translator (`convertScimToJsonPatch`) that handles SCIM's looser rules (leading-slash-free paths,
  path-omitted "flat object" adds) before applying via the app's generic `patchObject` JSON-patch
  utility. Search supports a minimal `filter=userName eq "..."` SCIM filter grammar via regex, plus
  hardcoded filtering to only `Patient,Practitioner,RelatedPerson` profile types (i.e. never surfaces
  bot/service accounts via SCIM). Errors are wrapped into the SCIM 2.0 error envelope (RFC 7644
  §3.12: `schemas`, `status`, `detail`) rather than a plain FHIR OperationOutcome.
- **Belongs in:** `shared IAM service` — SCIM is fundamentally a directory-synchronization protocol
  between an enterprise IdP and whatever owns user accounts; that's BetterAuth's job in this
  architecture, not fhir-gql's or fhir-server's. The one nuance: SCIM here also implicitly creates a
  FHIR `Patient`/`Practitioner`/`RelatedPerson` "profile" resource per user, which in fhir-gql's split
  would mean a SCIM-driven user create needs to *also* call fhir-server to create the corresponding
  clinical resource — same cross-service concern as patient self-registration (§2).
- **Port notes for fhir-gql:** Not recommended to build now. If/when enterprise customers need
  automated provisioning (a common ask from hospital-system IT departments), this would be a
  BetterAuth plugin/feature first; fhir-gql's role would only be the same orchestration hook needed
  for patient self-registration — creating the FHIR resource when IAM tells it a new
  Patient/Practitioner user was provisioned (e.g. via a webhook from BetterAuth).
- **Priority:** Low for now — enterprise SCIM provisioning is a "when we have hospital-IT customers"
  feature, not a near-term gap. Worth remembering the cross-service resource-creation pattern it
  shares with patient self-registration.

---

## 9. Security & Abuse Prevention (Cross-Cutting)

### Bot/Abuse Protection via reCAPTCHA
- **What it does:** Gates public, unauthenticated registration/reset endpoints behind Google
  reCAPTCHA to slow down automated account-creation/credential-stuffing abuse.
- **Source files:** `auth/utils.ts` (`validateRecaptcha`, `verifyRecaptcha`,
  `getProjectByRecaptchaSiteKey`), wired into `auth/routes.ts` on `/newuser` and `/resetpassword`.
- **How it works:** Middleware factory taking an optional per-project validation callback. Resolves
  which reCAPTCHA secret key to use — the server default, or (if the client's `recaptchaSiteKey`
  isn't the default) a per-project secret looked up via a `Project.site` search — then POSTs the
  client's token to Google's `siteverify` API and requires `success: true` before calling `next()`.
- **Belongs in:** `shared IAM service` — bot protection on account-creation endpoints is an IAM
  concern.
- **Port notes for fhir-gql:** N/A directly. If fhir-gql ever adds its own public unauthenticated
  endpoint (e.g. the patient self-registration orchestration endpoint proposed in §2), it should
  consider the *same* class of protection (reCAPTCHA/hCaptcha or Cloudflare Turnstile) at that layer,
  since it would be a new public attack surface even if BetterAuth already protects its own signup
  endpoint.
- **Priority:** Medium — directly relevant the moment the proposed patient self-registration endpoint
  is built, since that would be a new unauthenticated-ish surface in fhir-gql itself.

### IP Access Rules
- **What it does:** Per-project allow/block rules on client IP address, enforced at every point a
  `Login` becomes active (password login, membership selection, token refresh, client-credentials
  grant).
- **Source files:** `oauth/utils.ts` (`checkIpAccessRules`, `matchesIpAccessRule`), called from
  `setLoginMembership`, `oauth/token.ts`'s client-credentials and pre-authorized-code handlers.
- **How it works:** Iterates a project's `AccessPolicy.ipAccessRule` list in order; first matching
  rule (`*` wildcard, exact match, or prefix match via `startsWith`) wins — `allow` short-circuits
  success, `block` throws. No match falls through to allowed-by-default.
- **Belongs in:** `shared IAM service` for login-time enforcement (that's where Medplum applies it).
  Could be a candidate for **fhir-gql (middleware)** to *additionally* enforce at the API-gateway
  layer as defense-in-depth, since fhir-gql already sees every request's source IP.
- **Port notes for fhir-gql:** Not urgent; if wanted, this maps naturally onto a `RateLimitMiddleware`-
  adjacent piece (`app/middleware/rate_limit.py` already has the plumbing for per-request client
  identification) rather than the JWT/RBAC layer specifically.
- **Priority:** Low — nice defense-in-depth, not a current gap since org/tenant-level IP policy
  presumably lives with BetterAuth or a WAF today.

### Generic Rate Limiting on Auth Endpoints
- **What it does:** Medplum doesn't appear to have bespoke auth-specific rate limiting beyond
  reCAPTCHA + the external-userinfo-call's `429` passthrough
  (`oauth/utils.ts`'s `getExternalUserInfo` explicitly detects and rethrows a `tooManyRequests`
  outcome when an upstream IdP rate-limits it) — worth noting as an absence, not a feature to port.
- **Source files:** `oauth/utils.ts` (`getExternalUserInfo`, `tooManyRequests` handling only).
- **How it works:** N/A — no dedicated auth rate limiter found in the reviewed files.
- **Belongs in:** N/A.
- **Port notes for fhir-gql:** **Already implemented, generically** — `app/middleware/rate_limit.py`
  is a Redis-backed sliding-window limiter applied broadly (per `app/config.py`'s
  `RATE_LIMIT_READ`/`RATE_LIMIT_WRITE`/`RATE_LIMIT_WINDOW` settings). Worth confirming it also covers
  any new unauthenticated fhir-gql endpoints (like the proposed patient self-registration one) with a
  *tighter* limit than normal authenticated API traffic, since public signup endpoints are
  higher-value abuse targets than authenticated reads.
- **Priority:** Low — infra already exists; just needs a policy check when new public endpoints are
  added.

---

## Summary Table

| Feature | Priority | Belongs in |
|---|---|---|
| Password Login | Low | shared IAM service |
| Login Method Discovery | Low | shared IAM service |
| New User Registration | Low | shared IAM service |
| New Project Creation | Low | shared IAM service |
| **New Patient Self-Registration** | **High** | **fhir-gql + fhir-server + shared IAM service (split)** |
| Registration/Seed Utility | Low | out of scope |
| Password Reset Request | Low | shared IAM service |
| Set Password | Low | shared IAM service |
| Change Password | Low | shared IAM service |
| Email Verification | Low | shared IAM service |
| MFA (TOTP) Enrollment/Verify/Disable | Medium (flag to IAM) | shared IAM service |
| Multi-Profile Selection | Low | shared IAM service |
| Scope Selection / Incremental Consent | Low | shared IAM service / out of scope |
| Login Status Polling | Low | shared IAM service |
| Client Branding Info | Low | shared IAM service |
| Revoke / Logout Session | Medium | shared IAM service (thin fhir-gql proxy optional) |
| "Who Am I" (`/auth/me`) | Low | shared IAM service (trivial fhir-gql echo optional) |
| Google Sign-In | Low | shared IAM service |
| Generic External IdP (SSO) Federation | Low (Medium to verify hardening) | shared IAM service |
| External Token Exchange (RFC 8693) | Low | shared IAM service |
| OAuth2 Authorization Endpoint | Low | shared IAM service |
| OAuth2 Token Endpoint (dispatcher) | Low | shared IAM service |
| Client Credentials Grant | Low (Medium as design Q) | shared IAM service |
| Authorization Code Grant + PKCE | Low | shared IAM service |
| Refresh Token Grant + Rotation | Low | shared IAM service |
| Pre-Authorized Code Grant | Low | shared IAM service |
| Dynamic Client Registration | Low | shared IAM service |
| OAuth Client Redirect-URI Resolution | Low | shared IAM service |
| Client Auth — Private Key JWT | Low | shared IAM service |
| Client Auth — mTLS | Low | shared IAM service |
| Client Secret Rotation | Low | shared IAM service |
| JWKS / Signing Key Management | Low (already done, verify) | shared IAM (issuance) / fhir-gql (verification, done) |
| Token Introspection | **Medium** | shared IAM service (serve) / **fhir-gql (consume, gap)** |
| UserInfo Endpoint | Low | shared IAM service |
| Bearer/Basic Middleware + On-Behalf-Of | Low-Medium | shared IAM service / fhir-gql (pattern) |
| SCIM 2.0 User Provisioning | Low | shared IAM service |
| reCAPTCHA Bot Protection | **Medium** | shared IAM service / **fhir-gql (new public endpoints)** |
| IP Access Rules | Low | shared IAM service / fhir-gql (optional defense-in-depth) |
| Generic Auth Rate Limiting | Low | fhir-gql (already implemented generically) |

## Recommended Next Steps

The overwhelming majority of Medplum's identity surface is intentionally out of `fhir-gql`'s hands by
design — it's a thin, stateless JWT verifier + RBAC gate in front of BetterAuth, and that's correct
for a middleware layer. Three items deserve real attention, roughly in priority order: (1) **design
the patient self-registration orchestration flow** (`newpatient.ts`'s equivalent) since it's the only
feature here that directly extends the currently-shipped `Patient` slice and requires a new
BetterAuth contract (binding org/permissions to a user *after* a middleware-driven signup) that
doesn't obviously exist yet — this is a cross-team API design conversation, not just fhir-gql code;
(2) **decide fhir-gql's stance on token revocation freshness** — today `decode_token()` trusts a JWT
purely on signature + expiry with no way to see a mid-lifetime revocation (logout, password change),
which is a real if likely low-severity gap given presumably short access-token lifetimes; and
(3) **add rate limiting / bot protection explicitly to whatever new public endpoint patient
self-registration introduces**, since it would be fhir-gql's first genuinely public-facing surface.
Everything else in this document — the full OAuth2 authorization server, MFA, SCIM, external IdP
federation — is correctly BetterAuth's problem and should stay there unless a concrete product
requirement (e.g. third-party SMART app support) forces `fhir-gql` to become an authorization server
in its own right.
