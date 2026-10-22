# OpenEMR (local dev backend)

Runs a local OpenEMR + MariaDB stack for developing `app.connectors.openemr`
against a real instance, the same way `docker/connectors/medplum/` (once
added) would for Medplum — each connector gets its own backend here since
each is a genuinely separate system with its own Docker/compose shape.

## Start

```
docker compose -f docker/connectors/openemr/docker-compose.yml up -d
```

First boot takes 5-10 minutes (OpenEMR's own DB setup). Watch it with:

```
docker compose -f docker/connectors/openemr/docker-compose.yml logs -f openemr
```

Web UI: `https://localhost/` (self-signed cert — accept the browser warning).
Login: `admin` / `pass`.

## Enabling FHIR

Not on by default — no Docker env var for it (checked against OpenEMR's
current docs). One-time manual setup after first boot:

1. Log into the web UI as `admin`/`pass`.
2. **Administration → Config → Connectors** → check **Enable OpenEMR
   Standard FHIR REST API** → set **Site Address** to `https://localhost`
   (required for OAuth2/FHIR) → **Save**.
3. Register an OAuth2 client — `POST` to
   `https://localhost/oauth2/default/registration` with `client_name`,
   `redirect_uris`, `scope`. See
   [API_README.md](https://github.com/openemr/openemr/blob/master/API_README.md)
   and `AUTHENTICATION.md` in that repo for the client-credentials
   token flow (OpenEMR supports both a client-secret grant and
   JWKS-based asymmetric auth for backend services).
4. FHIR base path once enabled: `https://localhost/apis/default/fhir`.
   Interactive Swagger UI (same shape as the public demo at
   https://eleven.openemr.io/a/openemr/swagger/index.html): `https://localhost/swagger/`.

## Stop

```
docker compose -f docker/connectors/openemr/docker-compose.yml down
```

Add `-v` to also drop the `openemr_db`/`openemr_logs`/`openemr_sites`
volumes (full reset — you'll redo the FHIR/OAuth2 setup above from scratch).
