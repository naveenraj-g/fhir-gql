# OpenEMR connector

Status: **read-only (Organization, Location) - working and verified live.** Writes are parked and the connector answers 405 for them; see "Open work".

Local OpenEMR: `docker/connectors/openemr` (UI http://localhost, API docs http://localhost/swagger/,
FHIR capability statement http://localhost/apis/default/fhir/metadata).

## How it logs in (system scopes, SMART Backend Services)

No client secret is used. `token_manager.py` signs a short JWT (RS384) with our PRIVATE key and posts it as
`client_assertion` (`grant_type=client_credentials`). OpenEMR verifies it with the PUBLIC key (JWKS) stored on the
client, checks `iss=sub=client_id`, `aud=token URL`, `exp`, `iat` (<= 5 min old) and a never-before-seen `jti`,
then returns a 300 s access token. The `kid` is derived from the private key (RFC 7638 thumbprint).

Setup (once):
1. OpenEMR Administration -> Config -> Connectors: enable Standard REST API, Standard FHIR REST API and FHIR System
   Scopes; Site Address Override = `http://localhost` (no trailing dot).
2. Register the client (Administration -> System -> API Clients) with the public JWKS inline, then enable it.
3. `.env`: `CONNECTORS__OPENEMR__CLIENT_ID`, `CONNECTORS__OPENEMR__PRIVATE_KEY_PATH=secrets/openemr_private_key.pem`.
   The `secrets/` folder is gitignored. Never commit or share the private key.
4. `configs/config.yaml`: `connectors.active: openemr`.

## What works / what does not (tested live)

| Operation | Result |
|---|---|
| Organization / Location search, read by id, filters | works |
| Organization create / update | 401 - needs an admin **user** login, not available to system scopes |
| Organization delete | 404 - no such route |
| Location create / update / delete | 404 - no such routes |

OpenEMR offers no `system/*.write` scope at all (checked its `scopes_supported`). The only Organization write scope is
`user/Organization.write`; Location has no write scope. The connector's post/patch/delete are 405 stubs; the earlier
GET -> merge -> PUT patch emulation was removed (OpenEMR only has PUT).

## Open work (come back to this)

Organization writes via an admin user login (Location writes are impossible in OpenEMR):
1. Register a **second** client: user app, authorization-code flow, scopes
   `openid offline_access api:fhir user/Organization.read user/Organization.write`, with a redirect URL.
2. One-time browser login as an OpenEMR admin and consent; keep the returned refresh token (offline_access).
3. Add a token manager variant that exchanges the refresh token for access tokens (and stores the rotated refresh
   token), used for writes only; reads can keep the system-scope token.
4. Note writes then run as that admin user (audit shows the user, not the gateway).
5. Test Organization create and update live, then update README.md / CLAUDE.md, which currently say read-only.
