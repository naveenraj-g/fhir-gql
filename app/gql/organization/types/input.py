"""
GraphQL input types for the Organization resource.

Derived from the generated Pydantic models by `app.gql.fhir_types` (GraphQL needs separate input
classes, but they describe the same FHIR R4 elements as the output types):

* `FhirOrganizationInput` - create: the whole resource, where a field R4 requires is non-null.
* `FhirOrganizationPatchInput` - update: a merge-patch, every top-level element optional.
"""

from app.gql.fhir_types import input_type
from app.schemas.fhir_resources import Organization, OrganizationPatch

# Create input (`createFhirOrganization`).
FhirOrganizationInput = input_type(Organization)
# Update input (`updateFhirOrganization`): the same elements, all optional at the top level.
FhirOrganizationPatchInput = input_type(
    OrganizationPatch, name="FhirOrganizationPatchInput"
)
