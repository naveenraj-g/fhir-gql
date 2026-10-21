"""
FHIR R4 Reference datatype — a reference from one resource to another.

Simplified to `reference`/`display` only (no `type`/`identifier`) — nothing
in this gateway has needed the full shape yet; add fields here if a future
resource does.

Spec: https://hl7.org/fhir/R4/references.html#Reference
"""

from pydantic import BaseModel, Field


class FhirReference(BaseModel):
    reference: str | None = Field(
        default=None, description="Relative URL reference (e.g. 'Endpoint/1')"
    )
    display: str | None = Field(
        default=None, description="Human-readable text for the reference"
    )
