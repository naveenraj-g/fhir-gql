"""Shared RFC 6902 JSON Patch helper for Medplum's PATCH endpoint.

FHIR R4's PATCH interaction (hl7.org/fhir/R4/http.html#patch) does not
accept a plain resource body — Medplum enforces this and rejects one
outright with a 400 "Invalid patch body" (confirmed live: every one of
this gateway's `updateFhirX` mutations hit this before the fix, since
every medplum translator's `to_wire_patch()` previously just returned
`{"resourceType": X, **data}`, a full-resource-shaped dict, not a patch
document).

Medplum supports JSON Patch (rfc-editor.org/rfc/rfc6902), sent as a
top-level array with `Content-Type: application/json-patch+json` (set by
MedplumConnector.patch(), not here), so every top-level field this gateway
wants to change becomes one "add" operation — RFC 6902's "add" on an
*existing* member also replaces it, so this is correct whether the field
already exists or is being set for the first time; "replace" would fail
outright for the latter case.
"""


def to_json_patch(data: dict) -> list[dict]:
    """Canonical FHIR field-replacement dict -> RFC 6902 JSON Patch array.

    `data` only ever carries fields the caller actually supplied (each
    mutation builds it via `model_dump(exclude_none=True)`), so every key
    here gets its own "add" op; there is nothing to express a `null` value
    for, since an omitted field and an explicit null are indistinguishable
    by the time `data` reaches this function."""
    return [{"op": "add", "path": f"/{key}", "value": value} for key, value in data.items()]
