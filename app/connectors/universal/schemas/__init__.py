"""
Canonical FHIR R4 Pydantic schemas for the universal-FHIR-GraphQL
experiment, one module per resource (organization.py, ... as more get
added) — see app.connectors.universal's package docstring for the overall
idea. Re-exported here so existing imports
(`from app.connectors.universal.schemas import FhirOrgResponse`, etc.) keep
working unchanged regardless of which resource module a name lives in.
"""

from app.connectors.universal.schemas.organization import (
    FhirAddress,
    FhirCodeableConcept,
    FhirCoding,
    FhirContactPoint,
    FhirHumanName,
    FhirIdentifier,
    FhirOrgContact,
    FhirOrganizationInput,
    FhirOrgResponse,
    FhirPeriod,
    FhirReference,
)

__all__ = [
    "FhirAddress",
    "FhirCodeableConcept",
    "FhirCoding",
    "FhirContactPoint",
    "FhirHumanName",
    "FhirIdentifier",
    "FhirOrgContact",
    "FhirOrganizationInput",
    "FhirOrgResponse",
    "FhirPeriod",
    "FhirReference",
]
