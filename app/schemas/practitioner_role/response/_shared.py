from pydantic import BaseModel, ConfigDict, Field


class _AuditFields(BaseModel):
    """Shared audit trail fields present on every PractitionerRole sub-resource
    row — not part of FHIR itself, this codebase's own created/updated tracking."""

    model_config = ConfigDict(extra="allow")
    created_at: str | None = Field(None, description="When this row was created.")
    updated_at: str | None = Field(None, description="When this row was last updated.")
    created_by: str | None = Field(
        None, description="Acting user who created this row, forwarded by the gateway."
    )
    updated_by: str | None = Field(
        None,
        description="Acting user who last updated this row, forwarded by the gateway.",
    )
