# Project Rules

## Skills
- Before starting any operation, check if an appropriate skill exists for it. If a matching skill is available, use it — do not implement the operation manually.

## Adding/Changing a FHIR Resource — This Is Only Half

This gateway sits in front of `D:\code\work\projects\fhir-server` (sibling repo). When a resource (or a cross-cutting field, like `extension`) is asked for **"end to end,"** that means both repos — see fhir-server's CLAUDE.md, "What 'End-to-End' Means," and its `/new-fhir-resource` skill's Step 18 for the authoritative checklist of what this repo's own half needs: the canonical `app/fhir/schemas/<resource>.py`, **both** connector translators (`app/connectors/internal/translators/` **and** `app/connectors/medplum/translators/` — never just the one currently active in `configs/config.yaml`), the `translator_registry.py` entries, the GraphQL types (`app/gql/<resource>/types/` — any non-scalar field like `extension` needs an explicit `JSON | None` override; `all_fields=True` doesn't handle it alone), queries/mutations, and the root schema wiring.

**A resource/field is not done until it's been tested on both connectors, not just one.** `internal` and `medplum` have genuinely different wire conventions (e.g. PATCH: `internal` sends a plain partial-fields dict, `medplum` requires an RFC 6902 JSON Patch array via `app.connectors.medplum.json_patch.to_json_patch()` — every resource's medplum PATCH was silently broken this way until it was actually exercised against a live Medplum instance, not caught by code review). Don't declare something complete on the strength of `internal` working alone.

## Code Comments
- Every piece of code must have detailed comments explaining what it does, why it exists, and how it works. This includes functions, classes, methods, complex logic, configuration, and non-obvious decisions. Do not leave any code block without a comment.
